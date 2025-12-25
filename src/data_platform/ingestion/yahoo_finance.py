import yfinance as yf
import pandas as pd

def get_eod_from_yahoo(ticker: str, start_date: str | None = None, end_date : str | None = None):
    ticker = yf.Ticker(ticker)
    df = ticker.history(
        interval = "1d", 
        period = "max", 
        start=start_date, 
        end=end_date,
        auto_adjust = False)
    
    df = df.reset_index(drop = False)
    df = df.drop(["Dividends", "Stock Splits"], axis = 1)
    df = df.rename(columns = {
        "Date" : "date",
        "Open" : "open",
        "High" : "high",
        "Low" : "low",
        "Close" : "close",
        "Volume" : "volume",
        "Adj Close" : "adjusted_close",
    })
    return df



