from data_platform.ingestion.yahoo_finance import get_eod_from_yahoo
from data_platform.utils.load_s3 import write_parquet_to_s3
import boto3
from datetime import datetime


def handler(event, context):
    ticker = event["ticker"]
    start_date = event["start_date"]
    end_date = event["end_date"]
    bucket = event["bucket"]
 
    s3_client = boto3.client("s3")
    df = get_eod_from_yahoo(ticker, start_date, end_date)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    s3_key = f"yahoo_finance/{ticker}/{ticker}_{start_date}_{end_date}_{timestamp}.parquet"
    

    write_parquet_to_s3(
        s3_client=s3_client,
        df=df,
        bucket=bucket,
        key=s3_key
    )
    
    return {
        "statusCode": 200,
        "body": {
            "message": "Successfully fetched and uploaded data",
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "s3_location": f"s3://{bucket}/{s3_key}",
            "rows_uploaded": len(df)
        }
    }
