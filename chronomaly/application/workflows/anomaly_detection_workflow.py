"""
Anomaly detection workflow orchestrator.
"""

import pandas as pd
from typing import Optional, List
from ...infrastructure.data.readers.base import DataReader
from ...infrastructure.anomaly_detectors.base import AnomalyDetector
from ...infrastructure.data.writers.base import DataWriter
from ...infrastructure.filters.pre import PreFilter
from ...infrastructure.filters.post import PostFilter


class AnomalyDetectionWorkflow:
    """
    Main orchestrator class for the anomaly detection workflow.

    This class coordinates the entire anomaly detection workflow:
    1. Load forecast and actual data from sources
    2. Apply pre-filters to reduce dataset (optional)
    3. Detect anomalies by comparing forecast vs actual
    4. Apply post-filters and transformations (optional)
    5. Write results to output

    Args:
        forecast_reader: Data reader instance for forecast data
        actual_reader: Data reader instance for actual data
        anomaly_detector: Anomaly detector instance
        data_writer: Data writer instance for anomaly results
        pre_filters: List of pre-filters to apply before detection (optional)
        post_filters: List of post-filters to apply after detection (optional)

    Example:
        from chronomaly.infrastructure.filters.pre import CumulativeThresholdFilter
        from chronomaly.infrastructure.filters.post import AnomalyFilter, DeviationFormatter

        # Configure workflow with pre and post filters
        workflow = AnomalyDetectionWorkflow(
            forecast_reader=forecast_reader,
            actual_reader=actual_reader,
            anomaly_detector=detector,
            data_writer=writer,
            pre_filters=[CumulativeThresholdFilter(transformer, threshold_pct=0.95)],
            post_filters=[AnomalyFilter(), DeviationFormatter()]
        )
    """

    def __init__(
        self,
        forecast_reader: DataReader,
        actual_reader: DataReader,
        anomaly_detector: AnomalyDetector,
        data_writer: DataWriter,
        pre_filters: Optional[List[PreFilter]] = None,
        post_filters: Optional[List[PostFilter]] = None
    ):
        self.forecast_reader = forecast_reader
        self.actual_reader = actual_reader
        self.anomaly_detector = anomaly_detector
        self.data_writer = data_writer
        self.pre_filters = pre_filters or []
        self.post_filters = post_filters or []

    def _execute_detection(self) -> pd.DataFrame:
        """
        Shared detection logic for running anomaly detection.

        Pipeline:
        1. Load data
        2. Apply pre-filters
        3. Detect anomalies
        4. Apply post-filters
        5. Return results

        Returns:
            pd.DataFrame: The anomaly detection results

        Raises:
            ValueError: If loaded data is empty or incompatible
        """
        # Step 1: Load forecast data
        forecast_df = self.forecast_reader.load()

        # Validate forecast data
        if forecast_df is None or forecast_df.empty:
            raise ValueError(
                "Forecast reader returned empty dataset. Cannot proceed with anomaly detection."
            )

        # Step 2: Load actual data
        actual_df = self.actual_reader.load()

        # Validate actual data
        if actual_df is None or actual_df.empty:
            raise ValueError(
                "Actual reader returned empty dataset. Cannot proceed with anomaly detection."
            )

        # Step 3: Apply pre-filters (e.g., cumulative threshold)
        for pre_filter in self.pre_filters:
            forecast_df, actual_df = pre_filter.filter(forecast_df, actual_df)

        # Step 4: Detect anomalies
        anomaly_df = self.anomaly_detector.detect(
            forecast_df=forecast_df,
            actual_df=actual_df
        )

        # Validate anomaly detection results
        if anomaly_df is None or anomaly_df.empty:
            raise ValueError(
                "Anomaly detector returned empty results. Check your data and configuration."
            )

        # Step 5: Apply post-filters (e.g., anomaly filter, deviation formatter)
        for post_filter in self.post_filters:
            anomaly_df = post_filter.process(anomaly_df)

        return anomaly_df

    def run(self) -> pd.DataFrame:
        """
        Execute the complete anomaly detection workflow.

        Returns:
            pd.DataFrame: The anomaly detection results

        Raises:
            ValueError: If loaded data is empty or incompatible
        """
        anomaly_df = self._execute_detection()
        self.data_writer.write(anomaly_df)
        return anomaly_df

    def run_without_output(self) -> pd.DataFrame:
        """
        Execute anomaly detection workflow without writing to output.

        Useful for testing or when you want to inspect results before writing.

        Returns:
            pd.DataFrame: The anomaly detection results

        Raises:
            ValueError: If loaded data is empty or incompatible
        """
        return self._execute_detection()
