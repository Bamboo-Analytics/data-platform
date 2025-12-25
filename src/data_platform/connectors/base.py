"""
Base connector interface for data sources.

All data connectors must implement this interface.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Optional

from data_platform.models import AssetDataPoint, AssetClass, Vendor


class BaseConnector(ABC):
    """
    Abstract base class for all data source connectors.
    
    Each connector is responsible for:
    1. Fetching raw data from a vendor/API
    2. Transforming it into AssetDataPoint instances
    3. Handling vendor-specific errors and retries
    """

    def __init__(
        self,
        vendor: Vendor,
        asset_class: AssetClass,
        **kwargs,
    ):
        """
        Initialize connector.
        
        Args:
            vendor: Data vendor/source
            asset_class: Asset class this connector handles
            **kwargs: Connector-specific configuration
        """
        self.vendor = vendor
        self.asset_class = asset_class
        self.config = kwargs

    @abstractmethod
    def fetch(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        **kwargs,
    ) -> list[AssetDataPoint]:
        """
        Fetch data for a single ticker in a date range.
        
        Args:
            ticker: Ticker symbol (vendor-specific format)
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            **kwargs: Additional fetch parameters
            
        Returns:
            List of AssetDataPoint instances
            
        Raises:
            ValueError: Invalid parameters
            ConnectionError: Network/API errors
            Exception: Other errors
        """
        pass

    @abstractmethod
    def validate_ticker(self, ticker: str) -> bool:
        """
        Validate if ticker format is correct for this connector.
        
        Args:
            ticker: Ticker to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass

    def get_ticker_metadata(self, ticker: str) -> dict:
        """
        Get additional metadata about a ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Dictionary with metadata (name, exchange, etc.)
        """
        return {}

    @property
    @abstractmethod
    def supported_features(self) -> list[str]:
        """
        List of feature types this connector provides.
        
        Returns:
            List of feature names (e.g., ['price', 'return', 'volume'])
        """
        pass

    @property
    def name(self) -> str:
        """Connector name for logging."""
        return f"{self.vendor.value}_{self.asset_class.value}_connector"


class ConnectorFactory:
    """
    Factory for creating and managing connectors.
    
    Implements the registry pattern for extensibility.
    """

    _registry: dict[str, type[BaseConnector]] = {}

    @classmethod
    def register(
        cls,
        vendor: Vendor,
        asset_class: AssetClass,
        connector_class: type[BaseConnector],
    ) -> None:
        """
        Register a connector class.
        
        Args:
            vendor: Data vendor
            asset_class: Asset class
            connector_class: Connector class to register
        """
        key = cls._make_key(vendor, asset_class)
        cls._registry[key] = connector_class

    @classmethod
    def create(
        cls,
        vendor: Vendor,
        asset_class: AssetClass,
        **kwargs,
    ) -> BaseConnector:
        """
        Create a connector instance.
        
        Args:
            vendor: Data vendor
            asset_class: Asset class
            **kwargs: Connector configuration
            
        Returns:
            Connector instance
            
        Raises:
            ValueError: If no connector registered for (vendor, asset_class)
        """
        key = cls._make_key(vendor, asset_class)
        connector_class = cls._registry.get(key)

        if connector_class is None:
            raise ValueError(
                f"No connector registered for vendor={vendor.value}, "
                f"asset_class={asset_class.value}"
            )

        return connector_class(vendor=vendor, asset_class=asset_class, **kwargs)

    @classmethod
    def _make_key(cls, vendor: Vendor, asset_class: AssetClass) -> str:
        """Create registry key from vendor and asset class."""
        return f"{vendor.value}:{asset_class.value}"

    @classmethod
    def list_registered(cls) -> list[tuple[Vendor, AssetClass]]:
        """
        List all registered connectors.
        
        Returns:
            List of (vendor, asset_class) tuples
        """
        result = []
        for key in cls._registry.keys():
            vendor_str, asset_class_str = key.split(":")
            result.append((Vendor(vendor_str), AssetClass(asset_class_str)))
        return result
