"""
Anomaly Detection: SQLite → Detect with Transformers → SQLite

This example demonstrates a complete anomaly detection pipeline with transformers:
1. Read forecast data from SQLite (from previous forecast workflow)
2. Read actual data from SQLite
3. Apply transformers at different stages
4. Detect anomalies with configurable confidence intervals
5. Filter and format results
6. Write anomalies to SQLite

Use Case: Production anomaly detection with data quality filters and formatting

Requirements:
    pip install pandas

Usage:
    python examples/anomaly/sqlite_anomaly_with_transformers.py
"""

import pandas as pd
import sqlite3
from datetime import datetime, timedelta

print("""
╔══════════════════════════════════════════════════════════════════════╗
║    ANOMALY DETECTION: SQLite → Transformers → Detect → SQLite       ║
║                                                                      ║
║  Pipeline: Forecast DB + Actual DB → Filter → Detect → Format       ║
╚══════════════════════════════════════════════════════════════════════╝
""")

# ============================================================================
# STEP 1: Create sample databases
# ============================================================================

print("\n📊 STEP 1: Create sample forecast and actual data")
print("=" * 70)

# Create forecast database (simulating previous forecast workflow output)
forecast_data = pd.DataFrame({
    'date': [datetime(2024, 11, 10)] * 5,
    'platform': ['desktop', 'mobile', 'tablet', 'desktop', 'mobile'],
    'channel': ['organic', 'paid', 'organic', 'paid', 'organic'],
    'page': ['home', 'product', 'blog', 'product', 'home'],
    'sessions': [
        '5000|4500|4600|4750|4875|5000|5125|5250|5400|5500',  # desktop_organic_home
        '3000|2700|2775|2850|2925|3000|3075|3150|3240|3300',  # mobile_paid_product
        '100|90|92|95|97|100|102|105|108|110',                # tablet_organic_blog (low traffic)
        '2000|1800|1850|1900|1950|2000|2050|2100|2160|2200',  # desktop_paid_product
        '4000|3600|3700|3800|3900|4000|4100|4200|4320|4400',  # mobile_organic_home
    ]
})

# Save to SQLite
conn = sqlite3.connect('/tmp/forecasts.db')
forecast_data.to_sql('forecasts', conn, if_exists='replace', index=False)
conn.close()
print(f"✓ Created forecast database: /tmp/forecasts.db")
print(f"  {len(forecast_data)} forecast rows")
print()

# Create actual data with anomalies
actual_data = pd.DataFrame({
    'date': [datetime(2024, 11, 10)] * 5,
    'platform': ['desktop', 'mobile', 'tablet', 'desktop', 'mobile'],
    'channel': ['organic', 'paid', 'organic', 'paid', 'organic'],
    'page': ['home', 'product', 'blog', 'product', 'home'],
    'sessions': [
        5100,   # desktop_organic_home: IN_RANGE
        3500,   # mobile_paid_product: ABOVE_UPPER (16.67% deviation) ⚠️
        95,     # tablet_organic_blog: IN_RANGE (but low traffic, will be filtered)
        1700,   # desktop_paid_product: BELOW_LOWER (15% deviation) ⚠️
        3200,   # mobile_organic_home: BELOW_LOWER (20% deviation) ⚠️
    ]
})

conn = sqlite3.connect('/tmp/actuals.db')
actual_data.to_sql('actuals', conn, if_exists='replace', index=False)
conn.close()
print(f"✓ Created actual database: /tmp/actuals.db")
print(f"  {len(actual_data)} actual rows")
print()

# ============================================================================
# STEP 2: Workflow configuration
# ============================================================================

print("\n🔧 STEP 2: Configure workflow with transformers")
print("=" * 70)

workflow_code = '''
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.databases import SQLiteDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter
from chronomaly.infrastructure.anomaly_detectors import ForecastActualAnomalyDetector
from chronomaly.infrastructure.transformers import DataTransformer

# Import unified transformers
from chronomaly.infrastructure.transformers.filters import (
    ValueFilter,
    CumulativeThresholdFilter
)
from chronomaly.infrastructure.transformers.formatters import ColumnFormatter

# ═══════════════════════════════════════════════════════════════
# READERS: SQLite configuration
# ═══════════════════════════════════════════════════════════════

# Forecast reader
forecast_reader = SQLiteDataReader(
    db_path='/tmp/forecasts.db',
    query="""
        SELECT date, platform, channel, page, sessions
        FROM forecasts
        WHERE date = '2024-11-10'
        ORDER BY date
    """
)

# Actual reader
actual_reader = SQLiteDataReader(
    db_path='/tmp/actuals.db',
    query="""
        SELECT date, platform, channel, page, sessions
        FROM actuals
        WHERE date = '2024-11-10'
        ORDER BY date
    """
)

# ═══════════════════════════════════════════════════════════════
# TRANSFORMER: Pivot configuration
# ═══════════════════════════════════════════════════════════════
transformer = DataTransformer(
    index='date',
    columns=['platform', 'channel', 'page'],
    values='sessions'
)

# ═══════════════════════════════════════════════════════════════
# DETECTOR: Anomaly detection (80% confidence interval)
# ═══════════════════════════════════════════════════════════════
detector = ForecastActualAnomalyDetector(
    transformer=transformer,
    dimension_names=['platform', 'channel', 'page'],
    lower_quantile_idx=1,   # q10
    upper_quantile_idx=9    # q90
)

# ═══════════════════════════════════════════════════════════════
# TRANSFORMERS: Apply at different stages
# ═══════════════════════════════════════════════════════════════

# Stage 1: Filter forecast data (before detection)
# Remove low-traffic metrics to reduce noise
cumulative_filter = CumulativeThresholdFilter(
    transformer=transformer,
    threshold_pct=0.90  # Keep top 90% by forecast volume
)

# Stage 2: Filter actual data (before detection)
# Remove metrics with very low traffic
min_traffic_filter = ValueFilter(
    column='sessions',
    min_value=500  # At least 500 sessions
)

# Stage 3: Filter results (after detection)
# Only keep significant anomalies
anomaly_filter = ValueFilter(
    column='status',
    values=['BELOW_LOWER', 'ABOVE_UPPER'],
    mode='include'
)

deviation_filter = ValueFilter(
    column='deviation_pct',
    min_value=10.0  # At least 10% deviation
)

# Stage 4: Format results (before write)
formatter = ColumnFormatter.percentage(
    columns='deviation_pct',
    decimal_places=1
)

# ═══════════════════════════════════════════════════════════════
# WRITER: Save anomalies
# ═══════════════════════════════════════════════════════════════
writer = SQLiteDataWriter(
    db_path='/tmp/anomalies.db',
    table_name='detected_anomalies'
)

# ═══════════════════════════════════════════════════════════════
# WORKFLOW: Assemble pipeline with transformers
# ═══════════════════════════════════════════════════════════════
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=writer,
    transformers={
        'after_forecast_read': [
            cumulative_filter  # Remove low-traffic metrics
        ],
        'after_actual_read': [
            min_traffic_filter  # Data quality filter
        ],
        'after_detection': [
            anomaly_filter,     # Only anomalies
            deviation_filter    # Significant deviations only
        ],
        'before_write': [
            formatter          # Format as percentage
        ]
    }
)

# Execute pipeline
anomalies = workflow.run()

print(f"\\n✓ Pipeline complete!")
print(f"  Input forecasts: {len(forecast_reader.read())}")
print(f"  Input actuals: {len(actual_reader.read())}")
print(f"  After filters: ~{len(anomalies)}")
print(f"  Significant anomalies: {len(anomalies)}")
print(f"  Saved to: /tmp/anomalies.db")
'''

print(workflow_code)

# ============================================================================
# STEP 3: Pipeline flow
# ============================================================================

print("\n\n📊 PIPELINE FLOW")
print("=" * 70)
print("""
Step 1: READ FORECAST
  Source: /tmp/forecasts.db
  Query:  SELECT with date filter
  Output: 5 forecast rows with quantiles

Step 2: TRANSFORM (after_forecast_read)
  Filter: CumulativeThresholdFilter (top 90%)
  Remove: Low-traffic metrics (tablet_organic_blog)
  Output: 4 high-value metrics

Step 3: READ ACTUAL
  Source: /tmp/actuals.db
  Query:  SELECT with date filter
  Output: 5 actual measurements

Step 4: TRANSFORM (after_actual_read)
  Filter: ValueFilter (min_value=500)
  Remove: Very low traffic metrics
  Output: 4 metrics with sufficient traffic

Step 5: DETECT ANOMALIES
  Input:  4 forecast + 4 actual (matched)
  Method: Compare actual vs forecast quantiles (q10/q90)
  Output: 4 detection results (IN_RANGE, BELOW_LOWER, ABOVE_UPPER)

Step 6: TRANSFORM (after_detection)
  Filter: ValueFilter (status) → Only anomalies
  Filter: ValueFilter (deviation) → Only >10% deviation
  Output: 3 significant anomalies

Step 7: TRANSFORM (before_write)
  Format: ColumnFormatter.percentage()
  Output: "15.0%" instead of 15.0

Step 8: WRITE
  Target: /tmp/anomalies.db
  Table:  detected_anomalies
  Rows:   3 significant anomalies
""")

# ============================================================================
# STEP 4: Expected results
# ============================================================================

print("\n\n📈 EXPECTED RESULTS")
print("=" * 70)

expected_results = pd.DataFrame({
    'date': [datetime(2024, 11, 10)] * 3,
    'platform': ['mobile', 'desktop', 'mobile'],
    'channel': ['paid', 'paid', 'organic'],
    'page': ['product', 'product', 'home'],
    'actual': [3500, 1700, 3200],
    'forecast': [3000, 2000, 4000],
    'lower_bound': [2700, 1800, 3600],
    'upper_bound': [3300, 2200, 4400],
    'status': ['ABOVE_UPPER', 'BELOW_LOWER', 'BELOW_LOWER'],
    'deviation_pct': ['16.7%', '15.0%', '20.0%']
})

print(expected_results.to_string(index=False))

# ============================================================================
# STEP 5: Benefits of transformer stages
# ============================================================================

print("\n\n💡 WHY USE MULTI-STAGE TRANSFORMERS?")
print("=" * 70)
print("""
1. EFFICIENCY (after_forecast_read, after_actual_read)
   ✓ Filter data BEFORE detection (less computation)
   ✓ Remove low-quality data early
   ✓ Reduce memory usage
   Example: Filter out metrics with <500 sessions

2. DATA QUALITY (after_forecast_read, after_actual_read)
   ✓ Remove outliers before detection
   ✓ Handle missing data
   ✓ Normalize units
   Example: Remove negative values, NULL checks

3. FOCUS (after_detection)
   ✓ Keep only actionable anomalies
   ✓ Filter by severity
   ✓ Remove false positives
   Example: Only >10% deviation

4. PRESENTATION (before_write)
   ✓ Format for reporting
   ✓ Add computed columns
   ✓ Round numbers
   Example: Format 15.3 → "15.3%"

5. COMPOSABILITY
   ✓ Mix and match transformers
   ✓ Add/remove without changing code structure
   ✓ Test transformers independently
   ✓ Reuse across different pipelines
""")

# ============================================================================
# STEP 6: Advanced transformer patterns
# ============================================================================

print("\n\n🔧 ADVANCED TRANSFORMER PATTERNS")
print("=" * 70)

advanced_patterns = '''
# Pattern 1: Time-based filtering
workflow = AnomalyDetectionWorkflow(
    ...,
    transformers={
        'after_forecast_read': [
            ValueFilter('date', values=pd.date_range('2024-11-01', '2024-11-30'))
        ]
    }
)

# Pattern 2: Dimension filtering
workflow = AnomalyDetectionWorkflow(
    ...,
    transformers={
        'after_actual_read': [
            ValueFilter('platform', values=['desktop', 'mobile']),  # Exclude tablet
            ValueFilter('channel', values=['spam'], mode='exclude')  # Exclude spam
        ]
    }
)

# Pattern 3: Multi-tier alerting
critical_workflow = AnomalyDetectionWorkflow(
    ...,
    transformers={
        'after_detection': [
            ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER']),
            ValueFilter('deviation_pct', min_value=50.0),  # Critical: >50%
            ColumnFormatter.percentage('deviation_pct')
        ]
    }
)

warning_workflow = AnomalyDetectionWorkflow(
    ...,
    transformers={
        'after_detection': [
            ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER']),
            ValueFilter('deviation_pct', min_value=20.0, max_value=50.0),  # Warning: 20-50%
            ColumnFormatter.percentage('deviation_pct')
        ]
    }
)

# Pattern 4: Custom formatting
workflow = AnomalyDetectionWorkflow(
    ...,
    transformers={
        'before_write': [
            ColumnFormatter({
                'actual': lambda x: f"{x:,.0f}",           # 5000 → "5,000"
                'forecast': lambda x: f"{x:,.0f}",         # 5000 → "5,000"
                'deviation_pct': lambda x: f"{x:.1f}%",    # 15.3 → "15.3%"
                'status': lambda x: '🔴' if x == 'ABOVE_UPPER' else '🔵' if x == 'BELOW_LOWER' else '🟢'
            })
        ]
    }
)
'''

print(advanced_patterns)

# ============================================================================
# STEP 7: Production tips
# ============================================================================

print("\n\n🚀 PRODUCTION TIPS")
print("=" * 70)
print("""
1. DATABASE OPTIMIZATION
   ✓ Create indexes on date, platform, channel columns
   ✓ Use appropriate data types (INTEGER, REAL, TEXT, DATE)
   ✓ Vacuum database regularly
   ✓ Monitor database size

2. ERROR HANDLING
   ✓ Handle missing forecasts gracefully
   ✓ Validate data quality before detection
   ✓ Log transformer actions for debugging
   ✓ Set up alerts for failed pipelines

3. SCHEDULING
   ✓ Run after forecast workflow completes
   ✓ Use cron or Airflow for scheduling
   ✓ Typical schedule: 3:00 AM daily
   ✓ Monitor execution time

4. ALERTING
   ✓ Send notifications for critical anomalies
   ✓ Include context (metric, deviation, trend)
   ✓ Avoid alert fatigue (use severity levels)
   ✓ Provide actionable recommendations

5. MONITORING
   ✓ Track detection rate (% of metrics with anomalies)
   ✓ Monitor false positive rate
   ✓ Log transformer effectiveness
   ✓ Review and tune thresholds monthly
""")

print("\n" + "=" * 70)
print("This example shows the POWER of multi-stage transformers!")
print("Filter → Detect → Format → Alert for production-ready anomaly detection.")
print("=" * 70)
