"""
BigQuery data writer implementation.
"""

import os
import pandas as pd
from typing import Optional, Dict, List, Callable
from google.cloud import bigquery
from ..base import DataWriter
from chronomaly.shared import TransformableMixin


class BigQueryDataWriter(DataWriter, TransformableMixin):
    """
    Data writer implementation for Google BigQuery.

    Args:
        service_account_file: Path to the service account JSON file for authentication
        project: GCP project ID
        dataset: BigQuery dataset name
        table: BigQuery table name
        create_disposition: Specifies behavior if table doesn't exist
                           (default: CREATE_IF_NEEDED)
        write_disposition: Specifies behavior if table exists
                          (default: WRITE_TRUNCATE - replaces existing data)
        transformers: Optional dict of transformer lists to apply before/after writing
                     Example: {'before': [Filter1(), Filter2()]}
    """

    # Valid disposition values
    VALID_CREATE_DISPOSITIONS = {'CREATE_IF_NEEDED', 'CREATE_NEVER'}
    VALID_WRITE_DISPOSITIONS = {'WRITE_TRUNCATE', 'WRITE_APPEND', 'WRITE_EMPTY'}

    def __init__(
        self,
        service_account_file: Optional[str] = None,
        project: Optional[str] = None,
        dataset: Optional[str] = None,
        table: Optional[str] = None,
        create_disposition: str = 'CREATE_IF_NEEDED',
        write_disposition: str = 'WRITE_TRUNCATE',
        transformers: Optional[Dict[str, List[Callable]]] = None
    ):
        if dataset is None:
            raise ValueError("dataset parameter is required")
        if table is None:
            raise ValueError("table parameter is required")

        # Validate disposition parameters
        if create_disposition not in self.VALID_CREATE_DISPOSITIONS:
            raise ValueError(
                f"Invalid create_disposition: '{create_disposition}'. "
                f"Must be one of: {', '.join(sorted(self.VALID_CREATE_DISPOSITIONS))}"
            )
        if write_disposition not in self.VALID_WRITE_DISPOSITIONS:
            raise ValueError(
                f"Invalid write_disposition: '{write_disposition}'. "
                f"Must be one of: {', '.join(sorted(self.VALID_WRITE_DISPOSITIONS))}"
            )

        # BUG-005 FIX: Validate service account file path
        if service_account_file:
            if not service_account_file.strip():
                raise ValueError("service_account_file cannot be empty")

            abs_path = os.path.abspath(service_account_file)
            if not os.path.isfile(abs_path):
                raise FileNotFoundError(
                    f"Service account file not found: {abs_path}"
                )

            if not os.access(abs_path, os.R_OK):
                raise PermissionError(
                    f"Service account file is not readable: {abs_path}"
                )

            if not abs_path.endswith('.json'):
                raise ValueError(
                    "Service account file must be a JSON file (.json extension)"
                )

            self.service_account_file: Optional[str] = abs_path
        else:
            self.service_account_file = service_account_file
        self.project = project
        self.dataset: str = dataset  # type: ignore[assignment]
        self.table: str = table  # type: ignore[assignment]
        self.create_disposition = create_disposition
        self.write_disposition = write_disposition
        self._client = None
        self.transformers = transformers or {}

    def _get_client(self) -> bigquery.Client:
        """
        Get or create BigQuery client.

        Returns:
            bigquery.Client: Initialized BigQuery client
        """
        if self._client is None:
            if self.service_account_file:
                self._client = bigquery.Client.from_service_account_json(
                    self.service_account_file,
                    project=self.project
                )
            else:
                self._client = bigquery.Client(project=self.project)
        return self._client

    def write(self, dataframe: pd.DataFrame) -> None:
        """
        Write forecast results to BigQuery table.

        Args:
            dataframe: The forecast results as a pandas DataFrame

        Raises:
            TypeError: If dataframe is not a pandas DataFrame
            ValueError: If dataframe is empty
            RuntimeError: If the BigQuery write job fails
        """
        # Apply transformers before writing data
        dataframe = self._apply_transformers(dataframe, 'before')

        # BUG-004 FIX: Validate dataframe type and emptiness
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame, got {type(dataframe).__name__}"
            )

        if dataframe.empty:
            raise ValueError("Cannot write empty DataFrame to BigQuery")

        client = self._get_client()

        # BUG-007 FIX: Construct table ID with proper project handling
        if self.project:
            table_id = f"{self.project}.{self.dataset}.{self.table}"
        elif client.project:
            table_id = f"{client.project}.{self.dataset}.{self.table}"
        else:
            raise ValueError(
                "project must be specified either in constructor or in BigQuery client"
            )

        # Configure load job
        bigquery_job_config = bigquery.LoadJobConfig()

        # Set create disposition
        if self.create_disposition == 'CREATE_IF_NEEDED':
            bigquery_job_config.create_disposition = bigquery.CreateDisposition.CREATE_IF_NEEDED
        elif self.create_disposition == 'CREATE_NEVER':
            bigquery_job_config.create_disposition = bigquery.CreateDisposition.CREATE_NEVER

        # Set write disposition
        if self.write_disposition == 'WRITE_TRUNCATE':
            bigquery_job_config.write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE
        elif self.write_disposition == 'WRITE_APPEND':
            bigquery_job_config.write_disposition = bigquery.WriteDisposition.WRITE_APPEND
        elif self.write_disposition == 'WRITE_EMPTY':
            bigquery_job_config.write_disposition = bigquery.WriteDisposition.WRITE_EMPTY

        # Load dataframe to BigQuery using table_id string
        job = client.load_table_from_dataframe(
            dataframe,
            table_id,
            job_config=bigquery_job_config
        )

        # Wait for the job to complete with proper error handling
        try:
            job.result()
        except Exception as e:
            raise RuntimeError(
                f"Failed to write to BigQuery table {self.dataset}.{self.table}. "
                f"Error: {str(e)}"
            ) from e

    def close(self) -> None:
        """
        BUG-006 FIX: Close BigQuery client and release resources.

        This method should be called when the writer is no longer needed,
        or use the writer as a context manager for automatic cleanup.
        """
        if self._client is not None:
            try:
                self._client.close()
            finally:
                self._client = None

    def __enter__(self):
        """Support for context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure client is closed when used as context manager."""
        self.close()
        return False
