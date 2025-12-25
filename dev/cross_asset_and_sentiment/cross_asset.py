import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np
import investpy

end_date = datetime.now()
start_date = end_date - timedelta(days=5*365)

fx_pairs = [
    "EUR/USD",
    "USD/JPY",
    "USD/CNH",
    "USD/CNY",
    "USD/KRW",
    "USD/TWD",
    "USD/INR",
    "USD/BRL",
    "USD/MXN",
    "USD/CAD",
    "USD/CLP",
    "AUD/USD",
    "USD/NOK",
    "USD/RUB",
    "USD/GBP",
    "USD/CHF"
]

def get_sp500_return(start_date, end_date):
    """Return S&P 500 daily close price and percentage returns."""
    df = yf.download('^GSPC', start=start_date, end=end_date, progress=False, auto_adjust=True)
    # Prefer Close column and flatten if needed
    price = df['Close'].squeeze()
    returns = price.pct_change()
    return pd.DataFrame({'sp500_price': price, 'sp500_return': returns})

def get_sector_etf_returns(start_date, end_date):
    """Get sector ETF returns for XLK (Tech), XLF (Financials), XLE (Energy)"""
    tickers = ['XLK','XLF','XLE']
    data = yf.download(tickers, start=start_date, end=end_date, progress=False, auto_adjust=True)
    sector_data = pd.DataFrame()
    for t, name in zip(tickers, ['tech', 'financials', 'energy']):
        # Handle MultiIndex when multiple tickers
        price = data['Close'][t]
        sector_data[f'xlk_{name}_price' if t == 'XLK' else f'xlf_{name}_price' if t == 'XLF' else f'xle_{name}_price'] = price
        sector_data[f'xlk_{name}_return' if t == 'XLK' else f'xlf_{name}_return' if t == 'XLF' else f'xle_{name}_return'] = price.pct_change()
    return sector_data


def get_oil_price(start_date, end_date):
    """Get WTI crude oil price and returns"""
    oil = yf.download('CL=F', start=start_date, end=end_date, progress=False, auto_adjust=True)
    price = oil['Close'].squeeze()
    return pd.DataFrame({'oil_price': price, 'oil_return': price.pct_change()})

def get_gold_price(start_date, end_date):
    """Get gold price and returns"""
    gold = yf.download('GC=F', start=start_date, end=end_date, progress=False, auto_adjust=True)
    price = gold['Close'].squeeze()
    return pd.DataFrame({'gold_price': price, 'gold_return': price.pct_change()})


def get_usd_index(start_date, end_date):
    """Get US Dollar Index (DXY)"""
    usd = yf.download('DX-Y.NYB', start=start_date, end=end_date, progress=False, auto_adjust=True)
    price = usd['Close'].squeeze()
    return pd.DataFrame({'usd_index': price, 'usd_return': price.pct_change()})

def get_btc_correlation(start_date, end_date, ticker='^GSPC', window=30):
    """Compute BTC returns and rolling correlation with a given stock/Index.
    Returns data only for dates when both BTC and the stock traded.
    
    Parameters:
    - start_date, end_date: date range
    - ticker: stock or index ticker (e.g., 'AAPL', '^GSPC')
    - window: rolling window size in days
    
    Returns:
    - DataFrame with columns: btc_price, btc_return, btc_<ticker>_corr_<window>d
    """
    # Fetch extra days before start_date to have enough data for rolling window
    # Need more buffer for business days: ~50 calendar days for 30 business days
    extended_start = start_date - timedelta(days=int(window * 1.5) + 10)
    
    btc = yf.download('BTC-USD', start=extended_start, end=end_date, progress=False, auto_adjust=True)
    stock = yf.download(ticker, start=extended_start, end=end_date, progress=False, auto_adjust=True)
    
    btc_price = btc['Close'].squeeze()
    stock_price = stock['Close'].squeeze()
    
    btc_ret = btc_price.pct_change()
    stock_ret = stock_price.pct_change()
    
    # Align on common dates (intersection of both trading days)
    ret_df = pd.DataFrame({'btc_ret': btc_ret, 'stock_ret': stock_ret}).dropna()
    
    # Compute rolling correlation on aligned returns
    ret_df['corr'] = ret_df['btc_ret'].rolling(window=window, min_periods=window).corr(ret_df['stock_ret'])
    
    # Get BTC price for the aligned dates
    ret_df['btc_price'] = btc_price.reindex(ret_df.index)
    
    # Trim back to original date range
    ret_df = ret_df.loc[start_date:]
    
    corr_col = f"btc_{ticker.replace('^','').lower()}_corr_{window}d"
    return ret_df[['btc_price', 'btc_ret', 'corr']].rename(columns={'btc_ret': 'btc_return', 'corr': corr_col})


def get_treasury_yields(start_date, end_date):
    """Get Treasury yields for 2-year, 5-year, and 10-year"""
    treasury_data = pd.DataFrame()
    # 2Y: try ^2YY, fallback to ^UST2Y (if available)
    for t, col in [('^IRX','treasury_3m_yld_idx'), ('2YY=F','treasury_2y_yld'), ('ZT=F','treasury_2y_price'), ('^FVX','treasury_5y_yld_idx'), ('ZF=F','treasury_5y_price'), ('^TNX','treasury_10y_yld_idx'), ('ZN=F','treasury_10y_price')]:
        try:
            df = yf.download(t, start=start_date, end=end_date, progress=False, auto_adjust=True)
            if not df.empty:
                if 'Close' in df.columns:
                    price = df['Close']
                else:
                    price = df.squeeze()
                treasury_data[col] = price
        except Exception:
            pass
    return treasury_data


def get_credit_spreads(start_date, end_date):
    """Get High-Yield and Investment-Grade credit spreads (ETF proxy)"""
    data = yf.download(['HYG','LQD','AGG'], start=start_date, end=end_date, progress=False, auto_adjust=True)
    if isinstance(data.columns, pd.MultiIndex):
        hyg = data['Close']['HYG']
        lqd = data['Close']['LQD']
        agg = data['Close']['AGG']
    else:
        # Rare case when MultiIndex not returned; fetch individually
        hyg = yf.download('HYG', start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
        lqd = yf.download('LQD', start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
        agg = yf.download('AGG', start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    hy_ret = hyg.pct_change()
    ig_ret = lqd.pct_change()
    agg_ret = agg.pct_change()
    hy_spread = (hy_ret - agg_ret).cumsum()
    ig_spread = (ig_ret - agg_ret).cumsum()
    return pd.DataFrame({'hy_spread': hy_spread, 'ig_spread': ig_spread, 'hy_return': hy_ret, 'ig_return': ig_ret})


def get_fx_pairs(start_date, end_date, fx_pairs):
    """
    Get daily prices for a list of foreign exchange pairs.
    Falls back to investpy if Yahoo Finance doesn't have the data.
    
    Parameters:
    - start_date: Start date for data collection
    - end_date: End date for data collection
    - fx_pairs: List of FX pairs in format like "EUR/USD", "USD/JPY", etc.
    
    Returns:
    - DataFrame with daily prices for all FX pairs
    """
    import investpy
    
    fx_data = pd.DataFrame()
    
    for pair in fx_pairs:
        # Try Yahoo Finance first
        ticker = pair.replace("/", "") + "=X"
        col_name = pair.replace("/", "_").lower()
        
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
            if not df.empty and len(df) > 10:  # Check if we have meaningful data
                if 'Close' in df.columns:
                    price = df['Close'].squeeze()
                else:
                    price = df.squeeze()
                fx_data[f'{col_name}_price'] = price
                fx_data[f'{col_name}_return'] = price.pct_change()
                print(f"✓ {pair} fetched from Yahoo Finance")
            else:
                raise ValueError(f"Insufficient data from Yahoo Finance for {pair}")
        except Exception as yf_error:
            # Fallback to investpy
            try:
                print(f"⚠ Yahoo Finance failed for {pair}, trying investpy...")
                # Format dates for investpy (DD/MM/YYYY)
                from_date = start_date.strftime('%d/%m/%Y')
                to_date = end_date.strftime('%d/%m/%Y')
                
                df_investpy = investpy.get_currency_cross_historical_data(
                    currency_cross=pair,
                    from_date=from_date,
                    to_date=to_date
                )
                
                if not df_investpy.empty:
                    price = df_investpy['Close']
                    fx_data[f'{col_name}_price'] = price
                    fx_data[f'{col_name}_return'] = price.pct_change()
                    print(f"✓ {pair} fetched from investpy")
                else:
                    print(f"✗ No data available for {pair} from either source")
            except Exception as inv_error:
                print(f"✗ Error fetching {pair} from both sources:")
                print(f"  Yahoo Finance: {yf_error}")
                print(f"  investpy: {inv_error}")
    
    return fx_data

