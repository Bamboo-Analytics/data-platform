import yfinance as yf
import pandas as pd


class YahooFinanceClient:

    def __init__(self):
        pass

    def get_historical_price(
        self,
        ticker : str, 
        interval : str = "1mo",
        period : str = "max",
        start : str | None = None, 
        end : str | None = None
    ) -> pd.DataFrame:


        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(start = start, end = end, interval = interval, period = period)
        return df.reset_index()

    def get_info(self, ticker : str) -> dict:
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.info

    def get_income_statement(self, ticker: str) -> pd.DataFrame:
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.income_stmt.reset_index()

    def get_balance_sheet(self, ticker: str) -> pd.DataFrame:
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.balance_sheet.reset_index()

    def get_cash_flow(self, ticker: str) -> pd.DataFrame:
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.cashflow.reset_index()

    def get_dividends(self, ticker: str) -> pd.DataFrame:
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.dividends.reset_index()

    def get_splits(self, ticker: str) -> pd.DataFrame:
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.splits.reset_index()

    def get_recommendations(self, ticker: str) -> pd.DataFrame:
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.recommendations.reset_index()

    def get_calendar(self, ticker: str) -> pd.DataFrame:
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.calendar.reset_index()

    def get_major_holders(self, ticker: str) -> pd.DataFrame:
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.major_holders.reset_index()

    def get_institutional_holders(self, ticker: str) -> pd.DataFrame:
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.institutional_holders.reset_index()
