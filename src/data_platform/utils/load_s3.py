from io import BytesIO
from typing import Optional
import boto3
import pandas as pd


def write_parquet_to_s3(
    s3_client: boto3.session.Session.client,
    df: pd.DataFrame,
    bucket: str,
    key: str,
    compression: str = "snappy",
) -> None:
    
    parquet_buffer = BytesIO()
    df.to_parquet(
        parquet_buffer,
        engine="pyarrow",
        compression=compression,
        index=False,
    )
    parquet_buffer.seek(0)
    s3_client.put_object(Bucket=bucket, Key=key, Body=parquet_buffer)
    
