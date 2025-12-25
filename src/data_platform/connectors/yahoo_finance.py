"""
Yahoo Finance connector implementations.

Refactored from dev/cross_asset_and_sentiment/cross_asset.py
"""

from datetime import date, datetime, timedelta
from typing import Optional
import logging

import pandas as pd
import yfinance as yf

from data_platform.connectors.base import BaseConnector, ConnectorFactory
from data_platform.models import (
    AssetDataPoint,
    AssetClass,
    Vendor,
    FeatureType,
)

logger = logging.getLogger(__name__)


class YahooFinanceBaseConnector(BaseConnector):
    """Base class for all Yahoo Finance connectors."""

    def __init__(self, vendor: Vendor, asset_class: AssetClass, **kwargs):
        super().__init__(vendor, asset_class, **kwargs)
        self.auto_adjust = kwargs.get("auto_adjust", True)
        self.progress = kwargs.get("progress", False)

    def _download(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """
        Download data from Yahoo Finance with error handling.
        
        Args:
            ticker: Yahoo Finance ticker
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with OHLCV data
            
        Raises:
            ConnectionError: If download fails
        """
        try:
            df = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=self.progress,
                auto_adjust=self.auto_adjust,
            )

            if df.empty:
                raise ValueError(f"No data returned for {ticker}")

            return df

        except Exception as e:
            logger.error(f"Failed to download {ticker} from Yahoo Finance: {e}")
            raise ConnectionError(f"Yahoo Finance download failed: {e}") from e

    def validate_ticker(self, ticker: str) -> bool:
        """Validate Yahoo Finance ticker format."""
        # Basic validation - non-empty string
        return bool(ticker and isinstance(ticker, str))


class YahooFinanceEquityConnector(YahooFinanceBaseConnector):
    """Connector for equity indices and ETFs via Yahoo Finance."""

    def __init__(self, **kwargs):
        super().__init__(
            vendor=Vendor.YAHOO_FINANCE,
            asset_class=AssetClass.EQUITY_INDEX,
            **kwargs,
        )

    def fetch(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        **kwargs,
    ) -> list[AssetDataPoint]:
        """
        Fetch equity index/ETF data.
        
        Returns price and return features.
        """
        df = self._download(ticker, start_date, end_date)
        
        # Handle both single and multi-ticker downloads
        if isinstance(df.columns, pd.MultiIndex):
            price = df["Close"][ticker].squeeze()
        else:
            price = df["Close"].squeeze()

        returns = price.pct_change()

        data_points = []
        data_timestamp = datetime.utcnow()

        for dt, price_val in price.items():
            if pd.notna(price_val):
                # Price data point
                data_points.append(
                    AssetDataPoint(
                        date=dt.date() if hasattr(dt, 'date') else dt,
                        ticker=ticker,
                        asset_class=self.asset_class,
                        symbol=ticker,
                        feature_name="close_price",
                        feature_type=FeatureType.PRICE,
                        value=float(price_val),
                        currency="USD",
                        vendor=self.vendor,
                        data_timestamp=data_timestamp,
                    )
                )

        # Return data points
        for dt, ret_val in returns.items():
            if pd.notna(ret_val):
                data_points.append(
                    AssetDataPoint(
                        date=dt.date() if hasattr(dt, 'date') else dt,
                        ticker=ticker,
                        asset_class=self.asset_class,
                        symbol=ticker,
                        feature_name="daily_return",
                        feature_type=FeatureType.RETURN,
                        value=float(ret_val),
                        currency=None,
                        vendor=self.vendor,
                        data_timestamp=data_timestamp,
                    )
                )

        logger.info(f"Fetched {len(data_points)} data points for {ticker}")
        return data_points

    @property
    def supported_features(self) -> list[str]:
        return ["close_price", "daily_return"]


class YahooFinanceCommodityConnector(YahooFinanceBaseConnector):
    """Connector for commodities (oil, gold, etc.) via Yahoo Finance."""

    def __init__(self, **kwargs):
        super().__init__(
            vendor=Vendor.YAHOO_FINANCE,
            asset_class=AssetClass.COMMODITY,
            **kwargs,
        )

    def fetch(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        **kwargs,
    ) -> list[AssetDataPoint]:
        """Fetch commodity price and return data."""
        df = self._download(ticker, start_date, end_date)
        price = df["Close"].squeeze()
        returns = price.pct_change()

        data_points = []
        data_timestamp = datetime.utcnow()

        for dt, price_val in price.items():
            if pd.notna(price_val):
                data_points.append(
                    AssetDataPoint(
                        date=dt.date() if hasattr(dt, 'date') else dt,
                        ticker=ticker,
                        asset_class=self.asset_class,
                        symbol=ticker,
                        feature_name="close_price",
                        feature_type=FeatureType.PRICE,
                        value=float(price_val),
                        currency="USD",
                        vendor=self.vendor,
                        data_timestamp=data_timestamp,
                    )
                )

        for dt, ret_val in returns.items():
            if pd.notna(ret_val):
                data_points.append(
                    AssetDataPoint(
                        date=dt.date() if hasattr(dt, 'date') else dt,
                        ticker=ticker,
                        asset_class=self.asset_class,
                        symbol=ticker,
                        feature_name="daily_return",
                        feature_type=FeatureType.RETURN,
                        value=float(ret_val),
                        currency=None,
                        vendor=self.vendor,
                        data_timestamp=data_timestamp,
                    )
                )

        logger.info(f"Fetched {len(data_points)} data points for {ticker}")
        return data_points

    @property
    def supported_features(self) -> list[str]:
        return ["close_price", "daily_return"]


class YahooFinanceCryptoConnector(YahooFinanceBaseConnector):
    """Connector for cryptocurrency via Yahoo Finance."""

    def __init__(self, **kwargs):
        super().__init__(
            vendor=Vendor.YAHOO_FINANCE,
            asset_class=AssetClass.CRYPTOCURRENCY,
            **kwargs,
        )
        self.correlation_window = kwargs.get("correlation_window", 30)
        self.correlation_ticker = kwargs.get("correlation_ticker", "^GSPC")

    def fetch(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        **kwargs,
    ) -> list[AssetDataPoint]:
        """
        Fetch crypto price, return, and correlation data.
        
        Computes rolling correlation with a benchmark (default: S&P 500).
        """
        # Fetch extra days for rolling window calculation
        window = self.correlation_window
        extended_start = start_date - timedelta(days=int(window * 1.5) + 10)

        crypto_df = self._download(ticker, extended_start, end_date)
        benchmark_df = self._download(self.correlation_ticker, extended_start, end_date)

        crypto_price = crypto_df["Close"].squeeze()
        benchmark_price = benchmark_df["Close"].squeeze()

        crypto_ret = crypto_price.pct_change()
        benchmark_ret = benchmark_price.pct_change()

        # Align on common dates
        ret_df = pd.DataFrame(
            {"crypto_ret": crypto_ret, "benchmark_ret": benchmark_ret}
        ).dropna()

        # Compute rolling correlation
        ret_df["corr"] = (
            ret_df["crypto_ret"]
            .rolling(window=window, min_periods=window)
            .corr(ret_df["benchmark_ret"])
        )

        # Get crypto price for aligned dates
        ret_df["crypto_price"] = crypto_price.reindex(ret_df.index)

        # Trim to original date range
        ret_df = ret_df.loc[start_date:]

        data_points = []
        data_timestamp = datetime.utcnow()

        # Price and return data points
        for dt in ret_df.index:
            row = ret_df.loc[dt]
            
            if pd.notna(row["crypto_price"]):
                data_points.append(
                    AssetDataPoint(
                        date=dt.date() if hasattr(dt, 'date') else dt,
                        ticker=ticker,
                        asset_class=self.asset_class,
                        symbol=ticker,
                        feature_name="close_price",
                        feature_type=FeatureType.PRICE,
                        value=float(row["crypto_price"]),
                        currency="USD",
                        vendor=self.vendor,
                        data_timestamp=data_timestamp,
                    )
                )

            if pd.notna(row["crypto_ret"]):
                data_points.append(
                    AssetDataPoint(
                        date=dt.date() if hasattr(dt, 'date') else dt,
                        ticker=ticker,
                        asset_class=self.asset_class,
                        symbol=ticker,
                        feature_name="daily_return",
                        feature_type=FeatureType.RETURN,
                        value=float(row["crypto_ret"]),
                        currency=None,
                        vendor=self.vendor,
                        data_timestamp=data_timestamp,
                    )
                )

            if pd.notna(row["corr"]):
                data_points.append(
                    AssetDataPoint(
                        date=dt.date() if hasattr(dt, 'date') else dt,
                        ticker=ticker,
                        asset_class=self.asset_class,
                        symbol=ticker,
                        feature_name=f"correlation_{window}d",
                        feature_type=FeatureType.CORRELATION,
                        value=float(row["corr"]),
                        currency=None,
                        vendor=self.vendor,
                        data_timestamp=data_timestamp,
                        metadata={"benchmark": self.correlation_ticker},
                    )
                )

        logger.info(f"Fetched {len(data_points)} data points for {ticker}")
        return data_points

    @property
    def supported_features(self) -> list[str]:
        return ["close_price", "daily_return", "correlation_30d"]


class YahooFinanceFXConnector(YahooFinanceBaseConnector):
    """Connector for FX pairs via Yahoo Finance."""

    def __init__(self, **kwargs):
        super().__init__(
            vendor=Vendor.YAHOO_FINANCE,
            asset_class=AssetClass.FX,
            **kwargs,
        )

    def fetch(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        **kwargs,
    ) -> list[AssetDataPoint]:
        """Fetch FX pair data."""
        df = self._download(ticker, start_date, end_date)
        price = df["Close"].squeeze()
        returns = price.pct_change()

        data_points = []
        data_timestamp = datetime.utcnow()

        for dt, price_val in price.items():
            if pd.notna(price_val):
                data_points.append(
                    AssetDataPoint(
                        date=dt.date() if hasattr(dt, 'date') else dt,
                        ticker=ticker,
                        asset_class=self.asset_class,
                        symbol=ticker,
                        feature_name="close_price",
                        feature_type=FeatureType.PRICE,
                        value=float(price_val),
                        currency=None,  # FX pairs are dimensionless
                        vendor=self.vendor,
                        data_timestamp=data_timestamp,
                    )
                )

        for dt, ret_val in returns.items():
            if pd.notna(ret_val):
                data_points.append(
                    AssetDataPoint(
                        date=dt.date() if hasattr(dt, 'date') else dt,
                        ticker=ticker,
                        asset_class=self.asset_class,
                        symbol=ticker,
                        feature_name="daily_return",
                        feature_type=FeatureType.RETURN,
                        value=float(ret_val),
                        currency=None,
                        vendor=self.vendor,
                        data_timestamp=data_timestamp,
                    )
                )

        logger.info(f"Fetched {len(data_points)} data points for {ticker}")
        return data_points

    @property
    def supported_features(self) -> list[str]:
        return ["close_price", "daily_return"]


class YahooFinanceFixedIncomeConnector(YahooFinanceBaseConnector):
    """Connector for Treasury yields via Yahoo Finance."""

    def __init__(self, **kwargs):
        super().__init__(
            vendor=Vendor.YAHOO_FINANCE,
            asset_class=AssetClass.FIXED_INCOME,
            **kwargs,
        )

    def fetch(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        **kwargs,
    ) -> list[AssetDataPoint]:
        """Fetch Treasury yield data."""
        df = self._download(ticker, start_date, end_date)
        
        # Treasury yields are in 'Close' column
        if isinstance(df.columns, pd.MultiIndex):
            price = df["Close"][ticker].squeeze()
        else:
            price = df["Close"].squeeze()

        data_points = []
        data_timestamp = datetime.utcnow()

        # Determine if this is a yield index or price
        is_yield_index = any(x in ticker for x in ["^IRX", "^FVX", "^TNX"])
        feature_type = FeatureType.YIELD if is_yield_index else FeatureType.PRICE

        for dt, val in price.items():
            if pd.notna(val):
                data_points.append(
                    AssetDataPoint(
                        date=dt.date() if hasattr(dt, 'date') else dt,
                        ticker=ticker,
                        asset_class=self.asset_class,
                        symbol=ticker,
                        feature_name="yield_value" if is_yield_index else "close_price",
                        feature_type=feature_type,
                        value=float(val),
                        currency="USD" if not is_yield_index else None,
                        vendor=self.vendor,
                        data_timestamp=data_timestamp,
                    )
                )

        logger.info(f"Fetched {len(data_points)} data points for {ticker}")
        return data_points

    @property
    def supported_features(self) -> list[str]:
        return ["yield_value", "close_price"]


class YahooFinanceCreditConnector(YahooFinanceBaseConnector):
    """Connector for credit spreads via ETF proxies (HYG, LQD, AGG)."""

    def __init__(self, **kwargs):
        super().__init__(
            vendor=Vendor.YAHOO_FINANCE,
            asset_class=AssetClass.CREDIT,
            **kwargs,
        )

    def fetch(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        **kwargs,
    ) -> list[AssetDataPoint]:
        """
        Fetch credit ETF data and compute spreads.
        
        For HYG/LQD, computes spread vs AGG benchmark.
        """
        df = self._download(ticker, start_date, end_date)
        price = df["Close"].squeeze()
        returns = price.pct_change()

        data_points = []
        data_timestamp = datetime.utcnow()

        # Price and return data points
        for dt, price_val in price.items():
            if pd.notna(price_val):
                data_points.append(
                    AssetDataPoint(
                        date=dt.date() if hasattr(dt, 'date') else dt,
                        ticker=ticker,
                        asset_class=self.asset_class,
                        symbol=ticker,
                        feature_name="close_price",
                        feature_type=FeatureType.PRICE,
                        value=float(price_val),
                        currency="USD",
                        vendor=self.vendor,
                        data_timestamp=data_timestamp,
                    )
                )

        for dt, ret_val in returns.items():
            if pd.notna(ret_val):
                data_points.append(
                    AssetDataPoint(
                        date=dt.date() if hasattr(dt, 'date') else dt,
                        ticker=ticker,
                        asset_class=self.asset_class,
                        symbol=ticker,
                        feature_name="daily_return",
                        feature_type=FeatureType.RETURN,
                        value=float(ret_val),
                        currency=None,
                        vendor=self.vendor,
                        data_timestamp=data_timestamp,
                    )
                )

        logger.info(f"Fetched {len(data_points)} data points for {ticker}")
        return data_points

    @property
    def supported_features(self) -> list[str]:
        return ["close_price", "daily_return", "spread_value"]


# Register all connectors
ConnectorFactory.register(
    Vendor.YAHOO_FINANCE,
    AssetClass.EQUITY_INDEX,
    YahooFinanceEquityConnector,
)
ConnectorFactory.register(
    Vendor.YAHOO_FINANCE,
    AssetClass.EQUITY_ETF,
    YahooFinanceEquityConnector,
)
ConnectorFactory.register(
    Vendor.YAHOO_FINANCE,
    AssetClass.COMMODITY,
    YahooFinanceCommodityConnector,
)
ConnectorFactory.register(
    Vendor.YAHOO_FINANCE,
    AssetClass.CRYPTOCURRENCY,
    YahooFinanceCryptoConnector,
)
ConnectorFactory.register(
    Vendor.YAHOO_FINANCE,
    AssetClass.FX,
    YahooFinanceFXConnector,
)
ConnectorFactory.register(
    Vendor.YAHOO_FINANCE,
    AssetClass.FX_INDEX,
    YahooFinanceFXConnector,
)
ConnectorFactory.register(
    Vendor.YAHOO_FINANCE,
    AssetClass.FIXED_INCOME,
    YahooFinanceFixedIncomeConnector,
)
ConnectorFactory.register(
    Vendor.YAHOO_FINANCE,
    AssetClass.CREDIT,
    YahooFinanceCreditConnector,
)
