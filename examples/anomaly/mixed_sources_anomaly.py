"""
Anomaly Detection: Mixed Data Sources

This example shows how to:
1. Read forecast from SQLite database
2. Read actual from CSV file
3. Detect anomalies
4. Write results to SQLite

Use Case: Forecast stored in DB, actual data arrives as CSV files daily

Requirements:
    pip install pandas

Usage:
    python examples/anomaly/mixed_sources_anomaly.py
"""

import pandas as pd
import sqlite3
from datetime import datetime

print("""
╔══════════════════════════════════════════════════════════════════════╗
║        ANOMALY DETECTION: Mixed Data Sources                         ║
║                                                                      ║
║  SQLite Forecast + CSV Actual → Anomaly Detection → SQLite          ║
╚══════════════════════════════════════════════════════════════════════╝
""")

# Create forecast database
def create_forecast_database():
    """Create SQLite database with forecasts."""
    forecast_data = pd.DataFrame({
        'date': [datetime(2024, 11, 10)],
        'desktop_organic': ['2000|1800|1850|1900|1950|2000|2050|2100|2150|2200'],
        'desktop_paid': ['1000|900|920|950|975|1000|1025|1050|1080|1100'],
        'mobile_organic': ['1500|1300|1350|1400|1450|1500|1550|1600|1650|1700']
    })

    conn = sqlite3.connect('/tmp/forecasts.db')
    forecast_data.to_sql('forecasts', conn, if_exists='replace', index=False)
    conn.close()

    print("✓ Created forecast database: /tmp/forecasts.db")
    return forecast_data


# Create actual CSV
def create_actual_csv():
    """Create CSV file with actual data."""
    actual_data = pd.DataFrame({
        'timestamp': [datetime(2024, 11, 10)] * 3,
        'platform': ['desktop', 'desktop', 'mobile'],
        'channel': ['organic', 'paid', 'organic'],
        'sessions': [1900, 1150, 1200]  # paid is anomaly (above)
    })

    actual_data.to_csv('/tmp/daily_actuals.csv', index=False)
    print("✓ Created actual CSV: /tmp/daily_actuals.csv")
    return actual_data


print("\n📋 WORKFLOW CONFIGURATION")
print("=" * 70)
print("Forecast:  SQLite (/tmp/forecasts.db)")
print("Actual:    CSV (/tmp/daily_actuals.csv)")
print("Output:    SQLite (/tmp/anomaly_results.db)")
print("Use Case:  Daily batch processing")
print()

forecast = create_forecast_database()
actual = create_actual_csv()

print("\n📊 FORECAST DATA (from SQLite)")
print("=" * 70)
print(forecast.to_string(index=False))

print("\n📊 ACTUAL DATA (from CSV)")
print("=" * 70)
print(actual.to_string(index=False))

print("\n\n🔧 WORKFLOW CODE")
print("=" * 70)

workflow_code = '''
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.data.readers.databases import SQLiteDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter
from chronomaly.infrastructure.anomaly_detectors import ForecastActualAnomalyDetector
from chronomaly.infrastructure.transformers import DataTransformer

# Step 1: Configure forecast reader (SQLite)
forecast_reader = SQLiteDataReader(
    database_path='/tmp/forecasts.db',
    table_name='forecasts'
)

# Step 2: Configure actual reader (CSV)
actual_reader = CSVDataReader(
    file_path='/tmp/daily_actuals.csv',
    date_column='timestamp'  # Note: different column name
)

# Step 3: Configure transformer
transformer = DataTransformer(
    index='timestamp',  # Must match actual data column
    columns=['platform', 'channel'],
    values='sessions'
)

# Step 4: Configure detector
detector = ForecastActualAnomalyDetector(
    transformer=transformer,
    date_column='date',  # Forecast uses 'date'
    dimension_names=['platform', 'channel'],
    lower_quantile_idx=1,   # q10
    upper_quantile_idx=9    # q90
)

# Step 5: Configure writer
writer = SQLiteDataWriter(
    database_path='/tmp/anomaly_results.db',
    table_name='daily_anomalies',
    if_exists='append'  # Append daily results
)

# Step 6: Create and run workflow
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=writer
)

# Run detection
results = workflow.run()

print(f"\\n✓ Detection complete!")
print(f"  Metrics analyzed: {len(results)}")
print(f"  Results: /tmp/anomaly_results.db")
'''

print(workflow_code)

print("\n\n🔄 DAILY AUTOMATION PATTERN")
print("=" * 70)

automation_code = '''
#!/usr/bin/env python3
"""
daily_anomaly_check.py - Run daily anomaly detection

Schedule with cron:
0 8 * * * /path/to/daily_anomaly_check.py
"""

import sys
from datetime import datetime
from chronomaly.application.workflows import AnomalyDetectionWorkflow

def main():
    """Daily anomaly detection job."""
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"[{today}] Starting anomaly detection...")

    try:
        # Configure workflow (same as above)
        workflow = AnomalyDetectionWorkflow(...)

        # Run detection
        results = workflow.run()

        # Check for critical anomalies
        critical = results[
            (results['status'].isin(['BELOW_LOWER', 'ABOVE_UPPER'])) &
            (results['deviation_pct'] > 20)  # >20% deviation
        ]

        if len(critical) > 0:
            print(f"⚠️  {len(critical)} critical anomalies detected!")
            send_alert(critical)  # Email/Slack notification
        else:
            print(f"✓ No critical anomalies. {len(results)} metrics checked.")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        send_error_alert(str(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''

print(automation_code)

print("\n\n💡 REAL-WORLD SCENARIO")
print("=" * 70)
print("""
Day 1: Generate Forecasts
- Run forecast workflow at night
- Store forecasts in /tmp/forecasts.db

Day 2: Detect Anomalies
- Actual data arrives as CSV from data pipeline
- Run this anomaly detection workflow
- Results appended to /tmp/anomaly_results.db
- Critical anomalies trigger alerts

Day 3: Review & Investigate
- Query anomaly database for patterns
- Investigate root causes
- Update forecast models if needed

Repeat daily...
""")

print("\n\n🔍 ADVANCED QUERIES")
print("=" * 70)
print("""
# Find all anomalies from last 7 days
sqlite3 /tmp/anomaly_results.db "
  SELECT date, platform, channel, status, deviation_pct
  FROM daily_anomalies
  WHERE status IN ('ABOVE_UPPER', 'BELOW_LOWER')
    AND date >= date('now', '-7 days')
  ORDER BY deviation_pct DESC
"

# Count anomalies by platform
sqlite3 /tmp/anomaly_results.db "
  SELECT platform, status, COUNT(*) as count
  FROM daily_anomalies
  WHERE status != 'IN_RANGE'
  GROUP BY platform, status
  ORDER BY count DESC
"

# Top 10 biggest deviations
sqlite3 /tmp/anomaly_results.db "
  SELECT *
  FROM daily_anomalies
  WHERE status != 'IN_RANGE'
  ORDER BY deviation_pct DESC
  LIMIT 10
"
""")

print("\n" + "=" * 70)
print("Example complete! This pattern works great for:")
print("- Daily batch processing")
print("- Mixed data sources")
print("- Incremental anomaly detection")
print("=" * 70)
