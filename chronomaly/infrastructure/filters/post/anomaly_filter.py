"""
Post-filter to keep only anomalous results.
"""

import pandas as pd
from .base import PostFilter


class AnomalyFilter(PostFilter):
    """
    Post-filter that keeps only anomalous detection results.

    This filter removes IN_RANGE and NO_FORECAST statuses, keeping only
    BELOW_P10 and ABOVE_P90 statuses.

    Args:
        exclude_no_forecast: If True, exclude NO_FORECAST status (default: True)

    Example:
        filter = AnomalyFilter()
        anomalies_only = filter.process(results_df)
    """

    def __init__(self, exclude_no_forecast: bool = True):
        self.exclude_no_forecast = exclude_no_forecast

    def process(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter to keep only anomalous results.

        Args:
            results_df: Anomaly detection results

        Returns:
            pd.DataFrame: Results containing only anomalies
        """
        if results_df.empty or 'status' not in results_df.columns:
            return results_df

        # Keep only BELOW_P10 and ABOVE_P90
        filtered_df = results_df[results_df['status'].isin(['BELOW_P10', 'ABOVE_P90'])].copy()

        return filtered_df
