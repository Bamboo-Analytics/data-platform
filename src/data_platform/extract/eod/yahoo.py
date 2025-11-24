from .base import BaseEOD
import yfinance as yf
import polars as pl

class YahooFinanceEOD(BaseEOD):

    def __init__(self):
        super().__init__()

    def get_historical_price(self, 
        ticker : str, 
        period : str = "max",
        start : str | None = None, 
        end : str | None = None
        ) -> pl.DataFrame:
        ()
        
        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(
            start = start, 
            end = end, 
            interval = "1mo", 
            period = period, 
            auto_adjust = False)

        df = pl.from_pandas(df)
        df = df.select(
            pl.col("Date").dt.date().alias("date"),
            pl.col("Open").cast(pl.Float64).alias("open"),
            pl.col("High").cast(pl.Float64).alias("high"),
            pl.col("Low").cast(pl.Float64).alias("low"),
            pl.col("Close").cast(pl.Float64).alias("close"),
            pl.col("Adj Close").cast(pl.Float64).alias("adj_close"),
            pl.col("Volume").cast(pl.Int64).alias("volume")
        )
        df = df.select("date", "open", "high", "low", "close", "adj_close", "volume")
        return df