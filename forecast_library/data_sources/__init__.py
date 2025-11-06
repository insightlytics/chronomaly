"""
Data source implementations for loading time series data.
"""

from .base import DataSource
from .csv_source import CSVDataSource
from .sqlite_source import SQLiteDataSource

# BigQuery is an optional dependency
try:
    from .bigquery_source import BigQueryDataSource
    __all__ = [
        "DataSource",
        "CSVDataSource",
        "SQLiteDataSource",
        "BigQueryDataSource",
    ]
except ImportError:
    __all__ = [
        "DataSource",
        "CSVDataSource",
        "SQLiteDataSource",
    ]
