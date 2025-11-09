"""
Base abstract class for data writers.
"""

from abc import ABC, abstractmethod
import pandas as pd


class DataWriter(ABC):
    """
    Abstract base class for all data writer implementations.

    All data writer implementations must inherit from this class
    and implement the write() method.
    """

    @abstractmethod
    def write(self, dataframe: pd.DataFrame) -> None:
        """
        Write forecast results to the output destination.

        Args:
            dataframe: The forecast results as a pandas DataFrame
        """
        pass
