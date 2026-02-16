"""
OHLCV Data Ingestion Module
Fetches OHLCV data from Yahoo Finance and uploads to S3.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List
from io import BytesIO

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yfinance as yf
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

def get_s3_client():
    """Initialize and return S3 client using credentials from .env"""
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv("MY_AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("MY_AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("MY_AWS_DEFAULT_REGION", "us-east-2")
    )


def fetch_ohlcv(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Fetch OHLCV data for a given symbol using yfinance.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'GOOGL')
        start_date: Start date in 'YYYY-MM-DD' format (defaults to 30 days ago)
        end_date: End date in 'YYYY-MM-DD' format (defaults to today)
        interval: Data interval (1d, 1h, 5m, etc.)
    
    Returns:
        DataFrame with OHLCV data
    """
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    print(f"Fetching {symbol} from {start_date} to {end_date}")
    
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start_date, end=end_date, interval=interval)
    
    if df.empty:
        print(f"No data found for {symbol}")
        return df
    
    df.reset_index(inplace=True)
    df['symbol'] = symbol
    df['ingestion_timestamp'] = datetime.now()
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    
    print(f"Fetched {len(df)} records for {symbol}")
    return df


def write_parquet_in_chunks(
    df: pd.DataFrame,
    buffer: BytesIO,
    chunk_size: int = 10000,
) -> None:
    """
    Write a DataFrame to a parquet buffer in row chunks.

    Args:
        df: DataFrame to serialize
        buffer: Target in-memory bytes buffer
        chunk_size: Number of rows per parquet write
    """
    if chunk_size <= 0:
        raise ValueError("parquet_chunk_size must be a positive integer")

    writer = None
    chunk_count = 0
    try:
        for start in range(0, len(df), chunk_size):
            end = start + chunk_size
            chunk_df = df.iloc[start:end]
            table = pa.Table.from_pandas(chunk_df, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(buffer, table.schema)
            writer.write_table(table)
            chunk_count += 1
    finally:
        if writer is not None:
            writer.close()

    print(
        f"Wrote parquet incrementally in {chunk_count} chunk(s) "
        f"(chunk_size={chunk_size}, rows={len(df)})"
    )


def upload_to_s3(
    df: pd.DataFrame,
    partition_date: str,
    bucket_name: Optional[str] = None,
    prefix: str = "raw",
    source: str = "yahoo",
    dataset: str = "ohlcv_1d",
    file_format: str = "parquet",
    parquet_chunk_size: int = 10000,
) -> str:
    """
    Upload DataFrame to S3.
    
    Args:
        df: DataFrame containing OHLCV data
        partition_date: Date partition value (YYYY-MM-DD)
        bucket_name: S3 bucket name (defaults to env var)
        prefix: Base S3 prefix (e.g. 'raw')
        source: Data source partition value
        dataset: Dataset partition value
        file_format: File format ('parquet' or 'csv')
        parquet_chunk_size: Number of rows written per parquet chunk
    
    Returns:
        S3 URI of uploaded file
    """
    if df.empty:
        print("DataFrame is empty, skipping upload")
        return ""
    
    bucket_name = bucket_name or os.getenv("MY_AWS_BUCKET_NAME")
    try:
        partition_dt = datetime.strptime(partition_date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("partition_date must be in YYYY-MM-DD format") from exc

    year = partition_dt.strftime("%Y")
    month = partition_dt.strftime("%m")
    filename = f"{dataset}_{partition_date}.{file_format}"
    s3_key = (
        f"{prefix}/source={source}/dataset={dataset}/year={year}/"
        f"month={month}/{filename}"
    )
    
    buffer = BytesIO()
    if file_format == "parquet":
        write_parquet_in_chunks(df, buffer, chunk_size=parquet_chunk_size)
    elif file_format == "csv":
        df.to_csv(buffer, index=False)
    else:
        raise ValueError(f"Unsupported file format: {file_format}")
    
    buffer.seek(0)
    
    s3_client = get_s3_client()
    s3_client.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=buffer.getvalue(),
    )
    
    s3_uri = f"s3://{bucket_name}/{s3_key}"
    print(f"Uploaded to {s3_uri}")
    return s3_uri


def ingest_ohlcv(
    symbols: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = "1d",
    prefix: str = "raw",
    source: str = "yahoo",
    file_format: str = "parquet",
    parquet_chunk_size: int = 10000,
) -> List[str]:
    """
    Fetch OHLCV data and upload to S3.
    
    Args:
        symbols: List of stock ticker symbols
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        interval: Data interval
        prefix: Base S3 prefix
        source: Data source partition value
        file_format: File format ('parquet' or 'csv')
        parquet_chunk_size: Number of rows written per parquet chunk
    
    Returns:
        List of S3 URIs for uploaded files
    """
    s3_uris = []
    frames = []

    for symbol in symbols:
        df = fetch_ohlcv(symbol, start_date, end_date, interval)
        if not df.empty:
            frames.append(df)

    if not frames:
        print("\nIngestion complete. No data to upload")
        return s3_uris

    combined_df = pd.concat(frames, ignore_index=True)
    time_col = "date" if "date" in combined_df.columns else "datetime"
    if time_col not in combined_df.columns:
        raise ValueError("Expected a 'date' or 'datetime' column in OHLCV data")

    combined_df[time_col] = pd.to_datetime(combined_df[time_col], errors="coerce")
    combined_df = combined_df.dropna(subset=[time_col]).copy()
    ingest_ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    combined_df["source"] = source
    combined_df["ingestion_ts"] = ingest_ts
    combined_df["partition_date"] = combined_df[time_col].dt.strftime("%Y-%m-%d")
    dataset = f"ohlcv_{interval}"

    for partition_date, partition_df in combined_df.groupby("partition_date", sort=True):
        s3_uri = upload_to_s3(
            partition_df.drop(columns=["partition_date"]),
            partition_date=partition_date,
            prefix=prefix,
            source=source,
            dataset=dataset,
            file_format=file_format,
            parquet_chunk_size=parquet_chunk_size,
        )
        s3_uris.append(s3_uri)

    print(
        f"\nIngestion complete. Uploaded {len(s3_uris)} daily file(s) "
        f"for {len(symbols)} symbols"
    )
    return s3_uris
