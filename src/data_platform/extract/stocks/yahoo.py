import yfinance as yf
import polars as pl
from datetime import datetime
from .base import TickerAPI

class YahooFinanceAPI(TickerAPI):

    def __init__(self):
        super().__init__(api = None)

    def get_info(self, ticker: str) -> dict:
        pass

    def get_ohlcv(self, 
        ticker: str,
        frequency: str, 
        start: str | None = None, 
        end: str | None = None) -> pl.DataFrame:

        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(
            start = start, 
            end = end, 
            interval = frequency, 
            period = "max", 
            auto_adjust = False).reset_index()

        df = pl.from_pandas(df)
        df = df.select(
            pl.col("Date").dt.replace_time_zone("UTC").alias("date"),
            pl.col("Open").cast(pl.Float64).alias("open"),
            pl.col("High").cast(pl.Float64).alias("high"),
            pl.col("Low").cast(pl.Float64).alias("low"),
            pl.col("Close").cast(pl.Float64).alias("close"),
            pl.col("Adj Close").cast(pl.Float64).alias("adj_close"),
            pl.col("Volume").cast(pl.Int64).alias("volume")
        )
        df = df.select("date", "open", "high", "low", "close", "adj_close", "volume")
        return df

    def get_financials(self, ticker: str) -> dict[str, pl.DataFrame]:
        pass

    def get_recommendations(self, ticker: str) -> pl.DataFrame:
        pass

    def get_calendar(self, ticker: str) -> pl.DataFrame:
        pass