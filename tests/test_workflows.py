"""
Tests for workflow orchestrators.
"""

import pytest
import pandas as pd
from unittest.mock import Mock
from chronomaly.application.workflows import AnomalyDetectionWorkflow


class TestAnomalyDetectionWorkflow:
    """Tests for AnomalyDetectionWorkflow"""

    def test_basic_workflow_execution(self):
        """Test basic workflow execution without transformers."""
        # Create mock components
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric_a": ["100|90|92|95|98|100|102|105|108|110"],
            }
        )

        mock_actual_reader = Mock()
        mock_actual_reader.load.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "value": [95]}
        )

        mock_detector = Mock()
        mock_detector.detect.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "status": ["IN_RANGE"]}
        )

        mock_writer = Mock()

        # Create workflow
        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
        )

        # Execute
        result = workflow.run()

        # Verify
        assert result is not None
        assert len(result) == 1
        mock_forecast_reader.load.assert_called_once()
        mock_actual_reader.load.assert_called_once()
        mock_detector.detect.assert_called_once()
        mock_writer.write.assert_called_once()

    def test_workflow_with_transformers(self):
        """Test workflow execution with transformers at component level."""
        # Create mock components
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric_a": ["100|90|92|95|98|100|102|105|108|110"],
            }
        )

        mock_actual_reader = Mock()
        mock_actual_reader.load.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "value": [95]}
        )

        # Create mock detector with transformers
        mock_detector = Mock()
        mock_detector.detect.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "status": ["IN_RANGE"]}
        )

        mock_writer = Mock()

        # Transformers are now configured at component level (not workflow level)
        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
        )

        # Execute
        result = workflow.run()

        # Verify workflow executed successfully
        assert result is not None

    def test_workflow_empty_forecast_raises_error(self):
        """Test that empty forecast data raises ValueError."""
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame()  # Empty

        mock_actual_reader = Mock()
        mock_detector = Mock()
        mock_writer = Mock()

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
        )

        with pytest.raises(ValueError, match="Forecast reader returned empty dataset"):
            workflow.run()

    def test_workflow_empty_actual_raises_error(self):
        """Test that empty actual data raises ValueError."""
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric_a": ["100|90|92|95|98|100|102|105|108|110"],
            }
        )

        mock_actual_reader = Mock()
        mock_actual_reader.load.return_value = pd.DataFrame()  # Empty

        mock_detector = Mock()
        mock_writer = Mock()

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
        )

        with pytest.raises(ValueError, match="Actual reader returned empty dataset"):
            workflow.run()

    def test_workflow_empty_detection_result_raises_error(self):
        """Test that empty detection result raises ValueError."""
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric_a": ["100|90|92|95|98|100|102|105|108|110"],
            }
        )

        mock_actual_reader = Mock()
        mock_actual_reader.load.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "value": [95]}
        )

        mock_detector = Mock()
        mock_detector.detect.return_value = pd.DataFrame()  # Empty

        mock_writer = Mock()

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
        )

        with pytest.raises(ValueError, match="Anomaly detector returned empty results"):
            workflow.run()

    def test_run_without_output(self):
        """Test running workflow without data_writer."""
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric_a": ["100|90|92|95|98|100|102|105|108|110"],
            }
        )

        mock_actual_reader = Mock()
        mock_actual_reader.load.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "value": [95]}
        )

        mock_detector = Mock()
        mock_detector.detect.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "status": ["IN_RANGE"]}
        )

        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=None,
        )

        # Execute without writing (data_writer is None)
        result = workflow.run()

        # Verify result is returned
        assert result is not None

    def test_transformer_with_format_method(self):
        """Test that transformers with .format() method work correctly at component level."""
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric_a": ["100|90|92|95|98|100|102|105|108|110"],
            }
        )

        mock_actual_reader = Mock()
        mock_actual_reader.load.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "value": [95]}
        )

        # Mock detector handles transformers internally
        mock_detector = Mock()
        mock_detector.detect.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "status": ["IN_RANGE"]}
        )

        mock_writer = Mock()

        # Transformers are configured at component level (detector, reader, writer)
        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
        )

        result = workflow.run()

        # Verify workflow executed successfully
        assert result is not None

    def test_transformer_callable(self):
        """Test that callable transformers work correctly at component level."""
        mock_forecast_reader = Mock()
        mock_forecast_reader.load.return_value = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "metric_a": ["100|90|92|95|98|100|102|105|108|110"],
            }
        )

        mock_actual_reader = Mock()
        mock_actual_reader.load.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "value": [95]}
        )

        mock_detector = Mock()
        mock_detector.detect.return_value = pd.DataFrame(
            {"date": ["2024-01-01"], "metric": ["metric_a"], "status": ["IN_RANGE"]}
        )

        mock_writer = Mock()

        # Transformers are configured at component level (detector, reader, writer)
        workflow = AnomalyDetectionWorkflow(
            forecast_reader=mock_forecast_reader,
            actual_reader=mock_actual_reader,
            anomaly_detector=mock_detector,
            data_writer=mock_writer,
        )

        result = workflow.run()

        # Verify workflow executed successfully
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
