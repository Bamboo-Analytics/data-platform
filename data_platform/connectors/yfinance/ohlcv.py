"""YFinance connector for fetching and validating data from Yahoo Finance API."""
import logging
from datetime import datetime
from typing import List, Optional
import yfinance as yf
import pandas as pd
from data_platform.core.s
    YFinanceOHLCV,
    YFinanceInfo,
    YFinanceDividend,
    YFinanceSplit
)

logger = logging.getLogger(__name__)


class YFinanceConnector:
    """
    Fetches data from Yahoo Finance API and validates the response format.
    Returns YFinance-specific models that match the API's structure.
    """
    
    REQUIRED_OHLCV_FIELDS = ['Open', 'High', 'Low', 'Close', 'Volume']
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize YFinance connector.
        
        Args:
            config: Optional configuration dict (reserved for future use)
        """
        self.config = config or {}
    
    def fetch_ohlcv(
        self, 
        ticker: str, 
        start_date: datetime, 
        end_date: datetime,
        interval: str = '1d'
    ) -> List[YFinanceOHLCV]:
        """
        Fetch OHLCV data from Yahoo Finance.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for data
            end_date: End date for data
            interval: Data interval (1d, 1h, etc.)
        
        Returns:
            List of YFinanceOHLCV models
            
        Raises:
            ValueError: If API response format is invalid
        """
        logger.info(f"Fetching OHLCV for {ticker} from {start_date} to {end_date}")
        
        # Fetch from yfinance
        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(
            start=start_date,
            end=end_date,
            interval=interval
        )
        
        if df.empty:
            logger.warning(f"No OHLCV data returned for {ticker}")
            return []
        
        # Validate response format
        self._validate_ohlcv_dataframe(df)
        
        logger.debug(f"Fetched {len(df)} OHLCV records for {ticker}")
        logger.debug(f"Available columns: {df.columns.tolist()}")
        
        # Convert to YFinance models
        return self._dataframe_to_ohlcv_models(df)
    
    def fetch_info(self, ticker: str) -> YFinanceInfo:
        """
        Fetch asset information from Yahoo Finance.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            YFinanceInfo model
            
        Raises:
            ValueError: If API response is invalid
        """
        logger.info(f"Fetching asset info for {ticker}")
        
        ticker_obj = yf.Ticker(ticker)
        info_dict = ticker_obj.info
        
        if not info_dict or 'symbol' not in info_dict:
            raise ValueError(f"Invalid or empty info response for {ticker}")
        
        logger.debug(f"Fetched info for {ticker}: {info_dict.get('longName', 'N/A')}")
        
        # Validate and return as model
        return YFinanceInfo(**info_dict)
    
    def fetch_dividends(self, ticker: str) -> List[YFinanceDividend]:
        """
        Fetch dividend history from Yahoo Finance.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            List of YFinanceDividend models
        """
        logger.info(f"Fetching dividends for {ticker}")
        
        ticker_obj = yf.Ticker(ticker)
        div_series = ticker_obj.dividends
        
        if div_series.empty:
            logger.debug(f"No dividend history for {ticker}")
            return []
        
        # Convert to models
        dividends = []
        for date, amount in div_series.items():
            dividends.append(YFinanceDividend(
                Date=date.to_pydatetime(),
                Dividends=float(amount)
            ))
        
        logger.debug(f"Fetched {len(dividends)} dividend records for {ticker}")
        return dividends
    
    def fetch_splits(self, ticker: str) -> List[YFinanceSplit]:
        """
        Fetch stock split history from Yahoo Finance.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            List of YFinanceSplit models
        """
        logger.info(f"Fetching splits for {ticker}")
        
        ticker_obj = yf.Ticker(ticker)
        splits_series = ticker_obj.splits
        
        if splits_series.empty:
            logger.debug(f"No split history for {ticker}")
            return []
        
        # Convert to models
        splits = []
        for date, ratio in splits_series.items():
            # Format ratio (e.g., 2.0 becomes "2:1")
            split_str = self._format_split_ratio(float(ratio))
            splits.append(YFinanceSplit(
                Date=date.to_pydatetime(),
                Stock_Splits=split_str
            ))
        
        logger.debug(f"Fetched {len(splits)} split records for {ticker}")
        return splits
    
    def _validate_ohlcv_dataframe(self, df: pd.DataFrame):
        """
        Validate that DataFrame has required OHLCV fields.
        
        Raises:
            ValueError: If required fields are missing
        """
        missing_fields = [
            field for field in self.REQUIRED_OHLCV_FIELDS 
            if field not in df.columns
        ]
        
        if missing_fields:
            raise ValueError(
                f"YFinance API format changed! Missing required fields: {missing_fields}. "
                f"Available fields: {df.columns.tolist()}"
            )
    
    def _dataframe_to_ohlcv_models(self, df: pd.DataFrame) -> List[YFinanceOHLCV]:
        """
        Convert pandas DataFrame to list of YFinanceOHLCV models.
        
        Args:
            df: DataFrame with OHLCV data (Date as index)
            
        Returns:
            List of validated YFinanceOHLCV models
        """
        records = []
        
        for date, row in df.iterrows():
            try:
                record = YFinanceOHLCV(
                    Date=date.to_pydatetime() if hasattr(date, 'to_pydatetime') else date,
                    Open=float(row['Open']),
                    High=float(row['High']),
                    Low=float(row['Low']),
                    Close=float(row['Close']),
                    Volume=int(row['Volume'])
                )
                records.append(record)
            except (KeyError, ValueError, TypeError) as e:
                logger.error(f"Failed to convert row at {date}: {e}")
                raise ValueError(f"Failed to parse OHLCV data at {date}: {e}")
        
        return records
    
    @staticmethod
    def _format_split_ratio(ratio: float) -> str:
        """
        Format split ratio for display.
        
        Args:
            ratio: Split ratio (e.g., 2.0 for 2-for-1 split)
            
        Returns:
            Formatted string (e.g., "2:1")
        """
        if ratio >= 1:
            return f"{int(ratio)}:1"
        else:
            # Reverse split (e.g., 0.5 becomes "1:2")
            return f"1:{int(1/ratio)}"

