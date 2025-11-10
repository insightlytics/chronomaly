"""
Cumulative threshold pre-filter implementation.
"""

import pandas as pd
from typing import List, Optional
from .base import PreFilter
from ...transformers.pivot import DataTransformer


class CumulativeThresholdFilter(PreFilter):
    """
    Pre-filter that keeps only top X% of metrics by cumulative forecast value.

    This filter reduces the dataset to the most significant metrics based on
    their forecast values before anomaly detection runs.

    Args:
        transformer: DataTransformer to pivot actual data
        threshold_pct: Cumulative percentage threshold (e.g., 0.95 for top 95%)
        value_column_pattern: Pattern to identify forecast value column (default: uses point forecast)
        exclude_columns: Columns to exclude from filtering (e.g., ['date'])

    Example:
        # Keep only metrics that make up top 95% of forecast volume
        filter = CumulativeThresholdFilter(
            transformer=transformer,
            threshold_pct=0.95
        )

        filtered_forecast, filtered_actual = filter.filter(forecast_df, actual_df)
    """

    def __init__(
        self,
        transformer: DataTransformer,
        threshold_pct: float = 0.95,
        exclude_columns: Optional[List[str]] = None
    ):
        if not 0 < threshold_pct <= 1.0:
            raise ValueError(f"threshold_pct must be between 0 and 1, got {threshold_pct}")

        self.transformer = transformer
        self.threshold_pct = threshold_pct
        self.exclude_columns = exclude_columns or ['date']

    def filter(self, forecast_df: pd.DataFrame, actual_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Filter to keep only top X% of metrics by cumulative forecast value.

        Args:
            forecast_df: Forecast data in pivot format
            actual_df: Actual data in raw format

        Returns:
            tuple: (filtered_forecast_df, filtered_actual_df)
        """
        if forecast_df.empty or actual_df.empty:
            return forecast_df, actual_df

        # Extract point forecasts from pipe-separated values
        forecast_values = {}
        for col in forecast_df.columns:
            if col not in self.exclude_columns:
                # Extract point forecast (first value before |)
                try:
                    values = forecast_df[col].apply(lambda x: float(str(x).split('|')[0]))
                    forecast_values[col] = values.sum()
                except (ValueError, IndexError):
                    forecast_values[col] = 0.0

        if not forecast_values:
            return forecast_df, actual_df

        # Create series and sort by value
        value_series = pd.Series(forecast_values).sort_values(ascending=False)

        # Calculate cumulative percentage
        cumulative_sum = value_series.cumsum()
        total_value = value_series.sum()

        if total_value == 0:
            return forecast_df, actual_df

        cumulative_pct = cumulative_sum / total_value

        # Find metrics to keep
        threshold_mask = cumulative_pct <= self.threshold_pct
        metrics_to_keep = value_series[threshold_mask].index.tolist()

        # Always include at least one metric
        if not metrics_to_keep and len(value_series) > 0:
            metrics_to_keep = [value_series.index[0]]

        # Filter forecast DataFrame
        columns_to_keep = list(self.exclude_columns) + metrics_to_keep
        filtered_forecast = forecast_df[[col for col in columns_to_keep if col in forecast_df.columns]].copy()

        # Filter actual DataFrame
        # Parse metric names to filter actual data
        if hasattr(self.transformer, 'columns'):
            # Extract dimensions from metric names
            filtered_actual = self._filter_actual_by_metrics(actual_df, metrics_to_keep)
        else:
            filtered_actual = actual_df.copy()

        return filtered_forecast, filtered_actual

    def _filter_actual_by_metrics(self, actual_df: pd.DataFrame, metrics_to_keep: List[str]) -> pd.DataFrame:
        """
        Filter actual DataFrame to keep only rows matching the metrics.

        Args:
            actual_df: Actual data in raw format
            metrics_to_keep: List of metric names to keep

        Returns:
            pd.DataFrame: Filtered actual data
        """
        if actual_df.empty:
            return actual_df

        # Get transformer columns
        transformer_columns = self.transformer.columns
        if isinstance(transformer_columns, str):
            transformer_columns = [transformer_columns]
        else:
            transformer_columns = list(transformer_columns)

        # Build filter conditions
        filtered_rows = []
        for metric in metrics_to_keep:
            # Split metric name by underscore
            parts = metric.split('_')

            # Create filter condition
            if len(parts) == len(transformer_columns):
                mask = pd.Series([True] * len(actual_df))
                for i, col in enumerate(transformer_columns):
                    if col in actual_df.columns:
                        mask &= (actual_df[col] == parts[i])

                filtered_rows.append(actual_df[mask])

        if filtered_rows:
            return pd.concat(filtered_rows, ignore_index=True).drop_duplicates()
        else:
            return pd.DataFrame(columns=actual_df.columns)
