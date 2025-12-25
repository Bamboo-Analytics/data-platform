"""
Transformation layer for normalizing data.

Handles timezone conversion, trading calendar alignment,
missing value imputation, and feature engineering.
"""

from datetime import date, datetime, timezone
from typing import Optional
import logging

import pandas as pd
import numpy as np

from data_platform.models import AssetDataPoint, DailyFactRecord

logger = logging.getLogger(__name__)


class DataTransformer:
    """
    Transforms raw data points into canonical format.
    
    Responsibilities:
    - Timezone normalization (all to UTC)
    - Trading calendar alignment
    - Missing value handling
    - Unit conversion
    """

    def __init__(
        self,
        target_timezone: str = "UTC",
        fill_method: Optional[str] = None,
    ):
        """
        Initialize transformer.
        
        Args:
            target_timezone: Target timezone for all dates (default: UTC)
            fill_method: Method for filling missing values ('ffill', 'bfill', None)
        """
        self.target_timezone = target_timezone
        self.fill_method = fill_method

    def normalize_timezone(
        self, data_points: list[AssetDataPoint]
    ) -> list[AssetDataPoint]:
        """
        Normalize all timestamps to target timezone.
        
        Args:
            data_points: Input data points
            
        Returns:
            Data points with normalized timestamps
        """
        for dp in data_points:
            # Ensure data_timestamp is timezone-aware
            if dp.data_timestamp.tzinfo is None:
                dp.data_timestamp = dp.data_timestamp.replace(tzinfo=timezone.utc)
            
            # Ensure ingestion_timestamp is timezone-aware
            if dp.ingestion_timestamp.tzinfo is None:
                dp.ingestion_timestamp = dp.ingestion_timestamp.replace(
                    tzinfo=timezone.utc
                )

        return data_points

    def fill_missing_values(
        self, data_points: list[AssetDataPoint]
    ) -> list[AssetDataPoint]:
        """
        Fill missing values using specified method.
        
        Args:
            data_points: Input data points
            
        Returns:
            Data points with filled values
        """
        if not self.fill_method or not data_points:
            return data_points

        # Group by ticker and feature_name
        from collections import defaultdict
        
        grouped = defaultdict(list)
        for dp in data_points:
            key = (dp.ticker, dp.feature_name)
            grouped[key].append(dp)

        filled_points = []

        for key, points in grouped.items():
            # Sort by date
            points = sorted(points, key=lambda x: x.date)

            # Create series for filling
            dates = [p.date for p in points]
            values = [p.value for p in points]

            series = pd.Series(values, index=dates)

            if self.fill_method == "ffill":
                series = series.ffill()
            elif self.fill_method == "bfill":
                series = series.bfill()

            # Update values
            for i, point in enumerate(points):
                point.value = (
                    float(series.iloc[i]) 
                    if pd.notna(series.iloc[i]) 
                    else None
                )
                filled_points.append(point)

        return filled_points

    def convert_to_daily_facts(
        self, data_points: list[AssetDataPoint]
    ) -> list[DailyFactRecord]:
        """
        Convert AssetDataPoint list to DailyFactRecord list.
        
        Groups by (date, ticker) and pivots features into columns.
        
        Args:
            data_points: List of AssetDataPoint instances
            
        Returns:
            List of DailyFactRecord instances
        """
        if not data_points:
            return []

        # Group by (date, ticker)
        from collections import defaultdict
        
        grouped = defaultdict(list)
        for dp in data_points:
            key = (dp.date, dp.ticker)
            grouped[key].append(dp)

        daily_facts = []

        for (date_val, ticker), points in grouped.items():
            try:
                fact = DailyFactRecord.from_data_points(points)
                if fact:
                    daily_facts.append(fact)
            except Exception as e:
                logger.error(
                    f"Failed to convert data points to fact for "
                    f"{ticker} on {date_val}: {e}"
                )

        logger.info(
            f"Converted {len(data_points)} data points to "
            f"{len(daily_facts)} daily fact records"
        )

        return daily_facts

    def align_trading_calendar(
        self,
        data_points: list[AssetDataPoint],
        calendar: str = "NYSE",
    ) -> list[AssetDataPoint]:
        """
        Align data to trading calendar (remove non-trading days).
        
        Args:
            data_points: Input data points
            calendar: Trading calendar name (NYSE, LSE, etc.)
            
        Returns:
            Filtered data points
        """
        # For now, simple implementation - just remove weekends
        # In production, use pandas_market_calendars or similar
        
        filtered = [
            dp for dp in data_points
            if dp.date.weekday() < 5  # Monday=0, Sunday=6
        ]

        removed = len(data_points) - len(filtered)
        if removed > 0:
            logger.debug(f"Removed {removed} non-trading day records")

        return filtered

    def deduplicate(
        self, data_points: list[AssetDataPoint]
    ) -> list[AssetDataPoint]:
        """
        Remove duplicate (date, ticker, feature_name) keeping highest version.
        
        Args:
            data_points: Input data points
            
        Returns:
            Deduplicated data points
        """
        # Group by (date, ticker, feature_name)
        from collections import defaultdict
        
        grouped = defaultdict(list)
        for dp in data_points:
            key = (dp.date, dp.ticker, dp.feature_name)
            grouped[key].append(dp)

        deduped = []
        duplicates_removed = 0

        for key, points in grouped.items():
            if len(points) == 1:
                deduped.append(points[0])
            else:
                # Keep highest version
                best = max(points, key=lambda p: p.version)
                deduped.append(best)
                duplicates_removed += len(points) - 1

        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate records")

        return deduped
