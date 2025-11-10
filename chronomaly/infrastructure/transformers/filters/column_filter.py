"""
Column filter - DEPRECATED: Use ValueFilter instead.

This module is kept for backward compatibility.
ColumnFilter is now an alias to ValueFilter with numeric filtering.
"""

import warnings
from .value_filter import ValueFilter


class ColumnFilter(ValueFilter):
    """
    DEPRECATED: Use ValueFilter instead.

    Filter DataFrame rows based on numeric column thresholds.

    This class is now an alias to ValueFilter for backward compatibility.
    New code should use ValueFilter directly:

        # Old way (still works):
        filter = ColumnFilter('deviation_pct', min_value=10.0)

        # New way (recommended):
        filter = ValueFilter('deviation_pct', min_value=10.0)

    Args:
        column: Column name to filter on
        min_value: Minimum value (inclusive), None for no minimum
        max_value: Maximum value (inclusive), None for no maximum

    Example - Minimum sapma:
        filter = ColumnFilter('deviation_pct', min_value=10.0)
        significant = filter.filter(anomaly_df)

    Example - Değer aralığı:
        filter = ColumnFilter('sessions', min_value=100, max_value=10000)
        filtered = filter.filter(data_df)

    Example - Maksimum filtre:
        filter = ColumnFilter('error_rate', max_value=0.05)
        acceptable = filter.filter(metrics_df)
    """

    def __init__(
        self,
        column: str,
        min_value: float = None,
        max_value: float = None
    ):
        warnings.warn(
            "ColumnFilter is deprecated. Use ValueFilter instead: "
            "ValueFilter('column', min_value=X, max_value=Y)",
            DeprecationWarning,
            stacklevel=2
        )

        # Call parent ValueFilter with numeric parameters
        super().__init__(
            column=column,
            min_value=min_value,
            max_value=max_value
        )
