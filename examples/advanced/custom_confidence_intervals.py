"""
Advanced: Custom Confidence Intervals

This example shows how to use different quantile pairs for anomaly detection:
- q10/q90 → 80% confidence interval (default)
- q5/q95  → 90% confidence interval (stricter)
- q25/q75 → 50% confidence interval (looser, Interquartile Range)

Use Case: Adjust sensitivity based on business requirements

Requirements:
    pip install pandas

Usage:
    python examples/advanced/custom_confidence_intervals.py
"""

import pandas as pd
from datetime import datetime

print("""
╔══════════════════════════════════════════════════════════════════════╗
║         ADVANCED: Custom Confidence Intervals                        ║
║                                                                      ║
║  Adjust detection sensitivity with different quantile pairs         ║
╚══════════════════════════════════════════════════════════════════════╝
""")

# Create test data
def create_test_data():
    """Create forecast and actual data for testing different intervals."""
    forecast = pd.DataFrame({
        'date': [datetime(2024, 11, 10)],
        # Format: point|q5|q10|q15|q20|q25|...|q75|q80|q85|q90|q95
        # Indices:   0    1    2    3    4    5 ... 15   16   17   18   19
        'metric_a': ['1000|850|900|925|950|975|1000|1025|1050|1075|1100|1150']
    })

    actual = pd.DataFrame({
        'date': [datetime(2024, 11, 10)],
        'metric': ['metric_a'],
        'value': [1120]  # Test different intervals with this value
    })

    return forecast, actual


print("\n📊 TEST DATA")
print("=" * 70)

forecast, actual = create_test_data()

print("Forecast quantiles:")
print("  point: 1000")
print("  q5:    850   (5th percentile)")
print("  q10:   900   (10th percentile)")
print("  q25:   975   (25th percentile - Q1)")
print("  q75:   1025  (75th percentile - Q3)")
print("  q90:   1100  (90th percentile)")
print("  q95:   1150  (95th percentile)")
print()
print(f"Actual value: 1120")
print()

print("\n🔧 COMPARING CONFIDENCE INTERVALS")
print("=" * 70)

comparison_code = '''
from chronomaly.infrastructure.anomaly_detectors import ForecastActualAnomalyDetector
from chronomaly.infrastructure.transformers import DataTransformer

# Configure transformer
transformer = DataTransformer(
    index='date',
    columns=['metric'],
    values='value'
)

# ═══════════════════════════════════════════════════════════════
# OPTION 1: 80% Confidence Interval (DEFAULT)
# ═══════════════════════════════════════════════════════════════
detector_80 = ForecastActualAnomalyDetector(
    transformer=transformer,
    lower_quantile_idx=2,   # q10 (index 2 in our format)
    upper_quantile_idx=10   # q90 (index 10)
)

# With actual=1120, upper_bound=1100
# Status: ABOVE_UPPER (because 1120 > 1100)
# Deviation: ((1120-1100)/1100)*100 = 1.82%

# ═══════════════════════════════════════════════════════════════
# OPTION 2: 90% Confidence Interval (STRICTER)
# ═══════════════════════════════════════════════════════════════
detector_90 = ForecastActualAnomalyDetector(
    transformer=transformer,
    lower_quantile_idx=1,   # q5 (index 1)
    upper_quantile_idx=11   # q95 (index 11)
)

# With actual=1120, upper_bound=1150
# Status: IN_RANGE (because 1120 < 1150)
# No anomaly detected!

# ═══════════════════════════════════════════════════════════════
# OPTION 3: 50% Confidence Interval (LOOSER, IQR)
# ═══════════════════════════════════════════════════════════════
detector_50 = ForecastActualAnomalyDetector(
    transformer=transformer,
    lower_quantile_idx=5,   # q25 (index 5)
    upper_quantile_idx=15   # q75 (index 15)
)

# With actual=1120, upper_bound=1025
# Status: ABOVE_UPPER (because 1120 > 1025)
# Deviation: ((1120-1025)/1025)*100 = 9.27%

# MORE SENSITIVE to anomalies!
'''

print(comparison_code)

print("\n\n📊 COMPARISON TABLE")
print("=" * 70)

comparison_table = pd.DataFrame({
    'Interval': ['50% (IQR)', '80% (Default)', '90% (Strict)'],
    'Lower Index': [5, 2, 1],
    'Upper Index': [15, 10, 11],
    'Lower Bound': [975, 900, 850],
    'Upper Bound': [1025, 1100, 1150],
    'Status (actual=1120)': ['ABOVE_UPPER', 'ABOVE_UPPER', 'IN_RANGE'],
    'Deviation': ['9.27%', '1.82%', '0%']
})

print(comparison_table.to_string(index=False))

print("\n\n💡 CHOOSING THE RIGHT INTERVAL")
print("=" * 70)
print("""
50% Interval (q25/q75) - Interquartile Range
  Use when: You want high sensitivity
  ✓ Detect smaller deviations
  ✓ More anomalies flagged
  ✗ Higher false positive rate
  Example: E-commerce peak seasons

80% Interval (q10/q90) - DEFAULT
  Use when: Balanced detection
  ✓ Good sensitivity vs specificity
  ✓ Standard statistical practice
  ✓ Works for most use cases
  Example: General monitoring

90% Interval (q5/q95) - Stricter
  Use when: Only want significant anomalies
  ✓ Lower false positive rate
  ✓ Focus on major deviations
  ✗ May miss subtle anomalies
  Example: Critical systems, SLA monitoring

95% Interval (q2.5/q97.5) - Very Strict
  Use when: Extremely high confidence needed
  ✓ Very low false positives
  ✗ May miss many real anomalies
  Example: Financial fraud detection
""")

print("\n\n🎯 BUSINESS USE CASES")
print("=" * 70)

use_cases = '''
# Use Case 1: E-commerce Platform
# During normal times: 80% interval
# During Black Friday: 50% interval (more sensitive)

detector_normal = ForecastActualAnomalyDetector(
    transformer=transformer,
    lower_quantile_idx=2,  # q10
    upper_quantile_idx=10  # q90
)

detector_peak = ForecastActualAnomalyDetector(
    transformer=transformer,
    lower_quantile_idx=5,   # q25 (IQR)
    upper_quantile_idx=15   # q75
)

# Use Case 2: SLA Monitoring
# Critical services: 90% interval (stricter)
# Non-critical: 80% interval

detector_critical = ForecastActualAnomalyDetector(
    transformer=transformer,
    lower_quantile_idx=1,   # q5
    upper_quantile_idx=11   # q95
)

detector_standard = ForecastActualAnomalyDetector(
    transformer=transformer,
    lower_quantile_idx=2,   # q10
    upper_quantile_idx=10   # q90
)

# Use Case 3: Multi-tier Alerting
# Tier 1: 50% interval → Warning
# Tier 2: 80% interval → Alert
# Tier 3: 90% interval → Critical

warning_detector = ForecastActualAnomalyDetector(
    transformer, lower_quantile_idx=5, upper_quantile_idx=15
)

alert_detector = ForecastActualAnomalyDetector(
    transformer, lower_quantile_idx=2, upper_quantile_idx=10
)

critical_detector = ForecastActualAnomalyDetector(
    transformer, lower_quantile_idx=1, upper_quantile_idx=11
)
'''

print(use_cases)

print("\n\n📈 SENSITIVITY COMPARISON")
print("=" * 70)
print("""
Let's test with different actual values:

Actual | 50% Status    | 80% Status    | 90% Status    | Notes
-------|---------------|---------------|---------------|------------------
850    | BELOW_LOWER   | IN_RANGE      | IN_RANGE      | Only 50% detects
900    | BELOW_LOWER   | IN_RANGE      | IN_RANGE      | Only 50% detects
950    | BELOW_LOWER   | IN_RANGE      | IN_RANGE      | Only 50% detects
975    | IN_RANGE      | IN_RANGE      | IN_RANGE      | All clear
1000   | IN_RANGE      | IN_RANGE      | IN_RANGE      | Perfect match
1025   | IN_RANGE      | IN_RANGE      | IN_RANGE      | All clear
1050   | ABOVE_UPPER   | IN_RANGE      | IN_RANGE      | Only 50% detects
1100   | ABOVE_UPPER   | IN_RANGE      | IN_RANGE      | Only 50% detects
1120   | ABOVE_UPPER   | ABOVE_UPPER   | IN_RANGE      | 50% & 80% detect
1200   | ABOVE_UPPER   | ABOVE_UPPER   | ABOVE_UPPER   | All detect!

Observation:
- 50% interval: 6/10 flagged as anomalies (most sensitive)
- 80% interval: 2/10 flagged as anomalies (balanced)
- 90% interval: 1/10 flagged as anomalies (least sensitive)
""")

print("\n\n🔧 COMPLETE WORKFLOW EXAMPLE")
print("=" * 70)

complete_example = '''
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter
from chronomaly.infrastructure.anomaly_detectors import ForecastActualAnomalyDetector
from chronomaly.infrastructure.transformers import DataTransformer

# Read data
forecast_reader = CSVDataReader('/tmp/forecast.csv')
actual_reader = CSVDataReader('/tmp/actual.csv')

# Configure transformer
transformer = DataTransformer(
    index='date',
    columns=['metric'],
    values='value'
)

# Choose your confidence interval:

# For production monitoring (balanced):
detector = ForecastActualAnomalyDetector(
    transformer=transformer,
    lower_quantile_idx=2,   # q10
    upper_quantile_idx=10   # q90
)

# For high-sensitivity (detect more):
# detector = ForecastActualAnomalyDetector(
#     transformer=transformer,
#     lower_quantile_idx=5,   # q25
#     upper_quantile_idx=15   # q75
# )

# For critical systems (detect less, high confidence):
# detector = ForecastActualAnomalyDetector(
#     transformer=transformer,
#     lower_quantile_idx=1,   # q5
#     upper_quantile_idx=11   # q95
# )

# Create workflow
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=SQLiteDataWriter('/tmp/results.db', 'anomalies')
)

# Run detection
results = workflow.run()
'''

print(complete_example)

print("\n" + "=" * 70)
print("Experiment with different intervals to find what works best!")
print("Start with 80% (default) and adjust based on false positives/negatives.")
print("=" * 70)
