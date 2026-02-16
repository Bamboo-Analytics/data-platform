"""
AWS Lambda handler for OHLCV data ingestion.
"""

import json
from typing import Dict, Any
from ingest import ingest_ohlcv
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function handler for OHLCV data ingestion.
    
    Expected event format:
    {
        "symbols": ["AAPL", "GOOGL", "MSFT"],
        "interval": "1d",  # optional, defaults to "1d"
        "start_date": "2024-01-01",  # optional, defaults to 30 days ago
        "end_date": "2024-12-31",  # optional, defaults to today
        "prefix": "raw",  # optional
        "source": "yahoo",  # optional, defaults to "yahoo"
        "file_format": "parquet",  # optional, defaults to "parquet"
        "parquet_chunk_size": 10000  # optional, defaults to 10000
    }
    
    Args:
        event: Lambda event payload containing ingestion parameters
        context: Lambda context object
    
    Returns:
        Response with status code and results
    """
    try:
        # Extract parameters from event
        symbols = event.get('symbols', [])
        
        if not symbols:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameter: symbols',
                    'message': 'Please provide a list of symbols to ingest'
                })
            }
        
        # Optional parameters with defaults
        interval = event.get('interval', '1d')
        start_date = event.get('start_date')
        end_date = event.get('end_date')
        prefix = event.get('prefix', 'raw')
        source = event.get('source', 'yahoo')
        file_format = event.get('file_format', 'parquet')
        parquet_chunk_size = int(event.get('parquet_chunk_size', 10000))
        if parquet_chunk_size <= 0:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid parameter: parquet_chunk_size',
                    'message': 'parquet_chunk_size must be a positive integer'
                })
            }
        
        print(f"Starting ingestion for {len(symbols)} symbols: {symbols}")
        
        # Run the ingestion
        s3_uris = ingest_ohlcv(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            prefix=prefix,
            source=source,
            file_format=file_format,
            parquet_chunk_size=parquet_chunk_size,
        )
        
        # Return success response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully ingested {len(s3_uris)} symbols',
                'symbols_processed': len(s3_uris),
                'total_symbols': len(symbols),
                's3_uris': s3_uris
            })
        }
        
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
