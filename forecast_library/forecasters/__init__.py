"""
Forecaster implementations for time series prediction.
"""

from .base import Forecaster

# TimesFM requires torch which is an optional dependency
try:
    from .timesfm import TimesFMForecaster
    __all__ = [
        "Forecaster",
        "TimesFMForecaster",
    ]
except ImportError:
    __all__ = [
        "Forecaster",
    ]
