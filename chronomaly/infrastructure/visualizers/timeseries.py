"""
Anomaly visualization implementation.
"""

import io
import base64
from typing import Any, Optional
from pathlib import Path

import pandas as pd

from chronomaly.infrastructure.data.readers.base import DataReader


class TimeSeriesVisualizer:
    """
    Visualization class for time series anomaly data.

    Works independently and generates line charts using matplotlib.
    Standalone implementation of chart generation for anomaly visualization.

    Args:
        anomaly_data: DataReader instance for anomaly detection results.
                      Must have a 'group_key' column identifying metrics.
        history_data: DataReader instance for historical time series data.
                      Columns should match group_key values from anomaly_data.
    """

    def __init__(
        self,
        anomaly_data: DataReader,
        history_data: DataReader,
    ) -> None:
        """
        Initialize TimeSeriesVisualizer.

        Args:
            anomaly_data: DataReader for anomaly detection results (required)
            history_data: DataReader for historical time series (required)

        Raises:
            TypeError: If parameters are not DataReader instances
        """
        if not isinstance(anomaly_data, DataReader):
            raise TypeError(
                f"anomaly_data must be a DataReader instance, "
                f"got {type(anomaly_data).__name__}"
            )
        if not isinstance(history_data, DataReader):
            raise TypeError(
                f"history_data must be a DataReader instance, "
                f"got {type(history_data).__name__}"
            )

        self._anomaly_data: DataReader = anomaly_data
        self._history_data: DataReader = history_data

    def _create_line_chart(
        self, metric_name: str, data: pd.Series, title: Optional[str] = None
    ) -> str:
        """
        Create a line chart for a single metric and return as base64 string.

        Args:
            metric_name: Name of the metric
            data: Time series data (Series with DatetimeIndex)
            title: Optional chart title (defaults to metric_name)

        Returns:
            str: Base64-encoded PNG image
        """
        import matplotlib

        matplotlib.use("Agg")  # Non-interactive backend
        import matplotlib.pyplot as plt
        import matplotlib.dates
        from matplotlib.ticker import EngFormatter

        # Create figure
        plt.figure(figsize=(8, 4.5))

        # Plot line chart with markers
        plt.plot(
            data.index,
            data.values,
            marker="o",
            linewidth=2,
            markersize=6,
            color="#2E86AB",
        )

        # Title
        if title:
            plt.title(title, fontsize=12, fontweight="bold")

        # Grid
        plt.grid(True, alpha=0.3)

        # Format x-axis dates
        ax = plt.gca()
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y-%m-%d"))
        ax.xaxis.set_major_locator(matplotlib.dates.DayLocator(interval=2))
        plt.xticks(rotation=45, ha="right")

        # Format y-axis with k, M, G suffixes for large numbers
        ax.yaxis.set_major_formatter(EngFormatter())

        # Tight layout
        plt.tight_layout()

        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", dpi=75, bbox_inches="tight")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        plt.close()

        return image_base64

    def _create_line_chart_figure(
        self, metric_name: str, data: pd.Series, title: Optional[str] = None
    ):
        """
        Create a line chart and return matplotlib figure object.

        Args:
            metric_name: Name of the metric
            data: Time series data (Series with DatetimeIndex)
            title: Optional chart title (defaults to metric_name)

        Returns:
            matplotlib.figure.Figure: The chart figure object
        """
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates
        from matplotlib.ticker import EngFormatter

        fig, ax = plt.subplots(figsize=(8, 4.5))

        ax.plot(
            data.index,
            data.values,
            marker="o",
            linewidth=2,
            markersize=6,
            color="#2E86AB",
        )

        if title:
            ax.set_title(title, fontsize=12, fontweight="bold")

        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y-%m-%d"))
        ax.xaxis.set_major_locator(matplotlib.dates.DayLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
        ax.yaxis.set_major_formatter(EngFormatter())

        fig.tight_layout()

        return fig

    def generate_charts(self) -> dict[str, str]:
        """
        Generate line charts for all anomalous metrics.

        Loads data from both readers, identifies anomalous metrics from
        anomaly_data, and generates charts using history_data.

        Returns:
            dict: Mapping of metric names to base64-encoded chart images

        Example:
            >>> charts = visualizer.generate_charts()
            >>> # {'metric_a': 'iVBORw0KGgo...', 'metric_b': 'iVBORw0KGgo...'}
        """
        import warnings

        # Load data from readers
        try:
            anomaly_df = self._anomaly_data.load()
        except Exception as e:
            warnings.warn(f"Failed to load anomaly data: {str(e)}")
            return {}

        try:
            history_df = self._history_data.load()
        except Exception as e:
            warnings.warn(f"Failed to load history data: {str(e)}")
            return {}

        # Validate anomaly_df has group_key column
        if "group_key" not in anomaly_df.columns:
            warnings.warn(
                "Anomaly data does not contain 'group_key' column. "
                "Cannot generate charts."
            )
            return {}

        # Get unique group_keys from anomalies
        anomalous_metrics = anomaly_df["group_key"].unique()

        # Generate charts for each metric
        charts: dict[str, str] = {}
        for metric in anomalous_metrics:
            if metric in history_df.columns:
                metric_data = history_df[metric]

                # Skip if all NaN
                if metric_data.notna().any():
                    try:
                        chart_base64 = self._create_line_chart(metric, metric_data)
                        charts[metric] = chart_base64
                    except (ValueError, TypeError, RuntimeError) as e:
                        warnings.warn(
                            f"Failed to generate chart for metric '{metric}': {str(e)}"
                        )
                        continue

        return charts

    def save_charts(
        self,
        output_dir: str,
        format: str = "png",
        dpi: int = 75,
    ) -> list[str]:
        """
        Generate and save charts to files.

        Args:
            output_dir: Directory path to save chart images
            format: Image format (png, jpg, pdf, svg)
            dpi: Resolution for output images

        Returns:
            list: List of saved file paths

        Raises:
            ValueError: If output_dir is not a valid directory
        """
        import warnings
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Load data from readers
        try:
            anomaly_df = self._anomaly_data.load()
        except Exception as e:
            warnings.warn(f"Failed to load anomaly data: {str(e)}")
            return []

        try:
            history_df = self._history_data.load()
        except Exception as e:
            warnings.warn(f"Failed to load history data: {str(e)}")
            return []

        if "group_key" not in anomaly_df.columns:
            warnings.warn(
                "Anomaly data does not contain 'group_key' column. "
                "Cannot generate charts."
            )
            return []

        anomalous_metrics = anomaly_df["group_key"].unique()
        saved_files: list[str] = []

        for metric in anomalous_metrics:
            if metric in history_df.columns:
                metric_data = history_df[metric]

                if metric_data.notna().any():
                    try:
                        fig = self._create_line_chart_figure(metric, metric_data)
                        # Sanitize metric name for filename
                        safe_name = str(metric).replace("/", "_").replace("\\", "_")
                        file_path = output_path / f"{safe_name}.{format}"
                        fig.savefig(
                            file_path, format=format, dpi=dpi, bbox_inches="tight"
                        )
                        plt.close(fig)
                        saved_files.append(str(file_path))
                    except (ValueError, TypeError, RuntimeError) as e:
                        warnings.warn(
                            f"Failed to save chart for metric '{metric}': {str(e)}"
                        )
                        continue

        return saved_files

    def get_figures(self) -> dict[str, Any]:
        """
        Generate and return matplotlib figure objects.

        Useful when you need direct access to figures for further
        customization or display in notebooks.

        Returns:
            dict: Mapping of metric names to matplotlib Figure objects

        Note:
            Caller is responsible for closing figures with plt.close(fig)
            to avoid memory leaks.
        """
        import warnings

        # Load data from readers
        try:
            anomaly_df = self._anomaly_data.load()
        except Exception as e:
            warnings.warn(f"Failed to load anomaly data: {str(e)}")
            return {}

        try:
            history_df = self._history_data.load()
        except Exception as e:
            warnings.warn(f"Failed to load history data: {str(e)}")
            return {}

        if "group_key" not in anomaly_df.columns:
            warnings.warn(
                "Anomaly data does not contain 'group_key' column. "
                "Cannot generate charts."
            )
            return {}

        anomalous_metrics = anomaly_df["group_key"].unique()
        figures = {}

        for metric in anomalous_metrics:
            if metric in history_df.columns:
                metric_data = history_df[metric]

                if metric_data.notna().any():
                    try:
                        fig = self._create_line_chart_figure(metric, metric_data)
                        figures[metric] = fig
                    except (ValueError, TypeError, RuntimeError) as e:
                        warnings.warn(
                            f"Failed to create figure for metric '{metric}': {str(e)}"
                        )
                        continue

        return figures
