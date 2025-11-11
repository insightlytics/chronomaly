"""
Shared mixins for common functionality.
"""

import pandas as pd
from typing import Dict, List, Callable


class TransformableMixin:
    """
    Mixin that provides transformer application functionality.

    Components that need to apply transformers should inherit from this mixin
    and set self.transformers in their __init__ method.

    Usage:
        class MyComponent(TransformableMixin):
            def __init__(self, transformers=None):
                self.transformers = transformers or {}

            def process(self, df):
                df = self._apply_transformers(df, 'after')
                return df
    """

    def _apply_transformers(self, df: pd.DataFrame, stage: str) -> pd.DataFrame:
        """
        Apply transformers for a specific stage.

        Args:
            df: DataFrame to transform
            stage: Stage name ('before' or 'after')

        Returns:
            pd.DataFrame: Transformed DataFrame

        Raises:
            TypeError: If transformer doesn't have proper interface
        """
        if not hasattr(self, 'transformers'):
            return df

        if stage not in self.transformers:
            return df

        result = df
        for transformer in self.transformers[stage]:
            # Support .filter() method (for filters)
            if hasattr(transformer, 'filter'):
                result = transformer.filter(result)
            # Support .format() method (for formatters)
            elif hasattr(transformer, 'format'):
                result = transformer.format(result)
            # Support callable objects (for any transformer)
            elif callable(transformer):
                result = transformer(result)
            else:
                raise TypeError(
                    f"Transformer must have .filter(), .format() method or be callable. "
                    f"Got: {type(transformer).__name__}"
                )

        return result
