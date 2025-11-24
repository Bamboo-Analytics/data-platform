import boto3
from dotenv import load_dotenv
import polars as pl
from io import BytesIO

class S3Loader:

    def __init__(
        self, 
        api_key : str, 
        secret : str, 
        region : str, 
        bucket : str
        ) -> None:

        self.bucket = bucket
        self.s3_client = boto3.client('s3', 
            aws_access_key_id = api_key, 
            aws_secret_access_key = secret, 
            region_name = region)
    
    def load_to_s3(self, df : pl.DataFrame, key : str) -> None:
        buffer = BytesIO()
        df.write_parquet(buffer)
        buffer.seek(0)
        self.s3_client.put_object(Bucket = self.bucket, Key = key, Body = buffer)