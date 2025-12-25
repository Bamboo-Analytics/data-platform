"""
Data models for the cross-asset data pipeline.

The main fact table uses (date, ticker) as unique identifiers.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class AssetClass(str, Enum):
    """Asset classification."""

    EQUITY_INDEX = "equity_index"
    EQUITY_ETF = "equity_etf"
    EQUITY_SINGLE = "equity_single"  # Individual stocks
    COMMODITY = "commodity"
    CRYPTOCURRENCY = "cryptocurrency"
    FX = "fx"
    FX_INDEX = "fx_index"
    FIXED_INCOME = "fixed_income"
    CREDIT = "credit"
    VOLATILITY = "volatility"  # VIX, VVIX, etc.
    ALTERNATIVE = "alternative"  # Alternative data (sentiment, etc.)
    MACRO_INDICATOR = "macro_indicator"  # GDP, CPI, unemployment, etc.


class Vendor(str, Enum):
    """Data vendor/source."""

    YAHOO_FINANCE = "yahoo_finance"
    INVESTPY = "investpy"
    FRED = "fred"  # Federal Reserve Economic Data
    POLYGON = "polygon"
    ALPHA_VANTAGE = "alpha_vantage"
    CBOE = "cboe"  # Chicago Board Options Exchange (VIX data)
    QUANDL = "quandl"
    TWITTER_API = "twitter_api"  # Sentiment analysis
    REDDIT_API = "reddit_api"  # Social sentiment
    NEWS_API = "news_api"  # News sentiment
    FEAR_GREED = "fear_greed"  # CNN Fear & Greed Index
    FINVIZ = "finviz"  # Market screener data
    GOOGLE_TRENDS = "google_trends"  # Search trends
    ALTERNATIVE_ME = "alternative_me"  # Crypto Fear & Greed
    GLASSNODE = "glassnode"  # On-chain crypto metrics
    COINMETRICS = "coinmetrics"  # Crypto market data


class FeatureType(str, Enum):
    """Type of feature/metric."""

    # Price & Returns
    PRICE = "price"
    RETURN = "return"
    LOG_RETURN = "log_return"
    
    # Fixed Income
    YIELD = "yield"
    SPREAD = "spread"
    DURATION = "duration"
    
    # Volume & Liquidity
    VOLUME = "volume"
    DOLLAR_VOLUME = "dollar_volume"
    BID_ASK_SPREAD = "bid_ask_spread"
    
    # Volatility
    REALIZED_VOL = "realized_volatility"
    IMPLIED_VOL = "implied_volatility"
    VOLATILITY_INDEX = "volatility_index"  # VIX, VVIX, etc.
    
    # Cross-Asset Metrics
    CORRELATION = "correlation"
    BETA = "beta"
    INDEX_VALUE = "index_value"
    
    # Sentiment & Alternative Data
    SENTIMENT_SCORE = "sentiment_score"  # Numeric sentiment (-1 to 1)
    FEAR_GREED_INDEX = "fear_greed_index"  # 0-100 scale
    SOCIAL_VOLUME = "social_volume"  # Mentions, tweets, posts
    NEWS_COUNT = "news_count"
    SEARCH_INTEREST = "search_interest"  # Google Trends
    
    # On-Chain Metrics (Crypto)
    ON_CHAIN_VOLUME = "on_chain_volume"
    ACTIVE_ADDRESSES = "active_addresses"
    HASH_RATE = "hash_rate"
    NETWORK_VALUE = "network_value"
    
    # Macro Indicators
    ECONOMIC_INDICATOR = "economic_indicator"  # GDP, CPI, etc.
    INTEREST_RATE = "interest_rate"
    UNEMPLOYMENT = "unemployment"
    INFLATION = "inflation"
    
    # Technical Indicators
    RSI = "rsi"
    MACD = "macd"
    MOVING_AVERAGE = "moving_average"
    BOLLINGER_BAND = "bollinger_band"


class AssetDataPoint(BaseModel):
    """
    Canonical data model for a single cross-asset data point.
    
    Primary key: (date, ticker)
    This represents one feature value for one ticker on one date.
    """

    model_config = ConfigDict(
        frozen=False,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    # Primary key components
    date: date = Field(
        ..., description="Trading date (UTC timezone normalized)"
    )
    ticker: str = Field(
        ..., 
        min_length=1,
        max_length=50,
        description="Unique ticker/symbol identifier (e.g., '^GSPC', 'EURUSD', 'BTC-USD')"
    )

    # Asset identification
    asset_class: AssetClass = Field(..., description="Asset class classification")
    symbol: str = Field(
        ..., 
        min_length=1,
        max_length=50,
        description="Human-readable symbol (may differ from ticker)"
    )

    # Feature identification
    feature_name: str = Field(
        ..., 
        min_length=1,
        max_length=100,
        description="Feature name (e.g., 'close_price', 'daily_return', 'hy_spread')"
    )
    feature_type: FeatureType = Field(..., description="Type of feature")

    # Value
    value: Optional[float] = Field(
        None, description="Numeric value (can be null for missing data)"
    )

    # Metadata
    currency: Optional[str] = Field(
        None, max_length=3, description="Currency code (ISO 4217)"
    )
    vendor: Vendor = Field(..., description="Data source/vendor")
    
    # Lineage and versioning
    ingestion_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this record was ingested (UTC)"
    )
    data_timestamp: datetime = Field(
        ..., description="When the data was published/became available (UTC)"
    )
    version: int = Field(
        default=1, ge=1, description="Version number for deduplication (higher = newer)"
    )

    # Additional metadata (JSON field in DB)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (vendor-specific fields, quality flags, etc.)"
    )

    @field_validator("date")
    @classmethod
    def validate_date_not_future(cls, v: date) -> date:
        """Ensure date is not in the future."""
        if v > date.today():
            raise ValueError(f"Date cannot be in the future: {v}")
        return v

    @field_validator("ticker", "symbol")
    @classmethod
    def validate_uppercase(cls, v: str) -> str:
        """Normalize tickers and symbols to uppercase."""
        return v.upper()

    @field_validator("value")
    @classmethod
    def validate_finite(cls, v: Optional[float]) -> Optional[float]:
        """Ensure value is finite (not inf or -inf)."""
        if v is not None and not (-1e15 < v < 1e15):
            raise ValueError(f"Value out of reasonable range: {v}")
        return v


class DailyFactRecord(BaseModel):
    """
    Fact table record with multiple features for a single (date, ticker).
    
    This is the flattened/wide format for ClickHouse storage.
    Each row represents all features for one ticker on one date.
    """

    model_config = ConfigDict(frozen=False)

    # Primary key
    date: date = Field(..., description="Trading date")
    ticker: str = Field(..., description="Ticker symbol")

    # Asset metadata (denormalized for query performance)
    asset_class: AssetClass
    symbol: str
    currency: Optional[str] = None

    # Price features
    close_price: Optional[float] = None
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None

    # Return features
    daily_return: Optional[float] = None
    log_return: Optional[float] = None
    volume: Optional[float] = None
    dollar_volume: Optional[float] = None

    # Spread/yield features (for fixed income and credit)
    yield_value: Optional[float] = None
    spread_value: Optional[float] = None
    duration: Optional[float] = None

    # Volatility features
    realized_volatility: Optional[float] = None
    implied_volatility: Optional[float] = None
    volatility_index: Optional[float] = None  # VIX, etc.

    # Correlation features (for crypto/cross-asset)
    correlation_30d: Optional[float] = None
    correlation_90d: Optional[float] = None
    beta: Optional[float] = None

    # Sentiment features
    sentiment_score: Optional[float] = None  # -1 to 1 scale
    fear_greed_index: Optional[float] = None  # 0-100 scale
    social_volume: Optional[float] = None  # Number of mentions
    news_count: Optional[float] = None
    search_interest: Optional[float] = None  # Google Trends

    # On-chain metrics (crypto)
    on_chain_volume: Optional[float] = None
    active_addresses: Optional[float] = None
    hash_rate: Optional[float] = None
    network_value: Optional[float] = None

    # Macro indicators
    economic_indicator: Optional[float] = None
    interest_rate: Optional[float] = None
    unemployment_rate: Optional[float] = None
    inflation_rate: Optional[float] = None

    # Technical indicators
    rsi: Optional[float] = None
    macd: Optional[float] = None
    moving_average_50: Optional[float] = None
    moving_average_200: Optional[float] = None

    # Lineage
    vendor: Vendor
    ingestion_timestamp: datetime = Field(default_factory=datetime.utcnow)
    data_timestamp: datetime
    version: int = Field(default=1)

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_data_points(
        cls, data_points: list[AssetDataPoint]
    ) -> Optional["DailyFactRecord"]:
        """
        Construct a DailyFactRecord from multiple AssetDataPoint instances.
        
        All data points must have the same (date, ticker).
        """
        if not data_points:
            return None

        # Validate all have same date and ticker
        first = data_points[0]
        if not all(dp.date == first.date and dp.ticker == first.ticker for dp in data_points):
            raise ValueError("All data points must have same (date, ticker)")

        # Build feature dict
        features: dict[str, Any] = {
            "date": first.date,
            "ticker": first.ticker,
            "asset_class": first.asset_class,
            "symbol": first.symbol,
            "currency": first.currency,
            "vendor": first.vendor,
            "data_timestamp": first.data_timestamp,
            "version": max(dp.version for dp in data_points),
            "metadata": {},
        }

        # Map feature_name to field
        for dp in data_points:
            # Price features
            if dp.feature_type == FeatureType.PRICE:
                if "close" in dp.feature_name.lower():
                    features["close_price"] = dp.value
                elif "open" in dp.feature_name.lower():
                    features["open_price"] = dp.value
                elif "high" in dp.feature_name.lower():
                    features["high_price"] = dp.value
                elif "low" in dp.feature_name.lower():
                    features["low_price"] = dp.value
            
            # Return features
            elif dp.feature_type == FeatureType.RETURN:
                features["daily_return"] = dp.value
            elif dp.feature_type == FeatureType.LOG_RETURN:
                features["log_return"] = dp.value
            
            # Volume features
            elif dp.feature_type == FeatureType.VOLUME:
                features["volume"] = dp.value
            elif dp.feature_type == FeatureType.DOLLAR_VOLUME:
                features["dollar_volume"] = dp.value
            
            # Fixed income features
            elif dp.feature_type == FeatureType.YIELD:
                features["yield_value"] = dp.value
            elif dp.feature_type == FeatureType.SPREAD:
                features["spread_value"] = dp.value
            elif dp.feature_type == FeatureType.DURATION:
                features["duration"] = dp.value
            
            # Volatility features
            elif dp.feature_type == FeatureType.REALIZED_VOL:
                features["realized_volatility"] = dp.value
            elif dp.feature_type == FeatureType.IMPLIED_VOL:
                features["implied_volatility"] = dp.value
            elif dp.feature_type == FeatureType.VOLATILITY_INDEX:
                features["volatility_index"] = dp.value
            
            # Correlation and cross-asset
            elif dp.feature_type == FeatureType.CORRELATION:
                if "30" in dp.feature_name:
                    features["correlation_30d"] = dp.value
                elif "90" in dp.feature_name:
                    features["correlation_90d"] = dp.value
            elif dp.feature_type == FeatureType.BETA:
                features["beta"] = dp.value
            
            # Sentiment features
            elif dp.feature_type == FeatureType.SENTIMENT_SCORE:
                features["sentiment_score"] = dp.value
            elif dp.feature_type == FeatureType.FEAR_GREED_INDEX:
                features["fear_greed_index"] = dp.value
            elif dp.feature_type == FeatureType.SOCIAL_VOLUME:
                features["social_volume"] = dp.value
            elif dp.feature_type == FeatureType.NEWS_COUNT:
                features["news_count"] = dp.value
            elif dp.feature_type == FeatureType.SEARCH_INTEREST:
                features["search_interest"] = dp.value
            
            # On-chain metrics
            elif dp.feature_type == FeatureType.ON_CHAIN_VOLUME:
                features["on_chain_volume"] = dp.value
            elif dp.feature_type == FeatureType.ACTIVE_ADDRESSES:
                features["active_addresses"] = dp.value
            elif dp.feature_type == FeatureType.HASH_RATE:
                features["hash_rate"] = dp.value
            elif dp.feature_type == FeatureType.NETWORK_VALUE:
                features["network_value"] = dp.value
            
            # Macro indicators
            elif dp.feature_type == FeatureType.ECONOMIC_INDICATOR:
                features["economic_indicator"] = dp.value
            elif dp.feature_type == FeatureType.INTEREST_RATE:
                features["interest_rate"] = dp.value
            elif dp.feature_type == FeatureType.UNEMPLOYMENT:
                features["unemployment_rate"] = dp.value
            elif dp.feature_type == FeatureType.INFLATION:
                features["inflation_rate"] = dp.value
            
            # Technical indicators
            elif dp.feature_type == FeatureType.RSI:
                features["rsi"] = dp.value
            elif dp.feature_type == FeatureType.MACD:
                features["macd"] = dp.value
            elif dp.feature_type == FeatureType.MOVING_AVERAGE:
                if "50" in dp.feature_name:
                    features["moving_average_50"] = dp.value
                elif "200" in dp.feature_name:
                    features["moving_average_200"] = dp.value
                    features["correlation_30d"] = dp.value
                elif "90" in dp.feature_name:
                    features["correlation_90d"] = dp.value
            elif dp.feature_type == FeatureType.VOLUME:
                features["volume"] = dp.value

            # Merge metadata
            features["metadata"].update(dp.metadata)

        return cls(**features)


@dataclass
class IngestionResult:
    """Result of an ingestion run."""

    success: bool
    records_extracted: int = 0
    records_transformed: int = 0
    records_validated: int = 0
    records_loaded: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
