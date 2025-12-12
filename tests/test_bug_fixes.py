"""
Tests for bug fixes #7-#12.
These tests verify that all newly discovered bugs have been properly fixed.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter


class TestBug008BigQueryDispositionValidation:
    """Tests for BUG-008: BigQuery writer silently ignores invalid dispositions"""

    def test_invalid_create_disposition_raises_error(self):
        """
        BUG-008: Test that invalid create_disposition raises ValueError.
        """
        with pytest.raises(ValueError, match="Invalid create_disposition"):
            BigQueryDataWriter(
                dataset="test_dataset",
                table="test_table",
                create_disposition="INVALID_VALUE",
            )

    def test_invalid_write_disposition_raises_error(self):
        """
        BUG-008: Test that invalid write_disposition raises ValueError.
        """
        with pytest.raises(ValueError, match="Invalid write_disposition"):
            BigQueryDataWriter(
                dataset="test_dataset",
                table="test_table",
                write_disposition="INVALID_VALUE",
            )

    def test_valid_dispositions_accepted(self):
        """
        BUG-008: Test that valid dispositions are accepted without error.
        """
        # Should not raise any errors
        writer = BigQueryDataWriter(
            dataset="test_dataset",
            table="test_table",
            create_disposition="CREATE_IF_NEEDED",
            write_disposition="WRITE_TRUNCATE",
        )
        assert writer.create_disposition == "CREATE_IF_NEEDED"
        assert writer.write_disposition == "WRITE_TRUNCATE"


class TestBug009BigQueryErrorHandling:
    """Tests for BUG-009: BigQuery writer has no error handling for job failures"""

    @patch("chronomaly.infrastructure.data.writers.databases.bigquery.bigquery.Client")
    def test_job_failure_raises_runtime_error_with_context(self, mock_client_class):
        """
        BUG-009: Test that job failures raise RuntimeError with helpful context.
        """
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Make job.result() raise an exception
        mock_job = MagicMock()
        mock_job.result.side_effect = Exception("Permission denied")
        mock_client.load_table_from_dataframe.return_value = mock_job

        writer = BigQueryDataWriter(dataset="test_dataset", table="test_table")

        # Create test dataframe
        df = pd.DataFrame({"a": [1, 2, 3]})

        # Should raise RuntimeError with context
        with pytest.raises(RuntimeError, match="Failed to write to BigQuery table"):
            writer.write(df)

        # Verify the error message includes table information
        with pytest.raises(RuntimeError, match="test_dataset.test_table"):
            writer.write(df)


class TestBug010WorkflowTypeErrorHandling:
    """Tests for BUG-010: Workflow overly broad exception handling"""

    def test_forecaster_without_return_point_parameter(self):
        """
        BUG-010: Test that forecasters without return_point parameter work correctly.
        Uses inspect instead of try/except TypeError.
        """
        # Create mock components
        mock_reader = Mock()
        mock_reader.load.return_value = pd.DataFrame(
            {"a": [1, 2, 3]}, index=pd.date_range("2024-01-01", periods=3)
        )

        # Forecaster WITHOUT return_point parameter
        mock_forecaster = Mock()
        mock_forecaster.forecast = Mock(
            return_value=pd.DataFrame(
                {"a": [4, 5]}, index=pd.date_range("2024-01-04", periods=2)
            )
        )

        # Remove return_point from signature by using a function
        def forecast_no_return_point(dataframe, horizon):
            return pd.DataFrame({"a": [4, 5]})

        mock_forecaster.forecast = forecast_no_return_point

        mock_writer = Mock()

        # Create workflow
        workflow = ForecastWorkflow(
            data_reader=mock_reader, forecaster=mock_forecaster, data_writer=mock_writer
        )

        # Should work without error (inspect detects missing parameter)
        result = workflow.run(horizon=2, return_point=True)
        assert result is not None

    def test_forecaster_with_return_point_parameter(self):
        """
        BUG-010: Test that forecasters WITH return_point parameter work correctly.
        """
        # Create mock components
        mock_reader = Mock()
        mock_reader.load.return_value = pd.DataFrame(
            {"a": [1, 2, 3]}, index=pd.date_range("2024-01-01", periods=3)
        )

        # Forecaster WITH return_point parameter
        mock_forecaster = Mock()

        def forecast_with_return_point(dataframe, horizon, return_point=False):
            return pd.DataFrame({"a": [4, 5]})

        mock_forecaster.forecast = forecast_with_return_point

        mock_writer = Mock()

        # Create workflow
        workflow = ForecastWorkflow(
            data_reader=mock_reader, forecaster=mock_forecaster, data_writer=mock_writer
        )

        # Should pass return_point parameter
        result = workflow.run(horizon=2, return_point=True)
        assert result is not None


class TestBug011WorkflowHorizonValidation:
    """Tests for BUG-011: Workflow doesn't validate horizon parameter"""

    def test_negative_horizon_raises_error(self):
        """
        BUG-011: Test that negative horizon raises ValueError.
        """
        mock_reader = Mock()
        mock_forecaster = Mock()
        mock_writer = Mock()

        workflow = ForecastWorkflow(
            data_reader=mock_reader, forecaster=mock_forecaster, data_writer=mock_writer
        )

        with pytest.raises(ValueError, match="horizon must be a positive integer"):
            workflow.run(horizon=-5)

    def test_zero_horizon_raises_error(self):
        """
        BUG-011: Test that zero horizon raises ValueError.
        """
        mock_reader = Mock()
        mock_forecaster = Mock()
        mock_writer = Mock()

        workflow = ForecastWorkflow(
            data_reader=mock_reader, forecaster=mock_forecaster, data_writer=mock_writer
        )

        with pytest.raises(ValueError, match="horizon must be a positive integer"):
            workflow.run(horizon=0)

    def test_non_integer_horizon_raises_error(self):
        """
        BUG-011: Test that non-integer horizon raises ValueError.
        """
        mock_reader = Mock()
        mock_forecaster = Mock()
        mock_writer = Mock()

        workflow = ForecastWorkflow(
            data_reader=mock_reader, forecaster=mock_forecaster, data_writer=mock_writer
        )

        with pytest.raises(ValueError, match="horizon must be a positive integer"):
            workflow.run(horizon=5.5)

        with pytest.raises(ValueError, match="horizon must be a positive integer"):
            workflow.run(horizon="10")


class TestBug012WorkflowDataValidation:
    """Tests for BUG-012: Workflow doesn't validate loaded data"""

    def test_empty_dataframe_raises_error(self):
        """
        BUG-012: Test that empty DataFrame raises ValueError.
        """
        mock_reader = Mock()
        mock_reader.load.return_value = pd.DataFrame()  # Empty DataFrame

        mock_forecaster = Mock()
        mock_writer = Mock()

        workflow = ForecastWorkflow(
            data_reader=mock_reader, forecaster=mock_forecaster, data_writer=mock_writer
        )

        with pytest.raises(ValueError, match="Data reader returned empty dataset"):
            workflow.run(horizon=10)

    def test_none_dataframe_raises_error(self):
        """
        BUG-012: Test that None DataFrame raises ValueError.
        """
        mock_reader = Mock()
        mock_reader.load.return_value = None  # None instead of DataFrame

        mock_forecaster = Mock()
        mock_writer = Mock()

        workflow = ForecastWorkflow(
            data_reader=mock_reader, forecaster=mock_forecaster, data_writer=mock_writer
        )

        with pytest.raises(ValueError, match="Data reader returned empty dataset"):
            workflow.run(horizon=10)

    def test_empty_after_transform_raises_error(self):
        """
        BUG-012: Test that empty DataFrame from reader raises ValueError.
        Note: Transformers are now configured at component level, not workflow level.
        """
        # Reader returns empty DataFrame (simulating empty result after transformation)
        mock_reader = Mock()
        mock_reader.load.return_value = pd.DataFrame()  # Empty after transform

        mock_forecaster = Mock()
        mock_writer = Mock()

        workflow = ForecastWorkflow(
            data_reader=mock_reader, forecaster=mock_forecaster, data_writer=mock_writer
        )

        with pytest.raises(ValueError, match="Data reader returned empty dataset"):
            workflow.run(horizon=10)


class TestBug007BigQueryDeprecatedAPI:
    """Tests for BUG-007: BigQuery writer uses deprecated API"""

    @patch("chronomaly.infrastructure.data.writers.databases.bigquery.bigquery.Client")
    def test_uses_table_id_string_not_deprecated_methods(self, mock_client_class):
        """
        BUG-007: Test that modern table_id string is used instead of deprecated dataset().table().
        """
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_job = MagicMock()
        mock_client.load_table_from_dataframe.return_value = mock_job

        writer = BigQueryDataWriter(
            project="test_project", dataset="test_dataset", table="test_table"
        )

        df = pd.DataFrame({"a": [1, 2, 3]})
        writer.write(df)

        # Verify load_table_from_dataframe was called with string table_id
        # not with deprecated table reference object
        call_args = mock_client.load_table_from_dataframe.call_args
        table_ref_arg = call_args[0][1]  # Second positional argument

        # Should be a string, not a TableReference object
        assert isinstance(table_ref_arg, str)
        assert table_ref_arg == "test_project.test_dataset.test_table"

    @patch("chronomaly.infrastructure.data.writers.databases.bigquery.bigquery.Client")
    def test_table_id_without_project(self, mock_client_class):
        """
        BUG-007: Test table_id construction when project is not specified.
        """
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_job = MagicMock()
        mock_client.load_table_from_dataframe.return_value = mock_job

        writer = BigQueryDataWriter(dataset="test_dataset", table="test_table")

        df = pd.DataFrame({"a": [1, 2, 3]})
        writer.write(df)

        # Verify table_id format without project
        call_args = mock_client.load_table_from_dataframe.call_args
        table_ref_arg = call_args[0][1]

        assert isinstance(table_ref_arg, str)
        assert table_ref_arg == "test_dataset.test_table"
