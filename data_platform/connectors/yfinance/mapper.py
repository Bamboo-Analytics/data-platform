"""YFinance mapper that transforms API-specific models to standard platform models."""
import logging
from typing import List, Optional
from data_platform.ingestion.models.standard import OHLCV, AssetInfo
from data_platform.ingestion.connectors.yfinance.models import (
    YFinanceOHLCV,
    YFinanceInfo,
    YFinanceDividend,
    YFinanceSplit
)

logger = logging.getLogger(__name__)


class YFinanceMapper:
    """
    Transforms YFinance-specific models to standardized platform models.
    Handles field mapping and cherry-picking from multiple sources.
    """
    
    # Mapping from YFinance quoteType to platform asset_type
    ASSET_TYPE_MAPPING = {
        'EQUITY': 'stock',
        'ETF': 'etf',
        'CRYPTOCURRENCY': 'crypto',
        'MUTUALFUND': 'mutual_fund',
        'INDEX': 'index',
        'FUTURE': 'future',
        'OPTION': 'option',
        'CURRENCY': 'currency'
    }
    
    @staticmethod
    def to_ohlcv(yf_ohlcv: YFinanceOHLCV, ticker: str) -> OHLCV:
        """
        Map YFinance OHLCV model to standard platform OHLCV model.
        
        Args:
            yf_ohlcv: YFinance-specific OHLCV model
            ticker: Ticker symbol
            
        Returns:
            Standard OHLCV model
        """
        return OHLCV(
            ticker=ticker,
            timestamp=yf_ohlcv.Date,
            open=float(yf_ohlcv.Open),
            high=float(yf_ohlcv.High),
            low=float(yf_ohlcv.Low),
            close=float(yf_ohlcv.Close),
            volume=float(yf_ohlcv.Volume),
            source='yfinance'
        )
    
    @staticmethod
    def to_ohlcv_list(yf_ohlcv_list: List[YFinanceOHLCV], ticker: str) -> List[OHLCV]:
        """
        Map list of YFinance OHLCV models to standard models.
        
        Args:
            yf_ohlcv_list: List of YFinance OHLCV models
            ticker: Ticker symbol
            
        Returns:
            List of standard OHLCV models
        """
        return [
            YFinanceMapper.to_ohlcv(yf_ohlcv, ticker)
            for yf_ohlcv in yf_ohlcv_list
        ]
    
    @staticmethod
    def to_asset_info(
        yf_info: YFinanceInfo,
        dividends: Optional[List[YFinanceDividend]] = None,
        splits: Optional[List[YFinanceSplit]] = None
    ) -> AssetInfo:
        """
        Map YFinance info to standard platform AssetInfo model.
        Cherry-picks data from multiple YFinance sources (info, dividends, splits).
        
        Args:
            yf_info: YFinance asset info model
            dividends: Optional list of dividend records
            splits: Optional list of split records
            
        Returns:
            Standard AssetInfo model
        """
        # Get last dividend amount
        last_dividend = None
        if dividends and len(dividends) > 0:
            # Sort by date and get most recent
            sorted_divs = sorted(dividends, key=lambda d: d.Date)
            last_dividend = sorted_divs[-1].Dividends
            logger.debug(f"Last dividend for {yf_info.symbol}: ${last_dividend}")
        
        # Get last split ratio
        last_split = None
        if splits and len(splits) > 0:
            # Sort by date and get most recent
            sorted_splits = sorted(splits, key=lambda s: s.Date)
            last_split = sorted_splits[-1].Stock_Splits
            logger.debug(f"Last split for {yf_info.symbol}: {last_split}")
        
        # Map asset type
        asset_type = YFinanceMapper._map_asset_type(yf_info.quoteType)
        
        # Use longName if available, fall back to shortName, then symbol
        name = yf_info.longName or yf_info.shortName or yf_info.symbol
        
        return AssetInfo(
            ticker=yf_info.symbol,
            name=name,
            asset_type=asset_type,
            exchange=yf_info.exchange,
            currency=yf_info.currency,
            sector=yf_info.sector,
            industry=yf_info.industry,
            market_cap=float(yf_info.marketCap) if yf_info.marketCap else None,
            description=yf_info.longBusinessSummary,
            last_dividend=last_dividend,
            last_split=last_split,
            source='yfinance'
        )
    
    @staticmethod
    def _map_asset_type(quote_type: Optional[str]) -> str:
        """
        Map YFinance quoteType to platform asset_type.
        
        Args:
            quote_type: YFinance quoteType value
            
        Returns:
            Platform-standardized asset type
        """
        if not quote_type:
            return 'unknown'
        
        normalized_type = quote_type.upper()
        return YFinanceMapper.ASSET_TYPE_MAPPING.get(normalized_type, 'unknown')

