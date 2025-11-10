"""
Base abstract class for post-filters and transformers.
"""

from abc import ABC, abstractmethod
import pandas as pd


class PostFilter(ABC):
    """
    Abstract base class for post-filters that process anomaly detection results.

    Post-filters can filter, transform, or enrich the anomaly detection results
    after detection has completed.
    """

    @abstractmethod
    def process(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """
        Process anomaly detection results.

        Args:
            results_df: Anomaly detection results

        Returns:
            pd.DataFrame: Processed results
        """
        pass
