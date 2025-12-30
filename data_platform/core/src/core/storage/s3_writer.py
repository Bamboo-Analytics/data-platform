"""S3 writer for storing data in parquet format with incremental load support."""
import io
import logging
from datetime import datetime
from typing import List, Optional
import boto3
import pandas as pd
from botocore.exceptions import ClientError
from data_platform.ingestion.models.standard import OHLCV, AssetInfo

logger = logging.getLogger(__name__)


class S3ParquetWriter:
    """
    Handles writing data to S3 in parquet format.
    Supports incremental loads by tracking latest timestamps.
    """
    
    def __init__(self, bucket: str, region: Optional[str] = None):
        """
        Initialize S3 Parquet Writer.
        
        Args:
            bucket: S3 bucket name
            region: AWS region (optional, uses default if not provided)
        """
        self.bucket = bucket
        self.s3_client = boto3.client('s3', region_name=region)
        logger.info(f"Initialized S3ParquetWriter for bucket: {bucket}")
    
    def write_ohlcv(
        self, 
        data: List[OHLCV], 
        ticker: str,
        partition_by_date: bool = True
    ) -> str:
        """
        Write OHLCV data to S3 as parquet.
        
        Args:
            data: List of OHLCV records
            ticker: Ticker symbol
            partition_by_date: If True, partition by year/month/day
            
        Returns:
            S3 key where data was written
            
        Raises:
            ValueError: If data is empty
        """
        if not data:
            raise ValueError("No data to write")
        
        logger.info(f"Writing {len(data)} OHLCV records for {ticker}")
        
        # Convert to DataFrame
        df = pd.DataFrame([record.model_dump() for record in data])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Sort by timestamp
        df = df.sort_values('timestamp')
        
        # Generate S3 key with partitioning
        if partition_by_date:
            # Use the latest timestamp for partitioning
            latest_ts = df['timestamp'].max()
            timestamp_str = latest_ts.strftime('%Y%m%d_%H%M%S')
            s3_key = (
                f"ohlcv/"
                f"source={data[0].source}/"
                f"ticker={ticker.lower()}/"
                f"year={latest_ts.year}/"
                f"month={latest_ts.month:02d}/"
                f"day={latest_ts.day:02d}/"
                f"data_{timestamp_str}.parquet"
            )
        else:
            timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            s3_key = (
                f"ohlcv/"
                f"source={data[0].source}/"
                f"ticker={ticker.lower()}/"
                f"data_{timestamp_str}.parquet"
            )
        
        # Write to S3
        self._write_dataframe_to_s3(df, s3_key)
        
        logger.info(f"Successfully wrote OHLCV data to s3://{self.bucket}/{s3_key}")
        return s3_key
    
    def write_asset_info(self, data: AssetInfo) -> str:
        """
        Write asset info to S3 as parquet.
        
        Args:
            data: AssetInfo record
            
        Returns:
            S3 key where data was written
        """
        logger.info(f"Writing asset info for {data.ticker}")
        
        # Convert to DataFrame
        df = pd.DataFrame([data.model_dump()])
        
        # Generate S3 key
        timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        s3_key = (
            f"asset_info/"
            f"source={data.source}/"
            f"ticker={data.ticker.lower()}/"
            f"info_{timestamp_str}.parquet"
        )
        
        # Write to S3
        self._write_dataframe_to_s3(df, s3_key)
        
        logger.info(f"Successfully wrote asset info to s3://{self.bucket}/{s3_key}")
        return s3_key
    
    def get_latest_timestamp(
        self, 
        ticker: str, 
        data_type: str = 'ohlcv',
        source: Optional[str] = None
    ) -> Optional[datetime]:
        """
        Get the latest timestamp for a ticker from S3.
        Used for incremental loads to determine where to start fetching.
        
        Args:
            ticker: Ticker symbol
            data_type: Type of data ('ohlcv' or 'asset_info')
            source: Data source (e.g., 'yfinance'). If None, searches all sources.
            
        Returns:
            Latest timestamp or None if no data exists
        """
        try:
            # Construct prefix based on whether source is specified
            if source:
                prefix = f"{data_type}/source={source}/ticker={ticker.lower()}/"
            else:
                prefix = f"{data_type}/"
            
            logger.debug(f"Querying latest timestamp for {ticker} with prefix: {prefix}")
            
            # List objects with prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            
            if 'Contents' not in response or not response['Contents']:
                logger.debug(f"No existing data found for {ticker}")
                return None
            
            # Get the most recent file based on LastModified
            latest_file = max(response['Contents'], key=lambda x: x['LastModified'])
            logger.debug(f"Found latest file: {latest_file['Key']}")
            
            # Download and read the parquet file
            obj = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=latest_file['Key']
            )
            
            # Read parquet file
            df = pd.read_parquet(io.BytesIO(obj['Body'].read()))
            
            # Get latest timestamp from the data
            if 'timestamp' in df.columns:
                latest_ts = pd.to_datetime(df['timestamp']).max()
                latest_dt = latest_ts.to_pydatetime()
                logger.info(f"Latest timestamp for {ticker}: {latest_dt}")
                return latest_dt
            
            logger.warning(f"No timestamp column found in {latest_file['Key']}")
            return None
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchBucket':
                logger.error(f"Bucket {self.bucket} does not exist")
            elif error_code == 'NoSuchKey':
                logger.debug(f"No data found for {ticker}")
            else:
                logger.error(f"Error getting latest timestamp: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting latest timestamp: {e}", exc_info=True)
            return None
    
    def _write_dataframe_to_s3(self, df: pd.DataFrame, s3_key: str):
        """
        Write DataFrame to S3 as parquet.
        
        Args:
            df: DataFrame to write
            s3_key: S3 key (path) for the file
        """
        # Convert DataFrame to parquet in memory
        parquet_buffer = io.BytesIO()
        df.to_parquet(
            parquet_buffer, 
            engine='pyarrow', 
            index=False,
            compression='snappy'
        )
        parquet_buffer.seek(0)
        
        # Upload to S3
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=parquet_buffer.getvalue(),
            ContentType='application/x-parquet'
        )
        
        logger.debug(f"Uploaded {len(df)} rows to s3://{self.bucket}/{s3_key}")

