"""
ClickHouse client and data loader.

Handles connection pooling, batch insertion, and idempotent upserts.
"""

from datetime import date, datetime
from typing import Any, Optional
import logging

import clickhouse_connect
from clickhouse_connect.driver import Client

from data_platform.models import DailyFactRecord, AssetClass, Vendor

logger = logging.getLogger(__name__)


class ClickHouseClient:
    """
    ClickHouse client wrapper with batch insertion and deduplication.
    
    Uses clickhouse-connect library for native protocol support.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8123,
        username: str = "default",
        password: str = "",
        database: str = "default",
        batch_size: int = 10000,
        **kwargs,
    ):
        """
        Initialize ClickHouse client.
        
        Args:
            host: ClickHouse server host
            port: ClickHouse HTTP port (default: 8123)
            username: Database username
            password: Database password
            database: Database name
            batch_size: Batch size for inserts
            **kwargs: Additional connection parameters
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.batch_size = batch_size
        self.kwargs = kwargs
        self._client: Optional[Client] = None

    def connect(self) -> None:
        """Establish connection to ClickHouse."""
        try:
            self._client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                database=self.database,
                **self.kwargs,
            )
            logger.info(
                f"Connected to ClickHouse at {self.host}:{self.port}/{self.database}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise ConnectionError(f"ClickHouse connection failed: {e}") from e

    def disconnect(self) -> None:
        """Close ClickHouse connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Disconnected from ClickHouse")

    @property
    def client(self) -> Client:
        """Get active client connection."""
        if self._client is None:
            self.connect()
        return self._client

    def execute(self, query: str, parameters: Optional[dict] = None) -> Any:
        """
        Execute a query.
        
        Args:
            query: SQL query
            parameters: Query parameters
            
        Returns:
            Query result
        """
        try:
            return self.client.query(query, parameters=parameters)
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}")
            raise

    def insert_daily_facts(
        self,
        records: list[DailyFactRecord],
        table: str = "daily_features",
    ) -> int:
        """
        Insert daily fact records into ClickHouse.
        
        Uses batch insertion for performance.
        Relies on ReplacingMergeTree for deduplication.
        
        Args:
            records: List of DailyFactRecord instances
            table: Target table name
            
        Returns:
            Number of records inserted
        """
        if not records:
            logger.warning("No records to insert")
            return 0

        total_inserted = 0

        # Process in batches
        for i in range(0, len(records), self.batch_size):
            batch = records[i : i + self.batch_size]
            
            # Convert to column format
            data = self._records_to_columns(batch)

            try:
                self.client.insert(
                    table=table,
                    data=data,
                    column_names=list(data.keys()),
                )
                total_inserted += len(batch)
                logger.info(
                    f"Inserted batch {i // self.batch_size + 1}: {len(batch)} records"
                )
            except Exception as e:
                logger.error(f"Failed to insert batch: {e}")
                raise

        logger.info(f"Total inserted: {total_inserted} records into {table}")
        return total_inserted

    def _records_to_columns(
        self, records: list[DailyFactRecord]
    ) -> dict[str, list]:
        """
        Convert records to column-oriented format for ClickHouse.
        
        Args:
            records: List of DailyFactRecord instances
            
        Returns:
            Dictionary mapping column names to value lists
        """
        columns = {
            "date": [],
            "ticker": [],
            "asset_class": [],
            "symbol": [],
            "currency": [],
            "close_price": [],
            "open_price": [],
            "high_price": [],
            "low_price": [],
            "daily_return": [],
            "volume": [],
            "yield_value": [],
            "spread_value": [],
            "correlation_30d": [],
            "correlation_90d": [],
            "vendor": [],
            "ingestion_timestamp": [],
            "data_timestamp": [],
            "version": [],
            "metadata": [],
        }

        for record in records:
            columns["date"].append(record.date)
            columns["ticker"].append(record.ticker)
            columns["asset_class"].append(record.asset_class.value)
            columns["symbol"].append(record.symbol)
            columns["currency"].append(record.currency or "")
            columns["close_price"].append(record.close_price)
            columns["open_price"].append(record.open_price)
            columns["high_price"].append(record.high_price)
            columns["low_price"].append(record.low_price)
            columns["daily_return"].append(record.daily_return)
            columns["volume"].append(record.volume)
            columns["yield_value"].append(record.yield_value)
            columns["spread_value"].append(record.spread_value)
            columns["correlation_30d"].append(record.correlation_30d)
            columns["correlation_90d"].append(record.correlation_90d)
            columns["vendor"].append(record.vendor.value)
            columns["ingestion_timestamp"].append(record.ingestion_timestamp)
            columns["data_timestamp"].append(record.data_timestamp)
            columns["version"].append(record.version)
            columns["metadata"].append(str(record.metadata))  # JSON as string

        return columns

    def query_daily_facts(
        self,
        ticker: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 1000,
    ) -> list[dict]:
        """
        Query daily facts from ClickHouse.
        
        Args:
            ticker: Filter by ticker
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum records to return
            
        Returns:
            List of record dictionaries
        """
        conditions = []
        params = {}

        if ticker:
            conditions.append("ticker = %(ticker)s")
            params["ticker"] = ticker

        if start_date:
            conditions.append("date >= %(start_date)s")
            params["start_date"] = start_date

        if end_date:
            conditions.append("date <= %(end_date)s")
            params["end_date"] = end_date

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
        SELECT *
        FROM daily_features
        WHERE {where_clause}
        ORDER BY date DESC, ticker
        LIMIT {limit}
        """

        result = self.execute(query, params)
        return result.result_rows

    def create_tables(self) -> None:
        """Create tables if they don't exist."""
        # Daily features table
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_features
            (
                date Date,
                ticker String,
                asset_class String,
                symbol String,
                currency String,
                close_price Nullable(Float64),
                open_price Nullable(Float64),
                high_price Nullable(Float64),
                low_price Nullable(Float64),
                daily_return Nullable(Float64),
                volume Nullable(Float64),
                yield_value Nullable(Float64),
                spread_value Nullable(Float64),
                correlation_30d Nullable(Float64),
                correlation_90d Nullable(Float64),
                vendor String,
                ingestion_timestamp DateTime,
                data_timestamp DateTime,
                version UInt32,
                metadata String
            )
            ENGINE = ReplacingMergeTree(version)
            PARTITION BY toYYYYMM(date)
            ORDER BY (ticker, date)
            """
        )
        logger.info("Created daily_features table")

        # Quarterly features table (for future use)
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS quarterly_features
            (
                quarter String,
                ticker String,
                asset_class String,
                symbol String,
                feature_name String,
                value Nullable(Float64),
                vendor String,
                ingestion_timestamp DateTime,
                data_timestamp DateTime,
                version UInt32,
                metadata String
            )
            ENGINE = ReplacingMergeTree(version)
            PARTITION BY quarter
            ORDER BY (ticker, quarter, feature_name)
            """
        )
        logger.info("Created quarterly_features table")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
