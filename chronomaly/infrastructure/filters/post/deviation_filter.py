"""
Post-filter to keep only results above minimum deviation threshold.
"""

import pandas as pd
from .base import PostFilter


class DeviationFilter(PostFilter):
    """
    Post-filter that keeps only results above a minimum deviation threshold.

    This filter removes results where the deviation percentage is below
    the specified threshold, helping focus on significant anomalies.

    Args:
        min_deviation_pct: Minimum deviation percentage (e.g., 5.0 for 5%)
        keep_in_range: If True, keep IN_RANGE status regardless of deviation (default: True)

    Example:
        # Keep only anomalies with at least 10% deviation
        filter = DeviationFilter(min_deviation_pct=10.0)
        significant_anomalies = filter.process(results_df)
    """

    def __init__(self, min_deviation_pct: float, keep_in_range: bool = True):
        if min_deviation_pct < 0:
            raise ValueError(f"min_deviation_pct must be non-negative, got {min_deviation_pct}")

        self.min_deviation_pct = min_deviation_pct
        self.keep_in_range = keep_in_range

    def process(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter to keep only results above minimum deviation threshold.

        Args:
            results_df: Anomaly detection results

        Returns:
            pd.DataFrame: Results with significant deviations
        """
        if results_df.empty or 'deviation_pct' not in results_df.columns:
            return results_df

        if self.keep_in_range and 'status' in results_df.columns:
            # Keep IN_RANGE status or deviation above threshold
            mask = (results_df['status'] == 'IN_RANGE') | (results_df['deviation_pct'] >= self.min_deviation_pct)
        else:
            # Only keep deviation above threshold
            mask = results_df['deviation_pct'] >= self.min_deviation_pct

        return results_df[mask].copy()
