"""
Shared mixins for common functionality.
"""

import pandas as pd


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
        # BUG-021 FIX: Add error handling with context
        for i, transformer in enumerate(self.transformers[stage]):
            try:
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
            except Exception as e:
                transformer_name = type(transformer).__name__
                error_msg = (
                    f"Transformer {i+1} ({transformer_name}) failed "
                    f"during '{stage}' stage: {str(e)}"
                )
                raise RuntimeError(error_msg) from e

        return result
