# finance_helpers.py

import pandas as pd
import yfinance as yf
from typing import Tuple


def get_row(df: pd.DataFrame, candidates) -> pd.Series:
    """
    Return the first matching row for any name in `candidates`.
    If none found, return an empty Series with the same columns.
    """
    for name in candidates:
        if name in df.index:
            return df.loc[name]
    # nothing found – return empty series
    return pd.Series(index=df.columns, dtype="float64")


def align_to_dates(series: pd.Series, dates) -> pd.Series:
    """
    For each date in `dates`, pick the last available value in `series`
    at or before that date (forward-looking alignment for factors).
    """
    series = series.sort_index()
    
    # Ensure both series index and dates have compatible timezones
    if hasattr(series.index, 'tz') and series.index.tz is not None:
        # Series index is timezone-aware, convert dates to same timezone
        dates = pd.DatetimeIndex(dates).tz_localize(series.index.tz) if pd.DatetimeIndex(dates).tz is None else pd.DatetimeIndex(dates).tz_convert(series.index.tz)
    elif hasattr(pd.DatetimeIndex(dates), 'tz') and pd.DatetimeIndex(dates).tz is not None:
        # Dates are timezone-aware but series is not, remove timezone from dates
        dates = pd.DatetimeIndex(dates).tz_localize(None)
    
    aligned = {}
    for d in dates:
        s = series[series.index <= d]
        aligned[d] = s.iloc[-1] if not s.empty else pd.NA
    return pd.Series(aligned)


class BaseFinanceLoader:
    """
    Small helper class around yfinance.Ticker so the rest of your code
    doesn’t worry about low-level loading details.
    """

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.yf_ticker = yf.Ticker(ticker)

    def get_quarterly_statements(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Returns (income_stmt, balance_sheet, cashflow) as quarterly DataFrames.
        Tries the newer get_* API first, falls back to older quarterly attributes.
        """
        t = self.yf_ticker

        # newer API (yfinance ≥ 0.2.40) - quarterly frequency
        try:
            income = t.get_income_stmt(freq="quarterly")
            balance = t.get_balance_sheet(freq="quarterly")
            cashflow = t.get_cash_flow(freq="quarterly")
        except AttributeError:
            # older API - use quarterly attributes
            income = t.quarterly_income_stmt
            balance = t.quarterly_balance_sheet
            cashflow = t.quarterly_cashflow

        return income, balance, cashflow
    
    def get_annual_statements(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Returns (income_stmt, balance_sheet, cashflow) as annual DataFrames.
        Kept for backward compatibility, but quarterly is now the default.
        """
        t = self.yf_ticker

        # newer API (yfinance ≥ 0.2.40) - yearly frequency
        try:
            income = t.get_income_stmt(freq="yearly")
            balance = t.get_balance_sheet(freq="yearly")
            cashflow = t.get_cash_flow(freq="yearly")
        except AttributeError:
            # older API - use annual attributes
            income = t.income_stmt
            balance = t.balance_sheet
            cashflow = t.cashflow

        return income, balance, cashflow

    def get_price_and_shares(self):
        """
        Returns (price_history, shares_series) for the entire available history.
        """
        t = self.yf_ticker

        price_hist = t.history(period="max")["Close"]

        # some tickers may not support get_shares_full; fall back to current
        try:
            shares_df = t.get_shares_full(start=price_hist.index.min().strftime("%Y-%m-%d"))
            shares_series = shares_df.squeeze() if isinstance(shares_df, pd.DataFrame) else shares_df
        except Exception:
            info = t.get_info()
            current_shares = info.get("sharesOutstanding")
            shares_series = pd.Series(current_shares, index=price_hist.index)

        return price_hist, shares_series