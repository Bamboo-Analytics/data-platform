"""
Pipeline orchestrator - coordinates extraction, transformation, validation, and loading.

This is the core pipeline logic that is Airflow-agnostic.
"""

from datetime import date, datetime, timedelta
from typing import Optional
import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from data_platform.config import get_config
from data_platform.connectors.base import ConnectorFactory
from data_platform.models import (
    AssetDataPoint,
    DailyFactRecord,
    IngestionResult,
    AssetClass,
    Vendor,
)
from data_platform.transformers import DataTransformer
from data_platform.validation import DataQualityChecker
from data_platform.storage.clickhouse import ClickHouseClient

logger = logging.getLogger(__name__)


class PipelineRunner:
    """
    Main pipeline orchestrator.
    
    Runs the ETL pipeline: Extract -> Transform -> Validate -> Load
    """

    def __init__(
        self,
        config: Optional[dict] = None,
        clickhouse_client: Optional[ClickHouseClient] = None,
    ):
        """
        Initialize pipeline runner.
        
        Args:
            config: Optional configuration override
            clickhouse_client: Optional ClickHouse client (for testing)
        """
        self.config = config or get_config()
        self.transformer = DataTransformer()
        self.quality_checker = DataQualityChecker(
            max_null_rate=self.config.pipeline.max_null_rate,
        )
        
        # Initialize ClickHouse client
        if clickhouse_client:
            self.clickhouse = clickhouse_client
        else:
            self.clickhouse = ClickHouseClient(
                host=self.config.clickhouse.host,
                port=self.config.clickhouse.port,
                username=self.config.clickhouse.username,
                password=self.config.clickhouse.password,
                database=self.config.clickhouse.database,
                batch_size=self.config.clickhouse.batch_insert_size,
            )

    def run_daily(
        self,
        start_date: date,
        end_date: Optional[date] = None,
        tickers: Optional[list[str]] = None,
    ) -> IngestionResult:
        """
        Run daily ingestion pipeline.
        
        Args:
            start_date: Start date for ingestion
            end_date: End date for ingestion (default: today)
            tickers: Optional list of tickers to ingest (default: all)
            
        Returns:
            IngestionResult with stats and errors
        """
        if end_date is None:
            end_date = date.today()

        logger.info(f"Starting daily ingestion: {start_date} to {end_date}")

        result = IngestionResult(success=True)

        # Get enabled sources
        sources = self.config.get_enabled_daily_sources()
        
        # Filter by tickers if specified
        if tickers:
            sources = [s for s in sources if s["ticker"] in tickers]

        logger.info(f"Processing {len(sources)} sources")

        all_data_points = []

        # Extract data from all sources
        for source in sources:
            try:
                data_points = self._extract_source(source, start_date, end_date)
                all_data_points.extend(data_points)
                result.records_extracted += len(data_points)
                logger.info(
                    f"Extracted {len(data_points)} data points from {source['ticker']}"
                )
            except Exception as e:
                error_msg = f"Failed to extract {source['ticker']}: {e}"
                logger.error(error_msg)
                result.add_error(error_msg)

        if not all_data_points:
            logger.warning("No data extracted")
            return result

        # Transform
        try:
            all_data_points = self.transformer.normalize_timezone(all_data_points)
            all_data_points = self.transformer.deduplicate(all_data_points)
            daily_facts = self.transformer.convert_to_daily_facts(all_data_points)
            result.records_transformed = len(daily_facts)
            logger.info(f"Transformed {len(daily_facts)} daily fact records")
        except Exception as e:
            error_msg = f"Transformation failed: {e}"
            logger.error(error_msg)
            result.add_error(error_msg)
            return result

        # Validate
        try:
            is_valid, errors = self.quality_checker.check(daily_facts)
            result.records_validated = len(daily_facts) if is_valid else 0
            
            if not is_valid:
                for error in errors:
                    result.add_error(f"Validation error: {error}")
                logger.error("Data quality check failed")
                return result

            # Check outliers (warnings only)
            if self.config.pipeline.check_outliers:
                _, warnings = self.quality_checker.check_outliers(
                    daily_facts,
                    z_score_threshold=self.config.pipeline.z_score_threshold,
                )
                for warning in warnings:
                    result.add_warning(warning)

            logger.info("Data quality checks passed")
        except Exception as e:
            error_msg = f"Validation failed: {e}"
            logger.error(error_msg)
            result.add_error(error_msg)
            return result

        # Load
        try:
            with self.clickhouse:
                records_loaded = self.clickhouse.insert_daily_facts(daily_facts)
                result.records_loaded = records_loaded
                logger.info(f"Loaded {records_loaded} records to ClickHouse")
        except Exception as e:
            error_msg = f"Loading failed: {e}"
            logger.error(error_msg)
            result.add_error(error_msg)
            return result

        logger.info(f"Daily ingestion completed successfully: {result}")
        return result

    @retry(
        retry=retry_if_exception_type(ConnectionError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    def _extract_source(
        self, source: dict, start_date: date, end_date: date
    ) -> list[AssetDataPoint]:
        """
        Extract data from a single source with retry logic.
        
        Args:
            source: Source configuration dict
            start_date: Start date
            end_date: End date
            
        Returns:
            List of AssetDataPoint instances
        """
        vendor = Vendor(source["vendor"])
        asset_class = AssetClass(source["asset_class"])
        ticker = source["ticker"]

        # Create connector
        connector_config = source.get("config", {})
        connector = ConnectorFactory.create(
            vendor=vendor,
            asset_class=asset_class,
            **connector_config,
        )

        # Fetch data
        data_points = connector.fetch(ticker, start_date, end_date)

        return data_points

    def run_backfill(
        self,
        start_date: date,
        end_date: date,
        chunk_size_days: int = 365,
        tickers: Optional[list[str]] = None,
    ) -> list[IngestionResult]:
        """
        Run backfill for a large date range in chunks.
        
        Args:
            start_date: Start date
            end_date: End date
            chunk_size_days: Size of each chunk in days
            tickers: Optional list of tickers
            
        Returns:
            List of IngestionResult for each chunk
        """
        logger.info(
            f"Starting backfill: {start_date} to {end_date} "
            f"in {chunk_size_days}-day chunks"
        )

        results = []
        current_date = start_date

        while current_date <= end_date:
            chunk_end = min(current_date + timedelta(days=chunk_size_days), end_date)
            
            logger.info(f"Backfill chunk: {current_date} to {chunk_end}")
            
            result = self.run_daily(
                start_date=current_date,
                end_date=chunk_end,
                tickers=tickers,
            )
            results.append(result)

            if not result.success:
                logger.warning(f"Chunk failed: {current_date} to {chunk_end}")

            current_date = chunk_end + timedelta(days=1)

        total_loaded = sum(r.records_loaded for r in results)
        logger.info(f"Backfill completed: {total_loaded} total records loaded")

        return results

    def run_quarterly(self) -> IngestionResult:
        """
        Run quarterly ingestion pipeline (placeholder).
        
        Returns:
            IngestionResult
        """
        logger.info("Starting quarterly ingestion")
        result = IngestionResult(success=True)

        # Get quarterly sources
        sources = self.config.get_enabled_quarterly_sources()

        if not sources:
            logger.info("No quarterly sources configured")
            return result

        # TODO: Implement quarterly ingestion logic
        logger.warning("Quarterly ingestion not yet implemented")

        return result

    def initialize_database(self) -> None:
        """Initialize ClickHouse database tables."""
        logger.info("Initializing ClickHouse database")
        with self.clickhouse:
            self.clickhouse.create_tables()
        logger.info("Database initialized successfully")
