# Quick test to check what quarterly data is available
from fundamental_helper import BaseFinanceLoader
import pandas as pd

ticker = "AAPL"
loader = BaseFinanceLoader(ticker)

# Check quarterly data
income, balance, cashflow = loader.get_quarterly_statements()

print("=" * 60)
print("QUARTERLY DATA AVAILABILITY")
print("=" * 60)
print(f"\nIncome Statement - Shape: {income.shape}")
print(f"Date Range: {income.columns.min()} to {income.columns.max()}")
print(f"Quarters Available: {len(income.columns)}")
print(f"\nQuarterly dates:\n{income.columns.tolist()}")

print(f"\nBalance Sheet - Shape: {balance.shape}")
print(f"Date Range: {balance.columns.min()} to {balance.columns.max()}")

print(f"\nCash Flow - Shape: {cashflow.shape}")
print(f"Date Range: {cashflow.columns.min()} to {cashflow.columns.max()}")

# Check price data
price_hist, shares = loader.get_price_and_shares()
print("\n" + "=" * 60)
print("PRICE & SHARES DATA")
print("=" * 60)
print(f"Price History - Shape: {price_hist.shape}")
print(f"Date Range: {price_hist.index.min()} to {price_hist.index.max()}")
print(f"Sample prices:\n{price_hist.tail()}")

print(f"\nShares - Shape: {shares.shape}")
print(f"Date Range: {shares.index.min()} to {shares.index.max()}")
print(f"Sample shares:\n{shares.tail()}")
