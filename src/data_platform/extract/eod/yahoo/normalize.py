import pandas as pd
import polars as pl

class YahooFinanceEODNormalize:

    def __init__(self):
        pass

    def normalize_historical_price(self, df : pd.DataFrame) -> pl.DataFrame:
        
        df = pl.from_pandas(df)
        df = df.select(
            pl.col("Date").alias("timestamp"),
            pl.col("Open").cast(pl.Float64).alias("open"),
            pl.col("High").cast(pl.Float64).alias("high"),
            pl.col("Low").cast(pl.Float64).alias("low"),
            pl.col("Close").cast(pl.Float64).alias("close"),
            pl.col("Adj Close").cast(pl.Float64).alias("adj_close"),
            pl.col("Volume").cast(pl.Int64).alias("volume")
        )
        df = df.select("timestamp", "open", "high", "low", "close", "adj_close", "volume")
        return df
    
    def normalize_splits(self, df : pd.DataFrame) -> pl.DataFrame: 
        df = pl.from_pandas(df)
        df = df.select(pl.col("Date").alias("timestamp"), pl.col("Stock Splits").alias("stock_splits"))
        return df
    
    def normalize_dividends(self, df : pd.DataFrame) -> pl.DataFrame: 
        df = pl.from_pandas(df)
        df = df.select(pl.col("Date").alias("timestamp"), pl.col("Dividends").alias("dividends"))
        return df
