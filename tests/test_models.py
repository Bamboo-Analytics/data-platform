"""
Unit tests for data models.
"""

from datetime import date, datetime, timezone
import pytest

from data_platform.models import (
    AssetDataPoint,
    DailyFactRecord,
    AssetClass,
    Vendor,
    FeatureType,
    IngestionResult,
)


class TestAssetDataPoint:
    """Tests for AssetDataPoint model."""

    def test_create_valid_data_point(self):
        """Test creating a valid AssetDataPoint."""
        dp = AssetDataPoint(
            date=date(2024, 1, 15),
            ticker="^GSPC",
            asset_class=AssetClass.EQUITY_INDEX,
            symbol="S&P 500",
            feature_name="close_price",
            feature_type=FeatureType.PRICE,
            value=4500.50,
            currency="USD",
            vendor=Vendor.YAHOO_FINANCE,
            data_timestamp=datetime(2024, 1, 15, 16, 0, 0, tzinfo=timezone.utc),
        )

        assert dp.ticker == "^GSPC"
        assert dp.value == 4500.50
        assert dp.asset_class == AssetClass.EQUITY_INDEX

    def test_ticker_normalized_to_uppercase(self):
        """Test that ticker is normalized to uppercase."""
        dp = AssetDataPoint(
            date=date(2024, 1, 15),
            ticker="btc-usd",
            asset_class=AssetClass.CRYPTOCURRENCY,
            symbol="bitcoin",
            feature_name="close_price",
            feature_type=FeatureType.PRICE,
            value=45000.0,
            vendor=Vendor.YAHOO_FINANCE,
            data_timestamp=datetime.utcnow(),
        )

        assert dp.ticker == "BTC-USD"
        assert dp.symbol == "BITCOIN"

    def test_future_date_validation(self):
        """Test that future dates are rejected."""
        with pytest.raises(ValueError, match="cannot be in the future"):
            AssetDataPoint(
                date=date(2099, 12, 31),
                ticker="^GSPC",
                asset_class=AssetClass.EQUITY_INDEX,
                symbol="S&P 500",
                feature_name="close_price",
                feature_type=FeatureType.PRICE,
                value=5000.0,
                vendor=Vendor.YAHOO_FINANCE,
                data_timestamp=datetime.utcnow(),
            )

    def test_value_range_validation(self):
        """Test that extreme values are rejected."""
        with pytest.raises(ValueError, match="out of reasonable range"):
            AssetDataPoint(
                date=date(2024, 1, 15),
                ticker="^GSPC",
                asset_class=AssetClass.EQUITY_INDEX,
                symbol="S&P 500",
                feature_name="close_price",
                feature_type=FeatureType.PRICE,
                value=1e16,  # Too large
                vendor=Vendor.YAHOO_FINANCE,
                data_timestamp=datetime.utcnow(),
            )


class TestDailyFactRecord:
    """Tests for DailyFactRecord model."""

    def test_create_valid_fact_record(self):
        """Test creating a valid DailyFactRecord."""
        record = DailyFactRecord(
            date=date(2024, 1, 15),
            ticker="^GSPC",
            asset_class=AssetClass.EQUITY_INDEX,
            symbol="S&P 500",
            currency="USD",
            close_price=4500.50,
            daily_return=0.015,
            vendor=Vendor.YAHOO_FINANCE,
            data_timestamp=datetime.utcnow(),
        )

        assert record.ticker == "^GSPC"
        assert record.close_price == 4500.50
        assert record.daily_return == 0.015

    def test_from_data_points(self):
        """Test converting AssetDataPoint list to DailyFactRecord."""
        data_points = [
            AssetDataPoint(
                date=date(2024, 1, 15),
                ticker="^GSPC",
                asset_class=AssetClass.EQUITY_INDEX,
                symbol="S&P 500",
                feature_name="close_price",
                feature_type=FeatureType.PRICE,
                value=4500.50,
                currency="USD",
                vendor=Vendor.YAHOO_FINANCE,
                data_timestamp=datetime.utcnow(),
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
                data_timestamp=datetime.utcnow(),
            ),
        ]

        record = DailyFactRecord.from_data_points(data_points)

        assert record is not None
        assert record.ticker == "^GSPC"
        assert record.close_price == 4500.50
        assert record.daily_return == 0.015

    def test_from_data_points_different_dates_raises_error(self):
        """Test that data points with different dates raise error."""
        data_points = [
            AssetDataPoint(
                date=date(2024, 1, 15),
                ticker="^GSPC",
                asset_class=AssetClass.EQUITY_INDEX,
                symbol="S&P 500",
                feature_name="close_price",
                feature_type=FeatureType.PRICE,
                value=4500.50,
                vendor=Vendor.YAHOO_FINANCE,
                data_timestamp=datetime.utcnow(),
            ),
            AssetDataPoint(
                date=date(2024, 1, 16),  # Different date
                ticker="^GSPC",
                asset_class=AssetClass.EQUITY_INDEX,
                symbol="S&P 500",
                feature_name="daily_return",
                feature_type=FeatureType.RETURN,
                value=0.015,
                vendor=Vendor.YAHOO_FINANCE,
                data_timestamp=datetime.utcnow(),
            ),
        ]

        with pytest.raises(ValueError, match="same \\(date, ticker\\)"):
            DailyFactRecord.from_data_points(data_points)


class TestIngestionResult:
    """Tests for IngestionResult model."""

    def test_initial_success_state(self):
        """Test initial state of IngestionResult."""
        result = IngestionResult(success=True)

        assert result.success is True
        assert result.records_extracted == 0
        assert len(result.errors) == 0

    def test_add_error_sets_success_false(self):
        """Test that adding an error sets success to False."""
        result = IngestionResult(success=True)
        result.add_error("Test error")

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0] == "Test error"

    def test_add_warning_does_not_affect_success(self):
        """Test that adding a warning doesn't change success state."""
        result = IngestionResult(success=True)
        result.add_warning("Test warning")

        assert result.success is True
        assert len(result.warnings) == 1
