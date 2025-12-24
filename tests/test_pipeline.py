"""
Tests for pipeline runner.
"""

from datetime import date, datetime
from unittest.mock import Mock, patch, MagicMock
import pytest

from data_platform.pipeline import PipelineRunner
from data_platform.models import (
    AssetDataPoint,
    AssetClass,
    Vendor,
    FeatureType,
)


class TestPipelineRunner:
    """Tests for PipelineRunner."""

    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        # Mock ClickHouse client
        mock_clickhouse = Mock()

        runner = PipelineRunner(clickhouse_client=mock_clickhouse)

        assert runner.clickhouse == mock_clickhouse
        assert runner.transformer is not None
        assert runner.quality_checker is not None

    @patch("data_platform.pipeline.ConnectorFactory.create")
    def test_extract_source(self, mock_create_connector):
        """Test extracting data from a source."""
        # Mock connector
        mock_connector = Mock()
        mock_connector.fetch.return_value = [
            AssetDataPoint(
                date=date(2024, 1, 15),
                ticker="^GSPC",
                asset_class=AssetClass.EQUITY_INDEX,
                symbol="S&P 500",
                feature_name="close_price",
                feature_type=FeatureType.PRICE,
                value=4500.0,
                vendor=Vendor.YAHOO_FINANCE,
                data_timestamp=datetime.utcnow(),
            )
        ]
        mock_create_connector.return_value = mock_connector

        # Mock ClickHouse client
        mock_clickhouse = Mock()
        runner = PipelineRunner(clickhouse_client=mock_clickhouse)

        source = {
            "name": "sp500",
            "vendor": "yahoo_finance",
            "asset_class": "equity_index",
            "ticker": "^GSPC",
        }

        data_points = runner._extract_source(
            source,
            date(2024, 1, 15),
            date(2024, 1, 17),
        )

        assert len(data_points) == 1
        assert data_points[0].ticker == "^GSPC"

    def test_initialize_database(self):
        """Test database initialization."""
        mock_clickhouse = Mock()

        runner = PipelineRunner(clickhouse_client=mock_clickhouse)
        runner.initialize_database()

        # Should call create_tables
        mock_clickhouse.__enter__.return_value.create_tables.assert_called_once()
