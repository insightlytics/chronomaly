"""
Tests for forecaster implementations.
Tests for bug #2.
"""

import pytest
import pandas as pd
import numpy as np


class TestTimesFMForecaster:
    """Tests for TimesFMForecaster"""

    def test_get_last_date_with_multiindex(self):
        """
        Bug #2: Test that _get_last_date doesn't have redundant datetime conversion.
        This is more of a code quality issue - we can verify by checking the code.
        """
        # Import here to avoid timesfm dependency if not installed
        try:
            from chronomaly.infrastructure.forecasters import TimesFMForecaster
        except ImportError:
            pytest.skip("timesfm not installed")

        forecaster = TimesFMForecaster()

        # Create MultiIndex dataframe with datetime in first level
        dates = pd.date_range("2024-01-01", periods=3)
        stores = ["store1", "store2"]
        index = pd.MultiIndex.from_product([dates, stores], names=["date", "store"])
        df = pd.DataFrame(
            {"product_a": np.random.randn(6), "product_b": np.random.randn(6)},
            index=index,
        )

        # This should work without redundant conversion
        last_date = forecaster._get_last_date(df)

        assert isinstance(last_date, pd.Timestamp)

    def test_get_last_date_with_datetime_index(self):
        """Test _get_last_date with regular DatetimeIndex"""
        try:
            from chronomaly.infrastructure.forecasters import TimesFMForecaster
        except ImportError:
            pytest.skip("timesfm not installed")

        forecaster = TimesFMForecaster()

        df = pd.DataFrame(
            {"product_a": [1, 2, 3], "product_b": [4, 5, 6]},
            index=pd.date_range("2024-01-01", periods=3),
        )

        last_date = forecaster._get_last_date(df)

        assert isinstance(last_date, pd.Timestamp)
        assert last_date == pd.Timestamp("2024-01-03")

    def test_get_last_date_with_invalid_index_raises_error(self):
        """Test that _get_last_date raises proper error for non-datetime index"""
        try:
            from chronomaly.infrastructure.forecasters import TimesFMForecaster
        except ImportError:
            pytest.skip("timesfm not installed")

        forecaster = TimesFMForecaster()

        df = pd.DataFrame(
            {"product_a": [1, 2, 3], "product_b": [4, 5, 6]}, index=["a", "b", "c"]
        )

        with pytest.raises(ValueError, match="Could not parse index value"):
            forecaster._get_last_date(df)
