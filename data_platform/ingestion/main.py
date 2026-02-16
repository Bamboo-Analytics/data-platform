from ingest import ingest_ohlcv


def main():
    symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
    
    s3_uris = ingest_ohlcv(
        symbols=symbols,
        interval="1d",
        file_format="parquet",
        prefix="raw",
        source="yahoo",
    )
    
    print("\nResults:")
    for uri in s3_uris:
        print(f"{uri}")


if __name__ == "__main__":
    main()
