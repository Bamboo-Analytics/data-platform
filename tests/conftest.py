"""
Pytest configuration and fixtures.
"""

from datetime import date, datetime
import pytest

from data_platform.models import (
    AssetDataPoint,
    AssetClass,
    Vendor,
    FeatureType,
)


@pytest.fixture
def sample_data_points():
    """Fixture providing sample AssetDataPoint instances."""
    return [
        AssetDataPoint(
            date=date(2024, 1, 15),
            ticker="^GSPC",
            asset_class=AssetClass.EQUITY_INDEX,
            symbol="S&P 500",
            feature_name="close_price",
            feature_type=FeatureType.PRICE,
            value=4500.0,
            currency="USD",
            vendor=Vendor.YAHOO_FINANCE,
            data_timestamp=datetime(2024, 1, 15, 16, 0, 0),
        ),
        AssetDataPoint(
            date=date(2024, 1, 15),
            ticker="^GSPC",
            asset_class=AssetClass.EQUITY_INDEX,
            symbol="S&P 500",
            feature_name="daily_return",
            feature_type=FeatureType.RETURN,
            value=0.015,
            vendor=Vendor.YAHOO_FINANCE,
            data_timestamp=datetime(2024, 1, 15, 16, 0, 0),
        ),
        AssetDataPoint(
            date=date(2024, 1, 16),
            ticker="^GSPC",
            asset_class=AssetClass.EQUITY_INDEX,
            symbol="S&P 500",
            feature_name="close_price",
            feature_type=FeatureType.PRICE,
            value=4520.0,
            currency="USD",
            vendor=Vendor.YAHOO_FINANCE,
            data_timestamp=datetime(2024, 1, 16, 16, 0, 0),
        ),
    ]


@pytest.fixture
def mock_config():
    """Fixture providing mock configuration."""
    from unittest.mock import Mock

    config = Mock()
    config.clickhouse.host = "localhost"
    config.clickhouse.port = 8123
    config.clickhouse.database = "test_db"
    config.clickhouse.batch_insert_size = 1000
    config.pipeline.max_null_rate = 0.3
    config.pipeline.check_outliers = True
    config.pipeline.z_score_threshold = 5.0

    return config
