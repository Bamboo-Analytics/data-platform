"""Lambda handler for YFinance data ingestion."""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from data_platform.ingestion.connectors.yfinance.connector import YFinanceConnector
from data_platform.ingestion.connectors.yfinance.mapper import YFinanceMapper
from data_platform.ingestion.storage.s3_writer import S3ParquetWriter

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    YFinance Lambda Handler for financial data ingestion.
    
    Expected event structure:
    {
        "data_type": "ohlcv" or "asset_info",
        "ticker": "AAPL",
        "start_date": "2024-01-01",  # Optional for OHLCV, required if incremental=false
        "end_date": "2024-12-31",    # Optional for OHLCV, defaults to now
        "incremental": true,          # Optional, defaults to true
        "interval": "1d"              # Optional for OHLCV, defaults to "1d"
    }
    
    Environment variables:
    - S3_BUCKET: Target S3 bucket for data storage (required)
    - AWS_REGION: AWS region (auto-provided by Lambda)
    
    Returns:
        Dict with statusCode and body containing ingestion results
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse and validate event
        data_type = event.get('data_type')
        ticker = event.get('ticker')
        
        if not data_type or not ticker:
            return build_error_response(
                400,
                "Missing required fields: 'data_type' and 'ticker' are required"
            )
        
        # Get S3 bucket from environment
        s3_bucket = os.getenv('S3_BUCKET')
        if not s3_bucket:
            return build_error_response(
                500,
                "S3_BUCKET environment variable not set"
            )
        
        # Initialize components
        connector = YFinanceConnector()
        mapper = YFinanceMapper()
        s3_writer = S3ParquetWriter(
            bucket=s3_bucket,
            region=os.getenv('AWS_REGION')
        )
        
        # Route to appropriate handler based on data type
        if data_type.lower() == 'ohlcv':
            return handle_ohlcv_ingestion(
                event, connector, mapper, s3_writer, ticker
            )
        elif data_type.lower() == 'asset_info':
            return handle_asset_info_ingestion(
                event, connector, mapper, s3_writer, ticker
            )
        else:
            return build_error_response(
                400,
                f"Unknown data_type: '{data_type}'. Valid values: 'ohlcv', 'asset_info'"
            )
    
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {e}", exc_info=True)
        return build_error_response(500, f"Internal error: {str(e)}")


def handle_ohlcv_ingestion(
    event: Dict[str, Any],
    connector: YFinanceConnector,
    mapper: YFinanceMapper,
    s3_writer: S3ParquetWriter,
    ticker: str
) -> Dict[str, Any]:
    """
    Handle OHLCV data ingestion.
    
    Args:
        event: Lambda event dict
        connector: YFinance connector instance
        mapper: YFinance mapper instance
        s3_writer: S3 writer instance
        ticker: Stock ticker symbol
        
    Returns:
        Lambda response dict
    """
    try:
        incremental = event.get('incremental', True)
        interval = event.get('interval', '1d')
        
        # Determine date range
        start_date = get_start_date(event, s3_writer, ticker, incremental)
        end_date = get_end_date(event)
        
        logger.info(
            f"Fetching OHLCV for {ticker} from {start_date} to {end_date} "
            f"(incremental={incremental}, interval={interval})"
        )
        
        # 1. Fetch from YFinance API (returns YFinance models)
        yf_ohlcv_list = connector.fetch_ohlcv(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )
        
        if not yf_ohlcv_list:
            logger.info(f"No new OHLCV data for {ticker}")
            return build_success_response({
                'message': 'No new data to ingest',
                'ticker': ticker,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'records': 0
            })
        
        # 2. Transform to platform standard models
        platform_ohlcv_list = mapper.to_ohlcv_list(yf_ohlcv_list, ticker)
        
        # 3. Write to S3
        s3_key = s3_writer.write_ohlcv(platform_ohlcv_list, ticker)
        
        logger.info(f"Successfully ingested {len(platform_ohlcv_list)} OHLCV records for {ticker}")
        
        return build_success_response({
            'message': 'OHLCV data ingested successfully',
            'ticker': ticker,
            'records': len(platform_ohlcv_list),
            's3_key': s3_key,
            's3_uri': f"s3://{s3_writer.bucket}/{s3_key}",
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'interval': interval,
            'incremental': incremental
        })
    
    except ValueError as e:
        logger.error(f"Validation error in OHLCV ingestion: {e}")
        return build_error_response(400, str(e))
    except Exception as e:
        logger.error(f"Error in OHLCV ingestion: {e}", exc_info=True)
        return build_error_response(500, f"Failed to ingest OHLCV data: {str(e)}")


def handle_asset_info_ingestion(
    event: Dict[str, Any],
    connector: YFinanceConnector,
    mapper: YFinanceMapper,
    s3_writer: S3ParquetWriter,
    ticker: str
) -> Dict[str, Any]:
    """
    Handle asset info ingestion.
    
    Args:
        event: Lambda event dict
        connector: YFinance connector instance
        mapper: YFinance mapper instance
        s3_writer: S3 writer instance
        ticker: Stock ticker symbol
        
    Returns:
        Lambda response dict
    """
    try:
        logger.info(f"Fetching asset info for {ticker}")
        
        # 1. Fetch from YFinance API (multiple sources)
        yf_info = connector.fetch_info(ticker)
        yf_dividends = connector.fetch_dividends(ticker)
        yf_splits = connector.fetch_splits(ticker)
        
        # 2. Transform to platform standard model (cherry-picks from multiple sources)
        platform_info = mapper.to_asset_info(
            yf_info=yf_info,
            dividends=yf_dividends,
            splits=yf_splits
        )
        
        # 3. Write to S3
        s3_key = s3_writer.write_asset_info(platform_info)
        
        logger.info(f"Successfully ingested asset info for {ticker}")
        
        return build_success_response({
            'message': 'Asset info ingested successfully',
            'ticker': ticker,
            'asset_name': platform_info.name,
            'asset_type': platform_info.asset_type,
            's3_key': s3_key,
            's3_uri': f"s3://{s3_writer.bucket}/{s3_key}"
        })
    
    except ValueError as e:
        logger.error(f"Validation error in asset info ingestion: {e}")
        return build_error_response(400, str(e))
    except Exception as e:
        logger.error(f"Error in asset info ingestion: {e}", exc_info=True)
        return build_error_response(500, f"Failed to ingest asset info: {str(e)}")


def get_start_date(
    event: Dict[str, Any],
    s3_writer: S3ParquetWriter,
    ticker: str,
    incremental: bool
) -> datetime:
    """
    Determine the start date for OHLCV fetch.
    
    Args:
        event: Lambda event dict
        s3_writer: S3 writer instance
        ticker: Stock ticker
        incremental: Whether to use incremental load
        
    Returns:
        Start date for data fetch
    """
    if incremental:
        # Try to get latest timestamp from S3
        latest_ts = s3_writer.get_latest_timestamp(
            ticker=ticker,
            data_type='ohlcv',
            source='yfinance'
        )
        
        if latest_ts:
            logger.info(f"Incremental load: starting from {latest_ts}")
            return latest_ts
        else:
            # No existing data, use provided start_date or default
            start_date_str = event.get('start_date')
            if start_date_str:
                return datetime.fromisoformat(start_date_str)
            else:
                # Default to 1 year ago
                default_start = datetime.now().replace(year=datetime.now().year - 1)
                logger.info(f"No existing data, using default start date: {default_start}")
                return default_start
    else:
        # Non-incremental, must provide start_date
        start_date_str = event.get('start_date')
        if not start_date_str:
            raise ValueError("start_date is required when incremental=false")
        return datetime.fromisoformat(start_date_str)


def get_end_date(event: Dict[str, Any]) -> datetime:
    """
    Get end date from event or default to now.
    
    Args:
        event: Lambda event dict
        
    Returns:
        End date for data fetch
    """
    end_date_str = event.get('end_date')
    if end_date_str:
        return datetime.fromisoformat(end_date_str)
    return datetime.utcnow()


def build_success_response(body: Dict[str, Any]) -> Dict[str, Any]:
    """Build successful Lambda response."""
    return {
        'statusCode': 200,
        'body': json.dumps(body, default=str)
    }


def build_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Build error Lambda response."""
    return {
        'statusCode': status_code,
        'body': json.dumps({
            'error': message
        })
    }

