import yfinance as yf
import pandas as pd


class YahooFinanceEODExtract:

    def __init__(self):
        pass

    def get_historical_price(
        self,
        ticker : str,
        period : str = "max",
        start : str | None = None,
        end : str | None = None
        ) -> pd.DataFrame:

        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(
            start = start, 
            end = end, 
            interval = "1mo", 
            period = period, 
            auto_adjust = False)
        return df.reset_index()

    def get_dividends(self, ticker : str) -> pd.DataFrame:
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.dividends.reset_index()

    def get_splits(self, ticker : str) -> pd.DataFrame:
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.splits.reset_index()

