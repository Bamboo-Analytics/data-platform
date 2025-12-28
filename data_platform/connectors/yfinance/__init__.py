"""YFinance connector for fetching financial data from Yahoo Finance."""
from data_platform.ingestion.connectors.yfinance.connector import YFinanceConnector
from data_platform.ingestion.connectors.yfinance.mapper import YFinanceMapper

__all__ = ['YFinanceConnector', 'YFinanceMapper']

