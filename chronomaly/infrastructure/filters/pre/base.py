"""
Base abstract class for pre-filters.
"""

from abc import ABC, abstractmethod
import pandas as pd


class PreFilter(ABC):
    """
    Abstract base class for pre-filters that process data before anomaly detection.

    Pre-filters are used to reduce the dataset size or select specific metrics
    before running anomaly detection algorithms.
    """

    @abstractmethod
    def filter(self, forecast_df: pd.DataFrame, actual_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Filter forecast and actual data before anomaly detection.

        Args:
            forecast_df: Forecast data
            actual_df: Actual data

        Returns:
            tuple: (filtered_forecast_df, filtered_actual_df)
        """
        pass
