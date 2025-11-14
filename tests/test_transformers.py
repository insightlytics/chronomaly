"""
Tests for pivot transformer.
Tests for bugs #3, #4.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from chronomaly.infrastructure.transformers import PivotTransformer
from chronomaly.infrastructure.transformers.filters import DateRangeFilter


class TestPivotTransformer:
    """Tests for PivotTransformer"""

    def test_basic_pivot(self):
        """Test basic pivot functionality"""
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=3),
            'product': ['A', 'B', 'A'],
            'sales': [100, 200, 150]
        })

        transformer = PivotTransformer(
            index='date',
            columns='product',
            values='sales'
        )
        result = transformer.pivot_table(df)

        # Columns are lowercased by transformer
        assert 'a' in result.columns
        assert 'b' in result.columns
        assert len(result) == 3

    def test_pivot_with_object_column_containing_non_strings(self):
        """
        Bug #3: Test that transformer handles object columns with non-string data.
        Currently this test will FAIL with AttributeError.
        """
        # Create dataframe with object column containing datetime objects
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=3),
            'product': ['A', 'B', 'A'],
            'sales': [100, 200, 150],
            'metadata': [pd.Timestamp('2024-01-01'), None, pd.Timestamp('2024-01-02')]
        })

        transformer = PivotTransformer(
            index='date',
            columns='product',
            values='sales'
        )

        # Should not crash on object columns with non-string data (BUG #3)
        try:
            result = transformer.pivot_table(df)
            # If it doesn't crash, test passes
            assert True
        except AttributeError as e:
            # This is the bug - it tries to call .str methods on non-strings
            pytest.fail(f"Bug #3: AttributeError when handling object column: {e}")

    def test_pivot_with_datetime_index_not_named_date(self):
        """
        Bug #4: Test that frequency is set for datetime index regardless of name.
        Currently this test will FAIL because frequency is only set for 'date' column.
        """
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'product': ['A', 'B', 'A', 'B', 'A'],
            'sales': [100, 200, 150, 300, 250]
        })

        transformer = PivotTransformer(
            index='timestamp',
            columns='product',
            values='sales'
        )
        result = transformer.pivot_table(df)

        # The result index should have frequency set (BUG #4)
        # Currently fails because code checks for column name == 'date'
        assert result.index.freq is not None, "Bug #4: Frequency not set for datetime index named 'timestamp'"

    def test_pivot_with_string_columns_cleaning(self):
        """Test that string columns are properly cleaned"""
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=3),
            'product': ['Product A', 'Product B', 'Product A'],
            'sales': [100, 200, 150]
        })

        transformer = PivotTransformer(
            index='date',
            columns='product',
            values='sales'
        )
        result = transformer.pivot_table(df)

        # Verify that column names are cleaned (lowercase, no spaces)
        assert 'producta' in result.columns
        assert 'productb' in result.columns


class TestDateRangeFilter:
    """Tests for DateRangeFilter"""

    def test_filter_by_index_with_both_dates(self):
        """Test filtering by DataFrame index with start and end dates"""
        # Create test DataFrame with datetime index
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'value': range(10)
        }, index=dates)

        # Filter to middle 5 days (Jan 3-7)
        filter = DateRangeFilter(
            start_date='2024-01-03',
            end_date='2024-01-07'
        )
        result = filter.filter(df)

        # Verify we got exactly 5 rows
        assert len(result) == 5
        assert result.index[0] == pd.Timestamp('2024-01-03')
        assert result.index[-1] == pd.Timestamp('2024-01-07')

    def test_filter_by_column_with_both_dates(self):
        """Test filtering by specific date column"""
        # Create test DataFrame with date column
        df = pd.DataFrame({
            'transaction_date': pd.date_range('2024-01-01', periods=10, freq='D'),
            'amount': [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        })

        # Filter to middle 5 days
        filter = DateRangeFilter(
            start_date='2024-01-04',
            end_date='2024-01-08',
            date_column='transaction_date'
        )
        result = filter.filter(df)

        # Verify we got exactly 5 rows
        assert len(result) == 5
        assert result['amount'].tolist() == [400, 500, 600, 700, 800]

    def test_filter_with_only_start_date(self):
        """Test filtering with only start date (no upper bound)"""
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        df = pd.DataFrame({'value': range(10)}, index=dates)

        # Filter from Jan 6 onwards
        filter = DateRangeFilter(start_date='2024-01-06')
        result = filter.filter(df)

        # Should get last 5 days
        assert len(result) == 5
        assert result.index[0] == pd.Timestamp('2024-01-06')
        assert result.index[-1] == pd.Timestamp('2024-01-10')

    def test_filter_with_only_end_date(self):
        """Test filtering with only end date (no lower bound)"""
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        df = pd.DataFrame({'value': range(10)}, index=dates)

        # Filter up to Jan 5
        filter = DateRangeFilter(end_date='2024-01-05')
        result = filter.filter(df)

        # Should get first 5 days
        assert len(result) == 5
        assert result.index[0] == pd.Timestamp('2024-01-01')
        assert result.index[-1] == pd.Timestamp('2024-01-05')

    def test_filter_with_datetime_objects(self):
        """Test filtering using datetime objects instead of strings"""
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        df = pd.DataFrame({'value': range(10)}, index=dates)

        # Use datetime objects
        filter = DateRangeFilter(
            start_date=datetime(2024, 1, 3),
            end_date=datetime(2024, 1, 7)
        )
        result = filter.filter(df)

        assert len(result) == 5
        assert result.index[0] == pd.Timestamp('2024-01-03')
        assert result.index[-1] == pd.Timestamp('2024-01-07')

    def test_filter_with_empty_dataframe(self):
        """Test that empty DataFrame returns empty result"""
        df = pd.DataFrame()
        filter = DateRangeFilter(start_date='2024-01-01', end_date='2024-12-31')
        result = filter.filter(df)

        assert result.empty

    def test_filter_with_no_matching_dates(self):
        """Test filtering with date range that has no matches"""
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        df = pd.DataFrame({'value': range(10)}, index=dates)

        # Filter for dates in February (no matches)
        filter = DateRangeFilter(
            start_date='2024-02-01',
            end_date='2024-02-28'
        )
        result = filter.filter(df)

        assert len(result) == 0

    def test_filter_raises_error_with_no_dates(self):
        """Test that filter raises error when no dates are specified"""
        with pytest.raises(ValueError, match="At least one of 'start_date' or 'end_date' must be specified"):
            DateRangeFilter()

    def test_filter_raises_error_with_invalid_date_order(self):
        """Test that filter raises error when start_date > end_date"""
        with pytest.raises(ValueError, match="start_date .* must be before or equal to end_date"):
            DateRangeFilter(
                start_date='2024-12-31',
                end_date='2024-01-01'
            )

    def test_filter_raises_error_with_missing_column(self):
        """Test that filter raises error when specified column doesn't exist"""
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10, freq='D'),
            'value': range(10)
        })

        filter = DateRangeFilter(
            start_date='2024-01-01',
            end_date='2024-01-10',
            date_column='nonexistent_column'
        )

        with pytest.raises(ValueError, match="Column 'nonexistent_column' not found"):
            filter.filter(df)

    def test_filter_raises_error_with_non_datetime_index(self):
        """Test that filter raises error when index is not datetime and can't be converted"""
        df = pd.DataFrame({
            'value': range(10)
        }, index=['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j'])

        filter = DateRangeFilter(
            start_date='2024-01-01',
            end_date='2024-01-10'
        )

        with pytest.raises(ValueError, match="DataFrame index cannot be converted to datetime"):
            filter.filter(df)

    def test_filter_converts_string_index_to_datetime(self):
        """Test that filter can convert string index to datetime"""
        df = pd.DataFrame({
            'value': range(5)
        }, index=['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'])

        filter = DateRangeFilter(
            start_date='2024-01-02',
            end_date='2024-01-04'
        )
        result = filter.filter(df)

        assert len(result) == 3
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_filter_inclusive_boundaries(self):
        """Test that both start_date and end_date are inclusive"""
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        df = pd.DataFrame({'value': range(10)}, index=dates)

        filter = DateRangeFilter(
            start_date='2024-01-05',
            end_date='2024-01-05'  # Same date
        )
        result = filter.filter(df)

        # Should get exactly 1 row (inclusive on both sides)
        assert len(result) == 1
        assert result.index[0] == pd.Timestamp('2024-01-05')

    def test_filter_with_timestamps(self):
        """Test filtering using pandas Timestamp objects"""
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        df = pd.DataFrame({'value': range(10)}, index=dates)

        filter = DateRangeFilter(
            start_date=pd.Timestamp('2024-01-03'),
            end_date=pd.Timestamp('2024-01-07')
        )
        result = filter.filter(df)

        assert len(result) == 5
        assert result.index[0] == pd.Timestamp('2024-01-03')
        assert result.index[-1] == pd.Timestamp('2024-01-07')
