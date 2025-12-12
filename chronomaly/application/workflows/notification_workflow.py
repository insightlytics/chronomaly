"""
Notification workflow orchestrator.
"""

import pandas as pd
from typing import List
from ...infrastructure.notifiers.base import Notifier


class NotificationWorkflow:
    """
    Main orchestrator class for the notification workflow.

    This workflow orchestrates the notification process:
    1. Receive anomaly data (as DataFrame)
    2. Prepare notification payload
    3. Send notifications via all configured notifiers

    Args:
        anomalies_data: DataFrame containing anomaly detection results
        notifiers: List of notifier instances (email, Slack, etc.)
    """

    def __init__(self, anomalies_data: pd.DataFrame, notifiers: List[Notifier]):
        # Validate anomalies_data
        if not isinstance(anomalies_data, pd.DataFrame):
            raise TypeError(
                f"anomalies_data must be a DataFrame, "
                f"got {type(anomalies_data).__name__}"
            )

        if anomalies_data.empty:
            raise ValueError("anomalies_data cannot be empty")

        self.anomalies_data = anomalies_data

        # Validate notifiers
        if not isinstance(notifiers, list):
            raise TypeError(f"notifiers must be a list, got {type(notifiers).__name__}")

        if not notifiers:
            raise ValueError("notifiers list cannot be empty")

        # Validate all items are Notifier instances
        for i, notifier in enumerate(notifiers):
            if not isinstance(notifier, Notifier):
                raise TypeError(
                    f"notifiers[{i}] must be a Notifier instance, "
                    f"got {type(notifier).__name__}"
                )

        self.notifiers = notifiers

    def run(self) -> None:
        """
        Execute the complete notification workflow.

        This method:
        1. Prepares notification payload from anomaly data
        2. Sends notifications via all configured notifiers

        Each notifier may apply its own transformers (e.g., filters)
        before sending, so different notifiers may receive different
        subsets of the data based on their configuration.

        Raises:
            RuntimeError: If notification fails
        """
        # Prepare payload
        payload = {"anomalies": self.anomalies_data}

        # Send notifications via all notifiers
        for notifier in self.notifiers:
            try:
                notifier.notify(payload)
            except Exception as e:
                # Re-raise with context about which notifier failed
                notifier_name = type(notifier).__name__
                raise RuntimeError(
                    f"Failed to send notification via {notifier_name}: {str(e)}"
                ) from e
