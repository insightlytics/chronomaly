"""
Advanced: Anomaly Detection with Pre and Post Filters

This example demonstrates the power of filters:
1. PRE-FILTER: Reduce dataset before detection (CumulativeThresholdFilter)
2. DETECT: Run anomaly detection
3. POST-FILTER: Filter and format results (AnomalyFilter, DeviationFormatter)

Use Case: Focus on top metrics and format results for reporting

Requirements:
    pip install pandas

Usage:
    python examples/advanced/anomaly_with_filters.py
"""

import pandas as pd
import sqlite3
from datetime import datetime

print("""
╔══════════════════════════════════════════════════════════════════════╗
║          ADVANCED: Anomaly Detection with Filters                    ║
║                                                                      ║
║  Pre-Filter → Detect → Post-Filter → Format → Output                ║
╚══════════════════════════════════════════════════════════════════════╝
""")

# Create comprehensive forecast data
def create_comprehensive_forecast():
    """Create forecast with many metrics."""
    data = pd.DataFrame({
        'date': [datetime(2024, 11, 10)],
        # High-value metrics
        'desktop_organic_home': ['5000|4500|4600|4750|4875|5000|5125|5250|5400|5500'],
        'desktop_paid_product': ['3000|2700|2775|2850|2925|3000|3075|3150|3240|3300'],
        'mobile_organic_home': ['4000|3600|3700|3800|3900|4000|4100|4200|4320|4400'],

        # Medium-value metrics
        'tablet_organic_home': ['1000|900|925|950|975|1000|1025|1050|1080|1100'],
        'tablet_paid_product': ['500|450|465|480|490|500|510|525|540|550'],

        # Low-value metrics (will be filtered out by cumulative threshold)
        'other_organic_blog': ['100|90|92|95|97|100|102|105|108|110'],
        'other_paid_blog': ['50|45|46|48|49|50|51|52|54|55']
    })

    data.to_csv('/tmp/comprehensive_forecast.csv', index=False)
    print("✓ Created forecast with 7 metrics")
    return data


# Create actual data with anomalies
def create_actual_with_anomalies():
    """Create actual data with various anomaly types."""
    data = pd.DataFrame({
        'date': [datetime(2024, 11, 10)] * 7,
        'platform': ['desktop', 'desktop', 'mobile', 'tablet', 'tablet', 'other', 'other'],
        'channel': ['organic', 'paid', 'organic', 'organic', 'paid', 'organic', 'paid'],
        'page': ['home', 'product', 'home', 'home', 'product', 'blog', 'blog'],
        'sessions': [
            4800,   # desktop_organic_home: IN_RANGE
            3500,   # desktop_paid_product: ABOVE_UPPER (16.67% deviation)
            3200,   # mobile_organic_home: BELOW_LOWER (11.11% deviation)
            980,    # tablet_organic_home: IN_RANGE
            480,    # tablet_paid_product: IN_RANGE
            105,    # other_organic_blog: IN_RANGE (but will be filtered by pre-filter)
            52      # other_paid_blog: IN_RANGE (but will be filtered by pre-filter)
        ]
    })

    data.to_csv('/tmp/comprehensive_actual.csv', index=False)
    print("✓ Created actual data with 7 metrics")
    return data


print("\n📋 WORKFLOW CONFIGURATION")
print("=" * 70)
print("Input:       /tmp/comprehensive_forecast.csv (7 metrics)")
print("             /tmp/comprehensive_actual.csv")
print("Pre-Filter:  CumulativeThresholdFilter (top 95%)")
print("Post-Filter: AnomalyFilter (only anomalies)")
print("             DeviationFilter (min 10% deviation)")
print("             DeviationFormatter (format as percentage)")
print("Output:      /tmp/filtered_anomalies.db")
print()

forecast = create_comprehensive_forecast()
actual = create_actual_with_anomalies()

print("\n🔧 WORKFLOW CODE")
print("=" * 70)

workflow_code = '''
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter
from chronomaly.infrastructure.anomaly_detectors import ForecastActualAnomalyDetector
from chronomaly.infrastructure.transformers import DataTransformer

# Import filters
from chronomaly.infrastructure.filters.pre import CumulativeThresholdFilter
from chronomaly.infrastructure.filters.post import (
    AnomalyFilter,
    DeviationFilter,
    DeviationFormatter
)

# Configure readers
forecast_reader = CSVDataReader('/tmp/comprehensive_forecast.csv')
actual_reader = CSVDataReader('/tmp/comprehensive_actual.csv')

# Configure transformer
transformer = DataTransformer(
    index='date',
    columns=['platform', 'channel', 'page'],
    values='sessions'
)

# ═══════════════════════════════════════════════════════════════
# PRE-FILTER: Reduce dataset BEFORE detection
# ═══════════════════════════════════════════════════════════════
pre_filter = CumulativeThresholdFilter(
    transformer=transformer,
    threshold_pct=0.95  # Keep only top 95% metrics by forecast value
)

# This will filter out low-value metrics (other_organic_blog, other_paid_blog)
# BEFORE running anomaly detection, saving computation time

# ═══════════════════════════════════════════════════════════════
# DETECTOR: Pure anomaly detection
# ═══════════════════════════════════════════════════════════════
detector = ForecastActualAnomalyDetector(
    transformer=transformer,
    dimension_names=['platform', 'channel', 'page'],
    lower_quantile_idx=1,   # q10
    upper_quantile_idx=9    # q90
)

# ═══════════════════════════════════════════════════════════════
# POST-FILTERS: Process results AFTER detection
# ═══════════════════════════════════════════════════════════════

# Filter 1: Keep only anomalies
anomaly_filter = AnomalyFilter()

# Filter 2: Keep only significant deviations (>10%)
deviation_filter = DeviationFilter(
    min_deviation_pct=10.0,
    keep_in_range=False  # Remove IN_RANGE status
)

# Filter 3: Format deviation as percentage string
formatter = DeviationFormatter(decimal_places=1)

post_filters = [anomaly_filter, deviation_filter, formatter]

# ═══════════════════════════════════════════════════════════════
# WORKFLOW: Assemble pipeline
# ═══════════════════════════════════════════════════════════════
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=SQLiteDataWriter('/tmp/filtered_anomalies.db', 'anomalies'),
    pre_filters=[pre_filter],        # Applied before detection
    post_filters=post_filters         # Applied after detection
)

# Run the pipeline
results = workflow.run()

print(f"\\n✓ Pipeline complete!")
print(f"  Input metrics: 7")
print(f"  After pre-filter: ~5 (top 95%)")
print(f"  After detection: {len(results)}")
print(f"  Significant anomalies: {len(results[results['deviation_pct'] != '0.0%'])}")
'''

print(workflow_code)

print("\n\n📊 PIPELINE FLOW")
print("=" * 70)
print("""
Step 1: PRE-FILTER
  Input:  7 metrics
  Filter: CumulativeThresholdFilter (top 95%)
  Output: ~5 metrics (filtered out low-value metrics)

Step 2: DETECT
  Input:  5 metrics
  Detect: Compare actual vs forecast with q10/q90
  Output: 5 detection results (all statuses)

Step 3: POST-FILTER
  Input:  5 detection results
  Filter: AnomalyFilter → Keep only ABOVE_UPPER/BELOW_LOWER
  Filter: DeviationFilter → Keep only >10% deviation
  Format: DeviationFormatter → "16.7%" instead of 16.7
  Output: 2 significant anomalies

Step 4: WRITE
  Output: Save to SQLite database
""")

print("\n\n📈 EXPECTED RESULTS")
print("=" * 70)

expected_results = pd.DataFrame({
    'date': [datetime(2024, 11, 10)] * 2,
    'platform': ['desktop', 'mobile'],
    'channel': ['paid', 'organic'],
    'page': ['product', 'home'],
    'actual': [3500, 3200],
    'forecast': [3000, 4000],
    'lower_bound': [2700, 3600],
    'upper_bound': [3300, 4400],
    'status': ['ABOVE_UPPER', 'BELOW_LOWER'],
    'deviation_pct': ['16.7%', '11.1%']
})

print(expected_results.to_string(index=False))

print("\n\n💡 WHY USE FILTERS?")
print("=" * 70)
print("""
1. PRE-FILTERS (Before Detection)
   ✓ Reduce computation time
   ✓ Focus on important metrics
   ✓ Filter by forecast value, date range, dimensions
   ✓ Example: CumulativeThresholdFilter keeps top 95%

2. POST-FILTERS (After Detection)
   ✓ Clean up results
   ✓ Focus on actionable anomalies
   ✓ Format for reporting
   ✓ Example: AnomalyFilter removes IN_RANGE status

3. Benefits
   ✓ Modular: Add/remove filters easily
   ✓ Composable: Chain multiple filters
   ✓ Testable: Test each filter independently
   ✓ Flexible: Use same filter in different pipelines
""")

print("\n\n🔧 FILTER CUSTOMIZATION")
print("=" * 70)

customization_code = '''
# Example 1: Stricter filters
strict_post_filters = [
    AnomalyFilter(),
    DeviationFilter(min_deviation_pct=20.0),  # Only >20% deviation
    DeviationFormatter(decimal_places=2)       # 2 decimal places
]

# Example 2: Focus on specific platforms
from chronomaly.infrastructure.filters.post import ValueFilter

platform_filter = ValueFilter(
    column='platform',
    values=['desktop', 'mobile'],  # Exclude tablet
    mode='include'
)

post_filters = [platform_filter, AnomalyFilter(), formatter]

# Example 3: Alert thresholds
critical_filter = DeviationFilter(
    min_deviation_pct=50.0,  # >50% = critical
    keep_in_range=False
)

warning_filter = DeviationFilter(
    min_deviation_pct=20.0,  # 20-50% = warning
    keep_in_range=False
)
'''

print(customization_code)

print("\n" + "=" * 70)
print("This example shows the POWER of modular filters!")
print("You can mix and match filters for any use case.")
print("=" * 70)
