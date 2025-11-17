"""
Date range filter - filters DataFrame rows based on date/datetime ranges.
"""

import pandas as pd
from typing import Union, Optional
from datetime import datetime
from .base import DataFrameFilter


class DateRangeFilter(DataFrameFilter):
    """
    Filter DataFrame rows based on date/datetime ranges.

    This filter can work with:
    1. DataFrame index (if it's datetime)
    2. Specific date column
    3. Both start_date and end_date (inclusive)
    4. Only start_date (no upper bound)
    5. Only end_date (no lower bound)

    Args:
        start_date: Start date (inclusive), None for no start bound (optional)
        end_date: End date (inclusive), None for no end bound (optional)
        date_column: Column name to filter on. If None, uses DataFrame index (default: None)

    Example 1 - Filter by index (last 30 days):
        filter = DateRangeFilter(start_date='2024-01-01', end_date='2024-01-31')
        filtered = filter.filter(df)

    Example 2 - Filter by specific column:
        filter = DateRangeFilter(
            start_date='2024-01-01',
            end_date='2024-12-31',
            date_column='transaction_date'
        )
        filtered = filter.filter(df)

    Example 3 - Only start date (from date onwards):
        filter = DateRangeFilter(start_date='2024-01-01')
        filtered = filter.filter(df)

    Example 4 - Only end date (up to date):
        filter = DateRangeFilter(end_date='2024-12-31')
        filtered = filter.filter(df)

    Example 5 - Using datetime objects:
        from datetime import datetime
        filter = DateRangeFilter(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31)
        )
        filtered = filter.filter(df)
    """

    def __init__(
        self,
        start_date: Optional[Union[str, datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[str, datetime, pd.Timestamp]] = None,
        date_column: Optional[str] = None
    ):
        # Validate inputs
        if start_date is None and end_date is None:
            raise ValueError("At least one of 'start_date' or 'end_date' must be specified")

        self.start_date = pd.to_datetime(start_date) if start_date is not None else None
        self.end_date = pd.to_datetime(end_date) if end_date is not None else None
        self.date_column = date_column

        # Validate date order
        if self.start_date is not None and self.end_date is not None:
            if self.start_date > self.end_date:
                raise ValueError(f"start_date ({self.start_date}) must be before or equal to end_date ({self.end_date})")

    def filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter DataFrame by date range.

        Args:
            df: Input DataFrame

        Returns:
            pd.DataFrame: Filtered DataFrame

        Raises:
            ValueError: If date_column is specified but not found in DataFrame
            ValueError: If using index filtering but index is not datetime
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        # Determine which date source to use
        if self.date_column is not None:
            # Use specific column
            if self.date_column not in df.columns:
                raise ValueError(f"Column '{self.date_column}' not found in DataFrame")

            date_series = pd.to_datetime(result[self.date_column])

            # Apply date range filters
            if self.start_date is not None:
                result = result[date_series >= self.start_date]
                date_series = pd.to_datetime(result[self.date_column])  # Update after filter

            if self.end_date is not None:
                result = result[date_series <= self.end_date]

            # Reset index after filtering to ensure consistent indexing
            result = result.reset_index(drop=True)
        else:
            # Use index
            if not isinstance(result.index, pd.DatetimeIndex):
                try:
                    result.index = pd.to_datetime(result.index)
                except Exception as e:
                    raise ValueError(f"DataFrame index cannot be converted to datetime: {e}")

            # Apply date range filters on index
            if self.start_date is not None:
                result = result[result.index >= self.start_date]

            if self.end_date is not None:
                result = result[result.index <= self.end_date]

        return result
