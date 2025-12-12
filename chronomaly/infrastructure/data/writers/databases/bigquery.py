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
    """

    # Valid disposition values
    VALID_CREATE_DISPOSITIONS = {"CREATE_IF_NEEDED", "CREATE_NEVER"}
    VALID_WRITE_DISPOSITIONS = {"WRITE_TRUNCATE", "WRITE_APPEND", "WRITE_EMPTY"}

    def __init__(
        self,
        service_account_file: Optional[str] = None,
        project: Optional[str] = None,
        dataset: str = None,
        table: str = None,
        create_disposition: str = "CREATE_IF_NEEDED",
        write_disposition: str = "WRITE_TRUNCATE",
        transformers: Optional[Dict[str, List[Callable]]] = None,
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

        # PY-007 FIX: Validate service account file path
        if service_account_file:
            if not service_account_file.strip():
                raise ValueError("service_account_file cannot be empty")

            # Resolve to absolute path and check if it exists
            abs_path = os.path.abspath(service_account_file)
            if not os.path.isfile(abs_path):
                raise FileNotFoundError(f"Service account file not found: {abs_path}")

            # Check file is readable
            if not os.access(abs_path, os.R_OK):
                raise PermissionError(
                    f"Service account file is not readable: {abs_path}"
                )

            # Basic validation that it's a JSON file
            if not abs_path.endswith(".json"):
                raise ValueError(
                    "Service account file must be a JSON file (.json extension)"
                )

            service_account_file = abs_path

        self.service_account_file = service_account_file
        self.project = project
        self.dataset = dataset
        self.table = table
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
                    self.service_account_file, project=self.project
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
            RuntimeError: If the BigQuery write job fails
        """
        # Apply transformers before writing data
        dataframe = self._apply_transformers(dataframe, "before")

        client = self._get_client()

        # Construct table ID (modern API - replaces deprecated dataset().table())
        if self.project:
            table_id = f"{self.project}.{self.dataset}.{self.table}"
        else:
            table_id = f"{self.dataset}.{self.table}"

        # Configure load job
        bigquery_job_config = bigquery.LoadJobConfig()

        # Set create disposition
        if self.create_disposition == "CREATE_IF_NEEDED":
            bigquery_job_config.create_disposition = (
                bigquery.CreateDisposition.CREATE_IF_NEEDED
            )
        elif self.create_disposition == "CREATE_NEVER":
            bigquery_job_config.create_disposition = (
                bigquery.CreateDisposition.CREATE_NEVER
            )

        # Set write disposition
        if self.write_disposition == "WRITE_TRUNCATE":
            bigquery_job_config.write_disposition = (
                bigquery.WriteDisposition.WRITE_TRUNCATE
            )
        elif self.write_disposition == "WRITE_APPEND":
            bigquery_job_config.write_disposition = (
                bigquery.WriteDisposition.WRITE_APPEND
            )
        elif self.write_disposition == "WRITE_EMPTY":
            bigquery_job_config.write_disposition = (
                bigquery.WriteDisposition.WRITE_EMPTY
            )

        # Load dataframe to BigQuery using table_id string
        job = client.load_table_from_dataframe(
            dataframe, table_id, job_config=bigquery_job_config
        )

        # Wait for the job to complete with proper error handling
        try:
            job.result()
        except Exception as e:
            raise RuntimeError(
                f"Failed to write to BigQuery table {self.dataset}.{self.table}. "
                f"Error: {str(e)}"
            ) from e
