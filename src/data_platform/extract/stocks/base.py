from abc import ABC, abstractmethod
import polars as pl



class TickerAPI(ABC):
    """
    Abstract base class for extracting ticker information.
    
    This class defines the interface for all ticker information extractors.
    All methods that return dataframes should return Polars DataFrames.
    """

    def __init__(self, api):
        """
        Initialize with an API client.
        
        Args:
            api: API client instance (e.g., yf.Ticker, polygon client, etc.)
        """
        self.api = api
    

    @abstractmethod
    def get_info(self, ticker: str) -> dict:
        """
        Get basic ticker information.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        
        Returns:
            Dictionary with ticker information (name, sector, market cap, etc.)
        """
        pass

    @abstractmethod
    def get_ohlcv(
        self, 
        ticker : str, 
        frequency : str,
        start : str | None = None, 
        end : str | None = None) -> pl.DataFrame:

        pass

    @abstractmethod
    def get_financials(self, ticker: str) -> dict[str, pl.DataFrame]:
        """
        Get financial statements.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with keys 'income_statement', 'balance_sheet', 'cash_flow'
            Each value is a Polars DataFrame
        """
        pass

    @abstractmethod
    def get_recommendations(self, ticker: str) -> pl.DataFrame:
        """
        Get analyst recommendations.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Polars DataFrame with analyst recommendations
        """
        pass

    @abstractmethod
    def get_calendar(self, ticker: str) -> pl.DataFrame:
        """
        Get earnings calendar.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Polars DataFrame with earnings calendar
        """
        pass