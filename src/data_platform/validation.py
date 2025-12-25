"""
Data validation using Pandera schemas.

Validates AssetDataPoint and DailyFactRecord instances.
"""

import pandera as pa
from pandera import Column, DataFrameSchema, Check
from datetime import date, datetime
from typing import Optional

from data_platform.models import AssetClass, Vendor, FeatureType


# Schema for AssetDataPoint validation
asset_data_point_schema = DataFrameSchema(
    {
        "date": Column(
            pa.DateTime,
            checks=[
                Check.less_than_or_equal_to(datetime.now()),
                Check.greater_than(datetime(2000, 1, 1)),
            ],
            nullable=False,
            coerce=True,
        ),
        "ticker": Column(
            pa.String,
            checks=[
                Check.str_length(min_value=1, max_value=50),
            ],
            nullable=False,
        ),
        "asset_class": Column(
            pa.String,
            checks=[Check.isin([ac.value for ac in AssetClass])],
            nullable=False,
        ),
        "symbol": Column(
            pa.String,
            checks=[Check.str_length(min_value=1, max_value=50)],
            nullable=False,
        ),
        "feature_name": Column(
            pa.String,
            checks=[Check.str_length(min_value=1, max_value=100)],
            nullable=False,
        ),
        "feature_type": Column(
            pa.String,
            checks=[Check.isin([ft.value for ft in FeatureType])],
            nullable=False,
        ),
        "value": Column(
            pa.Float,
            checks=[
                Check.in_range(-1e15, 1e15),  # Reasonable bounds
            ],
            nullable=True,
        ),
        "vendor": Column(
            pa.String,
            checks=[Check.isin([v.value for v in Vendor])],
            nullable=False,
        ),
    },
    strict=False,  # Allow additional columns
    coerce=True,
)


# Schema for DailyFactRecord validation
daily_fact_schema = DataFrameSchema(
    {
        "date": Column(
            pa.DateTime,
            checks=[
                Check.less_than_or_equal_to(datetime.now()),
                Check.greater_than(datetime(2000, 1, 1)),
            ],
            nullable=False,
            coerce=True,
        ),
        "ticker": Column(
            pa.String,
            checks=[Check.str_length(min_value=1, max_value=50)],
            nullable=False,
        ),
        "asset_class": Column(
            pa.String,
            checks=[Check.isin([ac.value for ac in AssetClass])],
            nullable=False,
        ),
        "close_price": Column(
            pa.Float,
            checks=[Check.greater_than(0)],  # Prices should be positive
            nullable=True,
        ),
        "daily_return": Column(
            pa.Float,
            checks=[
                Check.in_range(-0.5, 0.5)  # Daily returns typically < 50%
            ],
            nullable=True,
        ),
        "vendor": Column(
            pa.String,
            checks=[Check.isin([v.value for v in Vendor])],
            nullable=False,
        ),
    },
    strict=False,
    coerce=True,
)


class DataQualityChecker:
    """
    Data quality checks for ingested data.
    
    Validates:
    - No future dates
    - No duplicates on (date, ticker)
    - Null rate thresholds
    - Value ranges
    - Time series monotonicity
    """

    def __init__(
        self,
        max_null_rate: float = 0.5,
        check_monotonic_time: bool = True,
    ):
        """
        Initialize data quality checker.
        
        Args:
            max_null_rate: Maximum acceptable null rate (0-1)
            check_monotonic_time: Whether to check time series is monotonic
        """
        self.max_null_rate = max_null_rate
        self.check_monotonic_time = check_monotonic_time

    def check(self, data_points: list) -> tuple[bool, list[str]]:
        """
        Run all quality checks.
        
        Args:
            data_points: List of AssetDataPoint or DailyFactRecord instances
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if not data_points:
            return True, []

        # Check for future dates
        today = date.today()
        future_dates = [
            dp for dp in data_points 
            if dp.date > today
        ]
        if future_dates:
            errors.append(
                f"Found {len(future_dates)} records with future dates"
            )

        # Check for duplicates on (date, ticker)
        seen = set()
        duplicates = []
        for dp in data_points:
            key = (dp.date, dp.ticker)
            if key in seen:
                duplicates.append(key)
            seen.add(key)

        if duplicates:
            errors.append(
                f"Found {len(duplicates)} duplicate (date, ticker) pairs"
            )

        # Check null rates for value fields
        if hasattr(data_points[0], 'value'):
            # AssetDataPoint
            null_count = sum(1 for dp in data_points if dp.value is None)
        else:
            # DailyFactRecord - check close_price
            null_count = sum(
                1 for dp in data_points 
                if dp.close_price is None
            )

        null_rate = null_count / len(data_points)
        if null_rate > self.max_null_rate:
            errors.append(
                f"Null rate {null_rate:.2%} exceeds threshold {self.max_null_rate:.2%}"
            )

        # Check time monotonicity
        if self.check_monotonic_time:
            dates = [dp.date for dp in data_points]
            if dates != sorted(dates):
                errors.append("Dates are not monotonically increasing")

        is_valid = len(errors) == 0
        return is_valid, errors

    def check_outliers(
        self,
        data_points: list,
        z_score_threshold: float = 5.0,
    ) -> tuple[bool, list[str]]:
        """
        Check for outliers using z-score.
        
        Args:
            data_points: List of data points
            z_score_threshold: Z-score threshold for outlier detection
            
        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        warnings = []

        if not data_points:
            return True, []

        # Extract values
        if hasattr(data_points[0], 'value'):
            values = [dp.value for dp in data_points if dp.value is not None]
        else:
            values = [
                dp.close_price 
                for dp in data_points 
                if dp.close_price is not None
            ]

        if len(values) < 10:
            # Not enough data for outlier detection
            return True, []

        # Compute z-scores
        import numpy as np
        
        values_array = np.array(values)
        mean = np.mean(values_array)
        std = np.std(values_array)

        if std == 0:
            return True, []

        z_scores = np.abs((values_array - mean) / std)
        outlier_count = np.sum(z_scores > z_score_threshold)

        if outlier_count > 0:
            outlier_rate = outlier_count / len(values)
            warnings.append(
                f"Found {outlier_count} outliers ({outlier_rate:.2%}) "
                f"with z-score > {z_score_threshold}"
            )

        return True, warnings  # Outliers are warnings, not errors
