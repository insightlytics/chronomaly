"""
Forecast Workflow: SQLite → Forecast → SQLite

This example shows how to:
1. Read historical data from SQLite database
2. Generate forecasts
3. Write forecast results to SQLite database

Use Case: Production database-to-database forecasting pipeline

Requirements:
    pip install pandas

Usage:
    python examples/forecast/sqlite_to_sqlite_forecast.py
"""

import pandas as pd
import sqlite3
from datetime import datetime, timedelta

print("""
╔══════════════════════════════════════════════════════════════════════╗
║        FORECAST WORKFLOW: SQLite → Forecast → SQLite                 ║
║                                                                      ║
║  Pipeline: Source DB → Forecaster → Destination DB                  ║
╚══════════════════════════════════════════════════════════════════════╝
""")

# Create sample source database
def create_source_database():
    """Create sample source database with historical data."""
    dates = pd.date_range(start='2024-01-01', periods=90, freq='D')

    data = pd.DataFrame({
        'date': dates,
        'metric_name': 'sessions',
        'platform': 'desktop',
        'value': [1000 + i * 10 + (i % 7) * 50 for i in range(90)]
    })

    conn = sqlite3.connect('/tmp/source_metrics.db')
    data.to_sql('metrics', conn, if_exists='replace', index=False)
    conn.close()

    print(f"✓ Created source database: /tmp/source_metrics.db")
    print(f"  Table: metrics")
    print(f"  Rows: {len(data)}")
    return data


print("\n📋 WORKFLOW CONFIGURATION")
print("=" * 70)
print("Source DB:      /tmp/source_metrics.db (metrics table)")
print("Destination DB: /tmp/forecasts_output.db (forecasts table)")
print("Forecaster:     TimesFM")
print("Frequency:      Daily (D)")
print("Horizon:        14 days")
print()

# Create source data
sample_data = create_source_database()

print("\n📊 SOURCE DATA PREVIEW")
print("=" * 70)
print(sample_data.tail(10).to_string(index=False))

print("\n\n🔧 WORKFLOW CODE")
print("=" * 70)

workflow_code = '''
from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.databases import SQLiteDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter
from chronomaly.infrastructure.forecasters import TimesFMForecaster

# Step 1: Configure source database reader
reader = SQLiteDataReader(
    database_path='/tmp/source_metrics.db',
    table_name='metrics'
)

# Alternative: Use custom SQL query
reader_with_query = SQLiteDataReader(
    database_path='/tmp/source_metrics.db',
    query="""
        SELECT date, metric_name, platform, value
        FROM metrics
        WHERE platform = 'desktop'
        AND date >= date('now', '-90 days')
        ORDER BY date
    """
)

# Step 2: Configure forecaster
forecaster = TimesFMForecaster(
    context_length=90,
    horizon=14,
    freq='D'
)

# Step 3: Configure destination database writer
writer = SQLiteDataWriter(
    database_path='/tmp/forecasts_output.db',
    table_name='forecasts',
    if_exists='append'  # Append to existing forecasts
)

# Step 4: Create and run workflow
workflow = ForecastWorkflow(
    data_reader=reader,
    forecaster=forecaster,
    data_writer=writer
)

# Run the forecast
print("Starting forecast generation...")
results = workflow.run()

print(f"✓ Forecast complete!")
print(f"  Input rows: {len(reader.load())}")
print(f"  Output rows: {len(results)}")
print(f"  Destination: /tmp/forecasts_output.db")
'''

print(workflow_code)

print("\n\n🔍 QUERY RESULTS")
print("=" * 70)
print("""
After running, query your forecasts:

sqlite3 /tmp/forecasts_output.db "SELECT * FROM forecasts LIMIT 5"

Or use pandas:

import sqlite3
import pandas as pd

conn = sqlite3.connect('/tmp/forecasts_output.db')
forecasts = pd.read_sql('SELECT * FROM forecasts', conn)
conn.close()

print(forecasts.head())
""")

print("\n\n💡 PRODUCTION TIPS")
print("=" * 70)
print("""
1. Use indexes for better query performance:
   CREATE INDEX idx_date ON forecasts(date);
   CREATE INDEX idx_metric ON forecasts(metric_name);

2. Partition by date for large datasets:
   CREATE TABLE forecasts_2024_01 AS SELECT * FROM forecasts WHERE ...

3. Schedule with cron:
   0 2 * * * python forecast_workflow.py  # Run daily at 2 AM

4. Monitor forecast quality:
   - Track MAE/RMSE over time
   - Alert on anomalous forecast patterns
   - Version control forecast parameters
""")

print("\n\n🔄 AUTOMATION EXAMPLE")
print("=" * 70)

automation_code = '''
# scheduled_forecast.py
import schedule
import time
from datetime import datetime

def run_forecast_job():
    """Daily forecast generation job."""
    print(f"[{datetime.now()}] Starting forecast job...")

    try:
        workflow = ForecastWorkflow(reader, forecaster, writer)
        results = workflow.run()
        print(f"[{datetime.now()}] Success! Generated {len(results)} forecasts")
    except Exception as e:
        print(f"[{datetime.now()}] Error: {e}")
        # Send alert email/Slack notification
        send_alert(f"Forecast job failed: {e}")

# Run every day at 2:00 AM
schedule.every().day.at("02:00").do(run_forecast_job)

while True:
    schedule.run_pending()
    time.sleep(60)
'''

print(automation_code)

print("\n" + "=" * 70)
print("Example complete!")
print("=" * 70)
