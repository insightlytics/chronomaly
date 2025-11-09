"""
Forecast vs Actual anomaly detection implementation.
"""

import warnings
import pandas as pd
import numpy as np
from typing import Optional, Union, List
from .base import AnomalyDetector
from ..transformers.pivot import DataTransformer


class ForecastActualComparator(AnomalyDetector):
    """
    Anomaly detector that compares forecast quantiles with actual values.

    This detector:
    1. Pivots actual data (raw format) to match forecast format
    2. Extracts q10 and q90 from pipe-separated forecast values (80% confidence interval)
    3. Compares actual values against the confidence interval
    4. Calculates deviation percentages
    5. Splits metric names into dimension columns (optional)
    6. Filters by cumulative threshold (optional)
    7. Returns only anomalies (optional)

    The forecast data is expected to be in pivot format with pipe-separated quantiles:
    "point|q10|q20|q30|q40|q50|q60|q70|q80|q90"
    where q10 is at index 1 and q90 is at index 9.

    Args:
        transformer: DataTransformer instance to pivot actual data
        date_column: Name of the date column (default: 'date')
        exclude_columns: List of columns to exclude from comparison (e.g., ['date', 'company'])
        dimension_names: List of dimension names to extract from metric (e.g., ['platform', 'channel', 'landing_page'])
        cumulative_threshold: Filter to top X% of metrics by forecast value (e.g., 0.95 for top 95%)
        return_only_anomalies: If True, return only BELOW_P10 and ABOVE_P90 statuses (default: False)
        min_deviation_threshold: Minimum deviation threshold to include (e.g., 0.05 for 5%)
        format_deviation_as_string: If True, format deviation_pct as "15.3%" instead of 15.3
    """

    # Quantile indices for pipe-separated forecast format
    QUANTILE_POINT_IDX = 0
    QUANTILE_Q10_IDX = 1
    QUANTILE_Q90_IDX = 9
    EXPECTED_QUANTILE_COUNT = 10

    def __init__(
        self,
        transformer: DataTransformer,
        date_column: str = 'date',
        exclude_columns: Optional[List[str]] = None,
        dimension_names: Optional[List[str]] = None,
        cumulative_threshold: Optional[float] = None,
        return_only_anomalies: bool = False,
        min_deviation_threshold: float = 0.0,
        format_deviation_as_string: bool = False
    ):
        self.transformer = transformer
        self.date_column = date_column
        self.exclude_columns = exclude_columns or [date_column]
        self.dimension_names = dimension_names
        self.cumulative_threshold = cumulative_threshold
        self.return_only_anomalies = return_only_anomalies
        self.min_deviation_threshold = min_deviation_threshold
        self.format_deviation_as_string = format_deviation_as_string

        # Validate dimension_names matches transformer.columns
        if dimension_names is not None:
            self._validate_dimension_names()

    def _validate_dimension_names(self):
        """
        Validate that dimension_names matches transformer.columns order.

        Raises:
            ValueError: If dimension_names doesn't match transformer.columns
        """
        if not hasattr(self.transformer, 'columns'):
            # Transformer doesn't expose columns, skip validation
            return

        # Convert transformer.columns to list for comparison
        transformer_columns = self.transformer.columns
        if isinstance(transformer_columns, str):
            transformer_columns = [transformer_columns]
        else:
            transformer_columns = list(transformer_columns)

        # Convert dimension_names to list for comparison
        dimension_names = list(self.dimension_names)

        # Check if they match
        if dimension_names != transformer_columns:
            raise ValueError(
                f"dimension_names must match transformer.columns in the same order.\n"
                f"  dimension_names: {dimension_names}\n"
                f"  transformer.columns: {transformer_columns}\n"
                f"Expected: dimension_names={transformer_columns}"
            )

    def detect(
        self,
        forecast_df: pd.DataFrame,
        actual_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Detect anomalies by comparing forecast quantiles with actual values.

        Args:
            forecast_df: Forecast data in pivot format with pipe-separated quantiles
            actual_df: Actual data in raw format (will be pivoted)

        Returns:
            pd.DataFrame: Anomaly detection results with columns:
                - date: The date of the observation (if available)
                - metric: The metric name (if dimension_names not specified)
                - [dimension columns]: Separate columns for each dimension (if dimension_names specified)
                - actual: Actual value
                - forecast: Point forecast (q50)
                - q10: Lower bound of 80% confidence interval
                - q90: Upper bound of 80% confidence interval
                - status: IN_RANGE, BELOW_P10, ABOVE_P90, or NO_FORECAST
                - deviation_pct: Percentage deviation from q10 or q90

        Raises:
            TypeError: If inputs are not pandas DataFrames
            ValueError: If dataframes are empty or incompatible
        """
        # Step 1: Validate inputs
        self._validate_inputs(forecast_df, actual_df)

        # Step 2: Prepare and standardize data
        forecast_std, actual_std, all_columns = self._prepare_data(forecast_df, actual_df)

        # Step 3: Compare all metrics
        results = self._compare_all_metrics(forecast_std, actual_std, all_columns)

        # Step 4: Create result dataframe
        if not results:
            return pd.DataFrame()

        result_df = pd.DataFrame(results)

        # Step 5: Post-process results
        result_df = self._post_process_results(result_df)

        return result_df

    def _validate_inputs(self, forecast_df: pd.DataFrame, actual_df: pd.DataFrame) -> None:
        """
        Validate input DataFrames.

        Args:
            forecast_df: Forecast data
            actual_df: Actual data

        Raises:
            TypeError: If inputs are not pandas DataFrames
            ValueError: If dataframes are empty
        """
        if not isinstance(forecast_df, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame for forecast_df, got {type(forecast_df).__name__}"
            )
        if not isinstance(actual_df, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame for actual_df, got {type(actual_df).__name__}"
            )

        if forecast_df.empty:
            raise ValueError("Forecast DataFrame is empty")
        if actual_df.empty:
            raise ValueError("Actual DataFrame is empty")

    def _prepare_data(
        self,
        forecast_df: pd.DataFrame,
        actual_df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, list]:
        """
        Pivot and standardize data for comparison.

        Args:
            forecast_df: Forecast data in pivot format
            actual_df: Actual data in raw format

        Returns:
            tuple: (forecast_std, actual_std, all_columns)
        """
        # Pivot actual data to match forecast format
        actual_pivot = self.transformer.pivot_table(actual_df)
        actual_pivot = actual_pivot.reset_index()

        # Standardize columns between forecast and actual
        forecast_cols = set(forecast_df.columns) - set(self.exclude_columns)
        actual_cols = set(actual_pivot.columns) - set(self.exclude_columns)

        # Get all unique columns
        all_columns = sorted(forecast_cols.union(actual_cols))

        # Standardize forecast dataframe with string fill value
        forecast_std = self._standardize_forecast_columns(
            forecast_df.copy(),
            all_columns
        )

        # Standardize actual dataframe with numeric fill value
        actual_std = self._standardize_actual_columns(
            actual_pivot.copy(),
            all_columns
        )

        return forecast_std, actual_std, all_columns

    def _compare_all_metrics(
        self,
        forecast_std: pd.DataFrame,
        actual_std: pd.DataFrame,
        all_columns: list
    ) -> list:
        """
        Compare forecast and actual for all metrics across all rows.

        Args:
            forecast_std: Standardized forecast data
            actual_std: Standardized actual data
            all_columns: List of all metric columns to compare

        Returns:
            list: List of comparison result dictionaries
        """
        results = []

        # Iterate through data rows (assuming single row or date-based rows)
        for idx in forecast_std.index:
            # Get date if available
            date_value = forecast_std.loc[idx, self.date_column] if self.date_column in forecast_std.columns else None

            forecast_row = forecast_std.loc[idx]
            actual_row = actual_std.loc[idx] if idx in actual_std.index else None

            if actual_row is None:
                continue

            # Compare each metric column
            for column in all_columns:
                result = self._compare_metric(
                    column=column,
                    forecast_value=forecast_row[column],
                    actual_value=actual_row[column],
                    date_value=date_value
                )
                results.append(result)

        return results

    def _post_process_results(self, result_df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply post-processing to results: dimension splitting, filtering, formatting.

        Args:
            result_df: Raw anomaly detection results

        Returns:
            pd.DataFrame: Post-processed results
        """
        # Split metric names into dimension columns (if specified)
        if self.dimension_names:
            result_df = self._split_metric_to_dimensions(result_df)

        # Apply cumulative threshold filter (if specified)
        if self.cumulative_threshold is not None:
            result_df = self._filter_cumulative_threshold(
                result_df,
                'forecast',
                self.cumulative_threshold
            )

        # Filter only anomalies (if specified)
        if self.return_only_anomalies or self.min_deviation_threshold > 0:
            result_df = self._filter_anomalies(result_df)

        # Format deviation as string (if specified)
        if self.format_deviation_as_string and not result_df.empty:
            result_df['deviation_pct'] = (
                (result_df['deviation_pct'].round(1).astype(str) + '%')
            )

        # Remove metric column if dimensions were extracted
        if self.dimension_names and 'metric' in result_df.columns:
            result_df = result_df.drop(columns=['metric'])

        return result_df

    def _standardize_columns(
        self,
        df: pd.DataFrame,
        column_list: List[str],
        fill_value: Union[str, float]
    ) -> pd.DataFrame:
        """
        Add missing columns with fill values.

        Args:
            df: DataFrame to standardize
            column_list: List of columns that should exist
            fill_value: Value to use for missing columns

        Returns:
            pd.DataFrame: Standardized dataframe
        """
        missing_columns = [col for col in column_list if col not in df.columns]

        if missing_columns:
            new_cols_df = pd.DataFrame(
                fill_value,
                index=df.index,
                columns=missing_columns
            )
            df = pd.concat([df, new_cols_df], axis=1)

        # Fill NaN values
        for column in column_list:
            df[column] = df[column].fillna(fill_value).replace('None', fill_value)

        return df

    def _standardize_forecast_columns(
        self,
        df: pd.DataFrame,
        column_list: List[str]
    ) -> pd.DataFrame:
        """
        Standardize forecast DataFrame columns with string fill values.

        Args:
            df: Forecast DataFrame to standardize
            column_list: List of columns that should exist

        Returns:
            pd.DataFrame: Standardized forecast dataframe
        """
        fill_value = '0|0|0|0|0|0|0|0|0|0'  # Default pipe-separated zeros
        return self._standardize_columns(df, column_list, fill_value)

    def _standardize_actual_columns(
        self,
        df: pd.DataFrame,
        column_list: List[str]
    ) -> pd.DataFrame:
        """
        Standardize actual DataFrame columns with numeric fill values.

        Args:
            df: Actual DataFrame to standardize
            column_list: List of columns that should exist

        Returns:
            pd.DataFrame: Standardized actual dataframe
        """
        fill_value = 0.0  # Default numeric zero
        return self._standardize_columns(df, column_list, fill_value)

    def _compare_metric(
        self,
        column: str,
        forecast_value: str,
        actual_value: float,
        date_value: Optional[pd.Timestamp] = None
    ) -> dict:
        """
        Compare a single metric between forecast and actual.

        Args:
            column: Metric name
            forecast_value: Pipe-separated forecast string
            actual_value: Actual numeric value
            date_value: Date of the observation

        Returns:
            dict: Comparison result with status and deviation
        """
        # Parse forecast quantiles
        forecast_parts = str(forecast_value).split('|')

        try:
            # Extract values using class constants
            point_forecast = float(forecast_parts[self.QUANTILE_POINT_IDX]) if len(forecast_parts) > self.QUANTILE_POINT_IDX else 0.0
            q10 = float(forecast_parts[self.QUANTILE_Q10_IDX]) if len(forecast_parts) > self.QUANTILE_Q10_IDX else 0.0
            q90 = float(forecast_parts[self.QUANTILE_Q90_IDX]) if len(forecast_parts) > self.QUANTILE_Q90_IDX else 0.0

            # Validate quantile count
            if len(forecast_parts) < self.EXPECTED_QUANTILE_COUNT:
                warnings.warn(
                    f"Expected {self.EXPECTED_QUANTILE_COUNT} quantiles, got {len(forecast_parts)}. "
                    f"Using available values."
                )
        except (ValueError, IndexError):
            # Invalid forecast format
            point_forecast = 0.0
            q10 = 0.0
            q90 = 0.0

        # Convert actual to float
        try:
            actual = float(actual_value)
        except (ValueError, TypeError):
            actual = 0.0

        # Determine status and deviation
        status = 'NO_FORECAST'
        deviation_pct = 0.0

        # Check for invalid or missing forecasts
        if pd.isna(q10) or pd.isna(q90) or pd.isna(point_forecast):
            status = 'NO_FORECAST'
        elif q10 == 0 and q90 == 0 and point_forecast == 0:
            # All forecast values are zero - no valid forecast
            status = 'NO_FORECAST'
        elif q10 <= actual <= q90:
            status = 'IN_RANGE'
        else:
            if actual < q10:
                status = 'BELOW_P10'
                # Calculate deviation percentage with proper zero handling
                if q10 != 0:
                    deviation_pct = ((q10 - actual) / q10 * 100)
                elif actual != 0:
                    # q10 is 0 but actual is negative - use absolute difference
                    deviation_pct = abs(actual) * 100
                else:
                    deviation_pct = 0.0
            elif actual > q90:
                status = 'ABOVE_P90'
                # Calculate deviation percentage with proper zero handling
                if q90 != 0:
                    deviation_pct = ((actual - q90) / q90 * 100)
                elif actual != 0:
                    # q90 is 0 but actual is positive - use absolute value
                    deviation_pct = abs(actual) * 100
                else:
                    deviation_pct = 0.0

        result = {
            'metric': column,
            'actual': round(actual),
            'forecast': round(point_forecast),
            'q10': round(q10),
            'q90': round(q90),
            'status': status,
            'deviation_pct': round(deviation_pct, 2)
        }

        # Add date if available
        if date_value is not None:
            result = {'date': date_value, **result}

        return result

    def _split_metric_to_dimensions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Split metric column into separate dimension columns.

        Args:
            df: DataFrame with 'metric' column

        Returns:
            pd.DataFrame: DataFrame with separate dimension columns
        """
        if 'metric' not in df.columns or not self.dimension_names:
            return df

        df = df.copy()

        # Split metric by underscore
        metric_parts = df['metric'].str.split('_', expand=True)

        # Assign to dimension columns
        for i, dim_name in enumerate(self.dimension_names):
            if i < metric_parts.shape[1]:
                df[dim_name] = metric_parts[i]
            else:
                df[dim_name] = None

        return df

    def _filter_cumulative_threshold(
        self,
        df: pd.DataFrame,
        value_column: str,
        threshold_pct: float = 0.95
    ) -> pd.DataFrame:
        """
        Filter DataFrame to keep only top X% of rows by cumulative sum.

        Args:
            df: Input DataFrame
            value_column: Column to use for cumulative calculation
            threshold_pct: Cumulative percentage threshold (e.g., 0.95 for 95%)

        Returns:
            pd.DataFrame: Filtered DataFrame
        """
        if df.empty:
            return df.copy()

        total_value = df[value_column].sum()

        if total_value == 0:
            return df.copy()

        # Sort values and calculate cumulative sum without creating DataFrame copy
        sorted_values = df[value_column].sort_values(ascending=False)
        cumulative_sum = sorted_values.cumsum()
        cumulative_pct = cumulative_sum / total_value

        # Find minimum threshold value
        threshold_mask = cumulative_pct >= threshold_pct
        if threshold_mask.any():
            threshold_idx = threshold_mask.idxmax()
            min_threshold = sorted_values.loc[:threshold_idx].min()
        else:
            min_threshold = sorted_values.min()

        # Filter original DataFrame by threshold
        return df[df[value_column] >= min_threshold].copy()

    def _filter_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter DataFrame to keep only anomalies.

        Args:
            df: Input DataFrame

        Returns:
            pd.DataFrame: Filtered DataFrame with only anomalies
        """
        if df.empty:
            return df

        # Filter by status
        if self.return_only_anomalies:
            df = df[df['status'].isin(['BELOW_P10', 'ABOVE_P90'])]

        # Filter by deviation threshold
        if self.min_deviation_threshold > 0:
            df = df[
                (df['status'] == 'IN_RANGE') |
                (df['deviation_pct'] >= self.min_deviation_threshold)
            ]

        return df

    def detect_with_filter(
        self,
        forecast_df: pd.DataFrame,
        actual_df: pd.DataFrame,
        min_deviation_pct: float = 5.0,
        exclude_no_forecast: bool = True
    ) -> pd.DataFrame:
        """
        Detect anomalies with filtering options.

        This is a convenience method for backward compatibility.
        For more control, use the constructor parameters instead.

        Args:
            forecast_df: Forecast data in pivot format
            actual_df: Actual data in raw format
            min_deviation_pct: Minimum deviation percentage to include (default: 5%)
            exclude_no_forecast: Exclude NO_FORECAST status (default: True)

        Returns:
            pd.DataFrame: Filtered anomaly results
        """
        # Run full detection
        result_df = self.detect(forecast_df, actual_df)

        # Apply filters
        if exclude_no_forecast:
            result_df = result_df[result_df['status'] != 'NO_FORECAST']

        # Filter by deviation percentage
        result_df = result_df[
            (result_df['status'] == 'IN_RANGE') |
            (result_df['deviation_pct'] >= min_deviation_pct)
        ]

        return result_df
