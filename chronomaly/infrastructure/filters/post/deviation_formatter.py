"""
Post-transformer to format deviation percentage as string.
"""

import pandas as pd
from .base import PostFilter


class DeviationFormatter(PostFilter):
    """
    Post-transformer that formats deviation percentage as a string.

    Converts numeric deviation_pct values (e.g., 15.3) to formatted strings
    (e.g., "15.3%") for better readability in reports.

    Args:
        decimal_places: Number of decimal places to show (default: 1)

    Example:
        formatter = DeviationFormatter(decimal_places=2)
        formatted_results = formatter.process(results_df)
    """

    def __init__(self, decimal_places: int = 1):
        if decimal_places < 0:
            raise ValueError(f"decimal_places must be non-negative, got {decimal_places}")

        self.decimal_places = decimal_places

    def process(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """
        Format deviation percentage as string.

        Args:
            results_df: Anomaly detection results

        Returns:
            pd.DataFrame: Results with formatted deviation_pct column
        """
        if results_df.empty or 'deviation_pct' not in results_df.columns:
            return results_df

        results_df = results_df.copy()

        # Format deviation as string with percentage sign
        results_df['deviation_pct'] = (
            results_df['deviation_pct']
            .round(self.decimal_places)
            .astype(str) + '%'
        )

        return results_df
