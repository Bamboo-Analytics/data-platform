"""
Configuration management using Pydantic Settings.

Loads configuration from YAML files and environment variables.
"""

from pathlib import Path
from typing import Any, Optional
import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml


class ClickHouseConfig(BaseSettings):
    """ClickHouse connection configuration."""

    model_config = SettingsConfigDict(
        env_prefix="CLICKHOUSE_",
        case_sensitive=False,
    )

    host: str = Field(default="localhost", description="ClickHouse host")
    port: int = Field(default=8123, description="ClickHouse HTTP port")
    username: str = Field(default="default", description="ClickHouse username")
    password: str = Field(default="", description="ClickHouse password")
    database: str = Field(default="data_platform", description="Database name")
    batch_insert_size: int = Field(default=10000, description="Batch insert size")


class PipelineConfig(BaseSettings):
    """Pipeline execution configuration."""

    model_config = SettingsConfigDict(
        env_prefix="PIPELINE_",
        case_sensitive=False,
    )

    batch_size: int = Field(default=1000, description="Processing batch size")
    max_retries: int = Field(default=3, description="Maximum retries for failed tasks")
    retry_delay_seconds: int = Field(default=5, description="Delay between retries")
    backoff_multiplier: float = Field(default=2.0, description="Backoff multiplier")
    max_null_rate: float = Field(default=0.3, description="Maximum null rate threshold")
    check_outliers: bool = Field(default=True, description="Enable outlier detection")
    z_score_threshold: float = Field(default=5.0, description="Z-score threshold")


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        case_sensitive=False,
    )

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format (json or text)")


class AppConfig(BaseSettings):
    """Main application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Sub-configurations
    clickhouse: ClickHouseConfig = Field(default_factory=ClickHouseConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Paths
    config_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "config"
    )
    sources_config_path: Path = Field(default=None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.sources_config_path is None:
            self.sources_config_path = self.config_dir / "sources.yaml"

    def load_sources_config(self) -> dict[str, Any]:
        """
        Load sources configuration from YAML file.
        
        Returns:
            Dictionary with sources configuration
        """
        if not self.sources_config_path.exists():
            raise FileNotFoundError(
                f"Sources config not found: {self.sources_config_path}"
            )

        with open(self.sources_config_path, "r") as f:
            config = yaml.safe_load(f)

        return config

    def get_enabled_daily_sources(self) -> list[dict[str, Any]]:
        """
        Get list of enabled daily sources.
        
        Returns:
            List of source configurations
        """
        sources_config = self.load_sources_config()
        daily_sources = sources_config.get("daily_sources", [])
        return [s for s in daily_sources if s.get("enabled", True)]

    def get_enabled_quarterly_sources(self) -> list[dict[str, Any]]:
        """
        Get list of enabled quarterly sources.
        
        Returns:
            List of source configurations
        """
        sources_config = self.load_sources_config()
        quarterly_sources = sources_config.get("quarterly_sources", [])
        return [s for s in quarterly_sources if s.get("enabled", True)]


# Global config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    Get global configuration instance (singleton).
    
    Returns:
        AppConfig instance
    """
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reload_config() -> AppConfig:
    """
    Reload configuration (useful for testing).
    
    Returns:
        New AppConfig instance
    """
    global _config
    _config = AppConfig()
    return _config
