"""
Tests for TimeSeriesVisualizer.
"""

import pytest
import pandas as pd
import base64
from chronomaly.infrastructure.visualizers import TimeSeriesVisualizer
from chronomaly.infrastructure.data.readers import DataFrameDataReader


class TestTimeSeriesVisualizerInit:
    """Tests for TimeSeriesVisualizer initialization."""

    def test_init_with_valid_readers(self):
        """Test initialization with valid DataReader instances."""
        anomaly_df = pd.DataFrame({"group_key": ["metric_a"], "value": [100]})
        history_df = pd.DataFrame(
            {"metric_a": [10, 20, 30]},
            index=pd.date_range("2024-01-01", periods=3),
        )

        anomaly_reader = DataFrameDataReader(anomaly_df)
        history_reader = DataFrameDataReader(history_df)

        visualizer = TimeSeriesVisualizer(
            anomaly_data=anomaly_reader,
            history_data=history_reader,
        )

        assert visualizer._anomaly_data is anomaly_reader
        assert visualizer._history_data is history_reader

    def test_init_with_invalid_anomaly_data_raises_error(self):
        """Test that non-DataReader anomaly_data raises TypeError."""
        history_df = pd.DataFrame({"metric_a": [10, 20, 30]})
        history_reader = DataFrameDataReader(history_df)

        with pytest.raises(TypeError, match="anomaly_data must be a DataReader"):
            TimeSeriesVisualizer(
                anomaly_data=pd.DataFrame(),  # Not a DataReader
                history_data=history_reader,
            )

    def test_init_with_invalid_history_data_raises_error(self):
        """Test that non-DataReader history_data raises TypeError."""
        anomaly_df = pd.DataFrame({"group_key": ["metric_a"]})
        anomaly_reader = DataFrameDataReader(anomaly_df)

        with pytest.raises(TypeError, match="history_data must be a DataReader"):
            TimeSeriesVisualizer(
                anomaly_data=anomaly_reader,
                history_data=[1, 2, 3],  # Not a DataReader
            )


class TestGenerateCharts:
    """Tests for generate_charts method."""

    def test_generate_charts_returns_dict(self):
        """Test that generate_charts returns a dictionary."""
        anomaly_df = pd.DataFrame({"group_key": ["metric_a"], "value": [100]})
        history_df = pd.DataFrame(
            {"metric_a": [10, 20, 30]},
            index=pd.date_range("2024-01-01", periods=3),
        )

        anomaly_reader = DataFrameDataReader(anomaly_df)
        history_reader = DataFrameDataReader(history_df)

        visualizer = TimeSeriesVisualizer(
            anomaly_data=anomaly_reader,
            history_data=history_reader,
        )

        charts = visualizer.generate_charts()

        assert isinstance(charts, dict)
        assert "metric_a" in charts

    def test_generate_charts_returns_base64(self):
        """Test that charts are valid base64-encoded images."""
        anomaly_df = pd.DataFrame({"group_key": ["metric_a"], "value": [100]})
        history_df = pd.DataFrame(
            {"metric_a": [10, 20, 30]},
            index=pd.date_range("2024-01-01", periods=3),
        )

        anomaly_reader = DataFrameDataReader(anomaly_df)
        history_reader = DataFrameDataReader(history_df)

        visualizer = TimeSeriesVisualizer(
            anomaly_data=anomaly_reader,
            history_data=history_reader,
        )

        charts = visualizer.generate_charts()

        # Verify base64 can be decoded
        decoded = base64.b64decode(charts["metric_a"])
        # PNG files start with specific bytes
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    def test_generate_charts_missing_group_key_warns(self):
        """Test warning when anomaly_data lacks group_key column."""
        anomaly_df = pd.DataFrame({"metric": ["a"], "value": [100]})
        history_df = pd.DataFrame(
            {"metric_a": [10, 20, 30]},
            index=pd.date_range("2024-01-01", periods=3),
        )

        anomaly_reader = DataFrameDataReader(anomaly_df)
        history_reader = DataFrameDataReader(history_df)

        visualizer = TimeSeriesVisualizer(
            anomaly_data=anomaly_reader,
            history_data=history_reader,
        )

        with pytest.warns(UserWarning, match="group_key"):
            charts = visualizer.generate_charts()

        assert charts == {}

    def test_generate_charts_metric_not_in_history(self):
        """Test that missing metrics in history are skipped."""
        anomaly_df = pd.DataFrame(
            {"group_key": ["metric_a", "metric_b"], "value": [100, 200]}
        )
        history_df = pd.DataFrame(
            {"metric_a": [10, 20, 30]},  # metric_b not present
            index=pd.date_range("2024-01-01", periods=3),
        )

        anomaly_reader = DataFrameDataReader(anomaly_df)
        history_reader = DataFrameDataReader(history_df)

        visualizer = TimeSeriesVisualizer(
            anomaly_data=anomaly_reader,
            history_data=history_reader,
        )

        charts = visualizer.generate_charts()

        assert "metric_a" in charts
        assert "metric_b" not in charts

    def test_generate_charts_skips_all_nan_metrics(self):
        """Test that metrics with all NaN values are skipped."""
        anomaly_df = pd.DataFrame({"group_key": ["metric_a"], "value": [100]})
        history_df = pd.DataFrame(
            {"metric_a": [float("nan"), float("nan"), float("nan")]},
            index=pd.date_range("2024-01-01", periods=3),
        )

        anomaly_reader = DataFrameDataReader(anomaly_df)
        history_reader = DataFrameDataReader(history_df)

        visualizer = TimeSeriesVisualizer(
            anomaly_data=anomaly_reader,
            history_data=history_reader,
        )

        charts = visualizer.generate_charts()

        assert "metric_a" not in charts


class TestSaveCharts:
    """Tests for save_charts method."""

    def test_save_charts_creates_files(self, tmp_path):
        """Test that save_charts creates image files."""
        anomaly_df = pd.DataFrame({"group_key": ["metric_a"], "value": [100]})
        history_df = pd.DataFrame(
            {"metric_a": [10, 20, 30]},
            index=pd.date_range("2024-01-01", periods=3),
        )

        anomaly_reader = DataFrameDataReader(anomaly_df)
        history_reader = DataFrameDataReader(history_df)

        visualizer = TimeSeriesVisualizer(
            anomaly_data=anomaly_reader,
            history_data=history_reader,
        )

        saved_files = visualizer.save_charts(str(tmp_path))

        assert len(saved_files) == 1
        assert (tmp_path / "metric_a.png").exists()

    def test_save_charts_creates_output_directory(self, tmp_path):
        """Test that save_charts creates output directory if not exists."""
        output_dir = tmp_path / "subdir" / "charts"

        anomaly_df = pd.DataFrame({"group_key": ["metric_a"], "value": [100]})
        history_df = pd.DataFrame(
            {"metric_a": [10, 20, 30]},
            index=pd.date_range("2024-01-01", periods=3),
        )

        anomaly_reader = DataFrameDataReader(anomaly_df)
        history_reader = DataFrameDataReader(history_df)

        visualizer = TimeSeriesVisualizer(
            anomaly_data=anomaly_reader,
            history_data=history_reader,
        )

        saved_files = visualizer.save_charts(str(output_dir))

        assert output_dir.exists()
        assert len(saved_files) == 1


class TestGetFigures:
    """Tests for get_figures method."""

    def test_get_figures_returns_figure_objects(self):
        """Test that get_figures returns matplotlib Figure objects."""
        import matplotlib.pyplot as plt

        anomaly_df = pd.DataFrame({"group_key": ["metric_a"], "value": [100]})
        history_df = pd.DataFrame(
            {"metric_a": [10, 20, 30]},
            index=pd.date_range("2024-01-01", periods=3),
        )

        anomaly_reader = DataFrameDataReader(anomaly_df)
        history_reader = DataFrameDataReader(history_df)

        visualizer = TimeSeriesVisualizer(
            anomaly_data=anomaly_reader,
            history_data=history_reader,
        )

        figures = visualizer.get_figures()

        assert isinstance(figures, dict)
        assert "metric_a" in figures

        # Verify it's a matplotlib Figure
        from matplotlib.figure import Figure

        assert isinstance(figures["metric_a"], Figure)

        # Cleanup
        for fig in figures.values():
            plt.close(fig)
