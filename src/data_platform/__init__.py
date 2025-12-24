"""
Data Platform - Cross-asset data ingestion pipeline.

Main package exports.
"""

__version__ = "0.1.0"

from data_platform.models import (
    AssetDataPoint,
    DailyFactRecord,
    AssetClass,
    Vendor,
    FeatureType,
    IngestionResult,
)
from data_platform.pipeline import PipelineRunner
from data_platform.config import get_config
from data_platform.connectors.base import BaseConnector, ConnectorFactory

__all__ = [
    "AssetDataPoint",
    "DailyFactRecord",
    "AssetClass",
    "Vendor",
    "FeatureType",
    "IngestionResult",
    "PipelineRunner",
    "get_config",
    "BaseConnector",
    "ConnectorFactory",
]
