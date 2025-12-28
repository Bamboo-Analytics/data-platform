"""YFinance API-specific data models that match the API's response format."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class YFinanceOHLCV(BaseModel):
    """
    Model matching yfinance's DataFrame structure for OHLCV data.
    Field names match exactly what yfinance returns.
    """
    Date: datetime = Field(..., description="Trading date")
    Open: float = Field(..., description="Opening price")
    High: float = Field(..., description="Highest price")
    Low: float = Field(..., description="Lowest price")
    Close: float = Field(..., description="Closing price")
    Volume: int = Field(..., description="Trading volume")
    
    class Config:
        json_schema_extra = {
            "example": {
                "Date": "2024-12-27T00:00:00",
                "Open": 195.23,
                "High": 196.50,
                "Low": 194.80,
                "Close": 196.10,
                "Volume": 45000000
            }
        }


class YFinanceInfo(BaseModel):
    """
    Model matching yfinance's .info dict structure.
    Contains comprehensive asset information from Yahoo Finance.
    """
    symbol: str
    longName: Optional[str] = None
    shortName: Optional[str] = None
    quoteType: Optional[str] = None  # "EQUITY", "ETF", "CRYPTOCURRENCY", etc.
    exchange: Optional[str] = None
    currency: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    marketCap: Optional[int] = None
    longBusinessSummary: Optional[str] = None
    dividendRate: Optional[float] = None
    dividendYield: Optional[float] = None
    
    class Config:
        # Allow extra fields that yfinance might return
        extra = "allow"


class YFinanceDividend(BaseModel):
    """Model for dividend events from yfinance."""
    Date: datetime
    Dividends: float = Field(..., description="Dividend amount")


class YFinanceSplit(BaseModel):
    """Model for stock split events from yfinance."""
    Date: datetime
    Stock_Splits: str = Field(..., description="Split ratio (e.g., '2.0' for 2:1 split)")

