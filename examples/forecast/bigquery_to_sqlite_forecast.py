"""
Forecast Workflow: BigQuery → TimesFM Forecaster → SQLite

This example shows how to:
1. Read historical data from Google BigQuery
2. Generate forecasts using TimesFM
3. Write forecasts to local SQLite database

Use Case: Cloud data warehouse → Local database for offline analysis

Requirements:
    pip install pandas google-cloud-bigquery

Setup:
    1. Set up Google Cloud credentials:
       export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"

    2. Ensure you have access to BigQuery dataset

Usage:
    python examples/forecast/bigquery_to_sqlite_forecast.py
"""

import pandas as pd
from datetime import datetime, timedelta

print("""
╔══════════════════════════════════════════════════════════════════════╗
║         FORECAST: BigQuery → TimesFM → SQLite                        ║
║                                                                      ║
║  Pipeline: Cloud Data Warehouse → Forecaster → Local Database       ║
╚══════════════════════════════════════════════════════════════════════╝
""")

# ============================================================================
# STEP 1: Create sample data (simulate BigQuery)
# ============================================================================

print("\n📊 STEP 1: Simulate BigQuery data")
print("=" * 70)
print("In production, you would query BigQuery with:")
print("  SELECT date, platform, channel, page, sessions")
print("  FROM `project.dataset.table`")
print("  WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)")
print()

# Create sample historical data
dates = pd.date_range(end=datetime.now(), periods=90, freq='D')
data = pd.DataFrame({
    'date': dates.tolist() * 3,
    'platform': ['desktop'] * 90 + ['mobile'] * 90 + ['tablet'] * 90,
    'channel': ['organic'] * 90 + ['paid'] * 90 + ['organic'] * 90,
    'page': ['home'] * 90 + ['product'] * 90 + ['blog'] * 90,
    'sessions': [
        # Desktop organic home (growing trend)
        *[5000 + i * 10 + (i % 7) * 100 for i in range(90)],
        # Mobile paid product (seasonal pattern)
        *[3000 + (i % 30) * 50 for i in range(90)],
        # Tablet organic blog (declining trend)
        *[1000 - i * 5 + (i % 14) * 30 for i in range(90)]
    ]
})

print(f"✓ Loaded {len(data)} rows from BigQuery (simulated)")
print(f"  Date range: {data['date'].min().date()} to {data['date'].max().date()}")
print(f"  Unique metrics: {data.groupby(['platform', 'channel', 'page']).ngroups}")
print()

# ============================================================================
# STEP 2: Configuration
# ============================================================================

print("\n🔧 STEP 2: Configure workflow")
print("=" * 70)

workflow_code = '''
from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter
from chronomaly.infrastructure.forecasters import TimesFMForecaster

# ═══════════════════════════════════════════════════════════════
# READER: BigQuery configuration
# ═══════════════════════════════════════════════════════════════
bigquery_reader = BigQueryDataReader(
    query="""
        SELECT
            date,
            platform,
            channel,
            page,
            sessions
        FROM `your-project.analytics.daily_metrics`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
        ORDER BY date
    """,
    project_id="your-project-id"
)

# ═══════════════════════════════════════════════════════════════
# FORECASTER: TimesFM with 30-day horizon
# ═══════════════════════════════════════════════════════════════
forecaster = TimesFMForecaster(
    context_length=90,          # Use 90 days of history
    horizon_length=30,          # Forecast 30 days ahead
    num_samples=100,            # Generate 100 samples for quantiles
    index_col='date',
    value_col='sessions',
    freq='D'                    # Daily frequency
)

# ═══════════════════════════════════════════════════════════════
# WRITER: SQLite database
# ═══════════════════════════════════════════════════════════════
sqlite_writer = SQLiteDataWriter(
    db_path='/data/forecasts.db',
    table_name='daily_forecasts'
)

# ═══════════════════════════════════════════════════════════════
# WORKFLOW: Assemble and run
# ═══════════════════════════════════════════════════════════════
workflow = ForecastWorkflow(
    data_reader=bigquery_reader,
    forecaster=forecaster,
    data_writer=sqlite_writer
)

# Execute pipeline
forecasts = workflow.run()

print(f"✓ Forecasted {len(forecasts)} rows")
print(f"  Saved to: /data/forecasts.db")
'''

print(workflow_code)

# ============================================================================
# STEP 3: Pipeline flow explanation
# ============================================================================

print("\n\n📊 PIPELINE FLOW")
print("=" * 70)
print("""
Step 1: READ from BigQuery
  Query:  Cloud data warehouse (last 90 days)
  Output: Historical time series data

Step 2: FORECAST with TimesFM
  Input:  90 days of history per metric
  Model:  TimesFM pre-trained foundation model
  Output: 30-day forecasts with quantiles (q10, q50, q90)

Step 3: WRITE to SQLite
  Input:  Forecast results with quantiles
  Format: One row per date-metric with quantile string
  Output: Local SQLite database for offline use

Typical Output Schema:
  - date: Forecast date
  - platform: desktop/mobile/tablet
  - channel: organic/paid
  - page: home/product/blog
  - sessions: Quantile string (q0|q10|q20|...|q90|q100)
""")

# ============================================================================
# STEP 4: Production tips
# ============================================================================

print("\n\n💡 PRODUCTION TIPS")
print("=" * 70)
print("""
1. BIGQUERY BEST PRACTICES
   ✓ Use partitioned tables for efficient queries
   ✓ Filter by date to reduce data scanned
   ✓ Use clustering for frequently filtered columns
   ✓ Monitor query costs with dry_run=True

2. CREDENTIALS MANAGEMENT
   ✓ Use service accounts with minimal permissions
   ✓ Store credentials securely (not in code!)
   ✓ Use environment variables or secret managers
   ✓ Rotate credentials regularly

3. COST OPTIMIZATION
   ✓ Cache BigQuery results for development
   ✓ Use scheduled queries for regular updates
   ✓ Compress data before transfer
   ✓ Consider BigQuery Storage API for large datasets

4. ERROR HANDLING
   ✓ Handle network timeouts gracefully
   ✓ Implement retry logic for transient failures
   ✓ Log query execution time and data volume
   ✓ Set up alerting for failed pipelines

5. SCHEDULING
   ✓ Run daily after source data is updated
   ✓ Use cron, Airflow, or Cloud Scheduler
   ✓ Typical schedule: 2:00 AM (after daily ETL)
   ✓ Monitor execution time and adjust resources
""")

# ============================================================================
# STEP 5: Example queries
# ============================================================================

print("\n\n📝 EXAMPLE BIGQUERY QUERIES")
print("=" * 70)

example_queries = '''
-- Query 1: Basic aggregation
SELECT
    date,
    platform,
    SUM(sessions) as sessions
FROM `project.analytics.events`
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY date, platform
ORDER BY date;

-- Query 2: With multiple dimensions
SELECT
    date,
    platform,
    channel,
    page,
    SUM(sessions) as sessions,
    SUM(revenue) as revenue
FROM `project.analytics.daily_metrics`
WHERE date BETWEEN '2024-01-01' AND CURRENT_DATE()
    AND platform IN ('desktop', 'mobile', 'tablet')
GROUP BY date, platform, channel, page
ORDER BY date;

-- Query 3: With data quality filters
SELECT
    date,
    platform,
    channel,
    COALESCE(SUM(sessions), 0) as sessions
FROM `project.analytics.events`
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    AND sessions >= 0  -- Remove negative values
    AND platform IS NOT NULL
GROUP BY date, platform, channel
HAVING sessions >= 100  -- Filter out low-traffic metrics
ORDER BY date;
'''

print(example_queries)

# ============================================================================
# STEP 6: Alternative: Save to CSV first (for development)
# ============================================================================

print("\n\n🔄 DEVELOPMENT WORKFLOW")
print("=" * 70)
print("""
For development, save BigQuery data to CSV first:

1. Query BigQuery and save to CSV:
   bq query --use_legacy_sql=false \\
     --format=csv \\
     --max_rows=100000 \\
     'SELECT * FROM `project.dataset.table`' \\
     > data.csv

2. Use CSV for local development:
   from chronomaly.infrastructure.data.readers.files import CSVDataReader
   reader = CSVDataReader('data.csv')

3. Switch to BigQuery in production

Benefits:
✓ Faster iteration (no network calls)
✓ No BigQuery costs during development
✓ Works offline
✓ Easy to version control sample data
""")

print("\n" + "=" * 70)
print("This example shows how to integrate cloud data with local forecasting!")
print("BigQuery → Local DB enables offline analysis and faster iteration.")
print("=" * 70)
