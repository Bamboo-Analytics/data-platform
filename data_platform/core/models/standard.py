"""Standard platform data models that all APIs map to."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OHLCV(BaseModel):
    """
    Standardized OHLCV (Open, High, Low, Close, Volume) model.
    All API connectors must transform their data to this format.
    """
    ticker: str = Field(..., description="Stock ticker symbol")
    timestamp: datetime = Field(..., description="Timestamp of the data point")
    open: float = Field(..., description="Opening price", gt=0)
    high: float = Field(..., description="Highest price", gt=0)
    low: float = Field(..., description="Lowest price", gt=0)
    close: float = Field(..., description="Closing price", gt=0)
    volume: float = Field(..., description="Trading volume", ge=0)
    source: str = Field(..., description="Data source (e.g., 'yfinance', 'polygon')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "timestamp": "2024-12-27T16:00:00",
                "open": 195.23,
                "high": 196.50,
                "low": 194.80,
                "close": 196.10,
                "volume": 45000000.0,
                "source": "yfinance"
            }
        }


class AssetInfo(BaseModel):
    """
    Standardized asset information model.
    All API connectors must transform their asset data to this format.
    """
    ticker: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Company/asset name")
    asset_type: str = Field(..., description="Asset type: stock, etf, crypto, mutual_fund, etc.")
    exchange: Optional[str] = Field(None, description="Exchange where asset is traded")
    currency: Optional[str] = Field(None, description="Trading currency")
    sector: Optional[str] = Field(None, description="Business sector")
    industry: Optional[str] = Field(None, description="Industry classification")
    market_cap: Optional[float] = Field(None, description="Market capitalization", ge=0)
    description: Optional[str] = Field(None, description="Company/asset description")
    last_dividend: Optional[float] = Field(None, description="Most recent dividend amount", ge=0)
    last_split: Optional[str] = Field(None, description="Most recent stock split (e.g., '2:1')")
    source: str = Field(..., description="Data source (e.g., 'yfinance', 'polygon')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "asset_type": "stock",
                "exchange": "NASDAQ",
                "currency": "USD",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "market_cap": 3000000000000.0,
                "description": "Apple Inc. designs, manufactures, and markets smartphones...",
                "last_dividend": 0.24,
                "last_split": "4:1",
                "source": "yfinance"
            }
        }

