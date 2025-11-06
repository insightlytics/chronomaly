"""
Tests for data source implementations.
Tests for bugs #1, #5, #6, #7.
"""

import pytest
import pandas as pd
import sqlite3
import os
import tempfile
from forecast_library.data_sources import CSVDataSource, SQLiteDataSource


class TestCSVDataSource:
    """Tests for CSVDataSource"""

    def test_csv_with_valid_date_column(self, tmp_path):
        """Test CSV loading with valid date column"""
        # Create test CSV
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'value': [1, 2, 3]
        })
        df.to_csv(csv_file, index=False)

        # Load with date_column
        source = CSVDataSource(file_path=str(csv_file), date_column='date')
        result = source.load()

        # Verify date column is parsed as datetime
        assert pd.api.types.is_datetime64_any_dtype(result['date'])

    def test_csv_with_missing_date_column_should_raise_error(self, tmp_path):
        """
        Bug #5: Test that CSVDataSource raises error when date_column doesn't exist.
        Currently this test will FAIL because the bug exists.
        """
        # Create test CSV with 'timestamp' column, not 'date'
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'value': [1, 2, 3]
        })
        df.to_csv(csv_file, index=False)

        # Try to load with date_column='date' (which doesn't exist)
        source = CSVDataSource(file_path=str(csv_file), date_column='date')

        # This should raise ValueError but currently doesn't (BUG #5)
        with pytest.raises(ValueError, match="date_column 'date' not found"):
            source.load()


class TestSQLiteDataSource:
    """Tests for SQLiteDataSource"""

    def test_sqlite_with_valid_query(self, tmp_path):
        """Test SQLite loading with valid query"""
        # Create test database
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        df = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'value': [1, 2, 3]
        })
        df.to_sql('test_table', conn, index=False)
        conn.close()

        # Load with valid query
        source = SQLiteDataSource(
            database_path=str(db_file),
            query="SELECT * FROM test_table",
            date_column='date'
        )
        result = source.load()

        assert len(result) == 3
        assert pd.api.types.is_datetime64_any_dtype(result['date'])

    def test_sqlite_with_invalid_query_should_show_proper_error(self, tmp_path):
        """
        Bug #1: Test that SQLite error is properly propagated.
        Currently this test will FAIL because UnboundLocalError is raised.
        """
        # Create test database
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        conn.close()

        # Try to load with invalid query
        source = SQLiteDataSource(
            database_path=str(db_file),
            query="SELECT * FROM nonexistent_table"
        )

        # Should raise sqlite3.OperationalError, not UnboundLocalError (BUG #1)
        with pytest.raises(Exception) as exc_info:
            source.load()

        # The error should be about the table, not UnboundLocalError
        assert "UnboundLocalError" not in str(type(exc_info.value))

    def test_sqlite_with_missing_date_column_should_raise_error(self, tmp_path):
        """
        Bug #6: Test that SQLiteDataSource raises error when date_column doesn't exist.
        Currently this test will FAIL because the bug exists.
        """
        # Create test database with 'timestamp' column, not 'date'
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        df = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'value': [1, 2, 3]
        })
        df.to_sql('test_table', conn, index=False)
        conn.close()

        # Try to load with date_column='date' (which doesn't exist)
        source = SQLiteDataSource(
            database_path=str(db_file),
            query="SELECT * FROM test_table",
            date_column='date'
        )

        # This should raise ValueError but currently doesn't (BUG #6)
        with pytest.raises(ValueError, match="date_column 'date' not found"):
            source.load()
