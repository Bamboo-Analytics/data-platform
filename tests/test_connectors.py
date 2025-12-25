"""
Unit tests for connectors.
"""

from datetime import date, datetime
from unittest.mock import Mock, patch, MagicMock
import pytest
import pandas as pd

from data_platform.connectors.base import BaseConnector, ConnectorFactory
from data_platform.connectors.yahoo_finance import (
    YahooFinanceEquityConnector,
    YahooFinanceCommodityConnector,
)
from data_platform.models import AssetClass, Vendor, FeatureType


class TestConnectorFactory:
    """Tests for ConnectorFactory."""

    def test_register_and_create_connector(self):
        """Test registering and creating a connector."""
        # Create a mock connector class
        class MockConnector(BaseConnector):
            def fetch(self, ticker, start_date, end_date, **kwargs):
                return []

            def validate_ticker(self, ticker):
                return True

            @property
            def supported_features(self):
                return ["price"]

        # Register it
        ConnectorFactory.register(
            Vendor.YAHOO_FINANCE,
            AssetClass.EQUITY_INDEX,
            MockConnector,
        )

        # Create an instance
        connector = ConnectorFactory.create(
            Vendor.YAHOO_FINANCE,
            AssetClass.EQUITY_INDEX,
        )

        assert isinstance(connector, MockConnector)
        assert connector.vendor == Vendor.YAHOO_FINANCE
        assert connector.asset_class == AssetClass.EQUITY_INDEX

    def test_create_unregistered_connector_raises_error(self):
        """Test that creating unregistered connector raises ValueError."""
        with pytest.raises(ValueError, match="No connector registered"):
            ConnectorFactory.create(
                Vendor.FRED,
                AssetClass.COMMODITY,
            )


class TestYahooFinanceEquityConnector:
    """Tests for YahooFinanceEquityConnector."""

    @patch("data_platform.connectors.yahoo_finance.yf.download")
    def test_fetch_equity_data(self, mock_download):
        """Test fetching equity data."""
        # Mock yfinance response
        mock_df = pd.DataFrame(
            {
                "Close": [4500.0, 4510.0, 4520.0],
            },
            index=pd.date_range("2024-01-15", periods=3, freq="D"),
        )
        mock_download.return_value = mock_df

        connector = YahooFinanceEquityConnector()
        data_points = connector.fetch(
            ticker="^GSPC",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 17),
        )

        # Should have price + return for 3 days = 6 data points
        # (but first day has no return)
        assert len(data_points) > 0

        # Check first data point
        price_points = [dp for dp in data_points if dp.feature_type == FeatureType.PRICE]
        assert len(price_points) == 3
        assert price_points[0].ticker == "^GSPC"
        assert price_points[0].value == 4500.0

    @patch("data_platform.connectors.yahoo_finance.yf.download")
    def test_fetch_handles_empty_response(self, mock_download):
        """Test that fetch handles empty DataFrame."""
        mock_download.return_value = pd.DataFrame()

        connector = YahooFinanceEquityConnector()

        with pytest.raises(ConnectionError, match="Yahoo Finance download failed"):
            connector.fetch(
                ticker="^GSPC",
                start_date=date(2024, 1, 15),
                end_date=date(2024, 1, 17),
            )


class TestYahooFinanceCommodityConnector:
    """Tests for YahooFinanceCommodityConnector."""

    @patch("data_platform.connectors.yahoo_finance.yf.download")
    def test_fetch_commodity_data(self, mock_download):
        """Test fetching commodity data."""
        # Mock yfinance response
        mock_df = pd.DataFrame(
            {
                "Close": [75.0, 76.0, 74.5],
            },
            index=pd.date_range("2024-01-15", periods=3, freq="D"),
        )
        mock_download.return_value = mock_df

        connector = YahooFinanceCommodityConnector()
        data_points = connector.fetch(
            ticker="CL=F",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 17),
        )

        assert len(data_points) > 0

        price_points = [dp for dp in data_points if dp.feature_type == FeatureType.PRICE]
        assert price_points[0].ticker == "CL=F"
        assert price_points[0].currency == "USD"

    def test_validate_ticker(self):
        """Test ticker validation."""
        connector = YahooFinanceCommodityConnector()

        assert connector.validate_ticker("CL=F") is True
        assert connector.validate_ticker("") is False
        assert connector.validate_ticker(None) is False
