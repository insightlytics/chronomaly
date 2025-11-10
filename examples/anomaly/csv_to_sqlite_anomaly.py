"""
Anomaly Detection Workflow: CSV → Detect Anomalies → SQLite

This example shows how to:
1. Read forecast data from CSV
2. Read actual data from CSV
3. Detect anomalies by comparing forecast vs actual
4. Write anomaly results to SQLite database

Use Case: Daily anomaly detection with file-based inputs

Requirements:
    pip install pandas

Usage:
    python examples/anomaly/csv_to_sqlite_anomaly.py
"""

import pandas as pd
import sqlite3
from datetime import datetime

print("""
╔══════════════════════════════════════════════════════════════════════╗
║      ANOMALY DETECTION: CSV Forecast + CSV Actual → SQLite          ║
║                                                                      ║
║  Pipeline: CSV Files → Anomaly Detector → SQLite Database           ║
╚══════════════════════════════════════════════════════════════════════╝
""")

# Create sample forecast data
def create_forecast_csv():
    """Create sample forecast data with quantiles."""
    data = pd.DataFrame({
        'date': [datetime(2024, 11, 10)],
        'desktop_organic': ['1000|900|920|950|975|1000|1025|1050|1080|1100'],
        'desktop_paid': ['500|450|465|480|490|500|510|525|540|550'],
        'mobile_organic': ['800|700|720|750|775|800|825|850|880|900'],
        'mobile_paid': ['300|250|265|280|290|300|310|325|340|350']
    })

    data.to_csv('/tmp/forecast.csv', index=False)
    print("✓ Created forecast data: /tmp/forecast.csv")
    return data


# Create sample actual data
def create_actual_csv():
    """Create sample actual data with anomalies."""
    data = pd.DataFrame({
        'date': [datetime(2024, 11, 10)] * 4,
        'platform': ['desktop', 'desktop', 'mobile', 'mobile'],
        'channel': ['organic', 'paid', 'organic', 'paid'],
        'sessions': [950, 600, 650, 290]  # paid anomalies: above, below
    })

    data.to_csv('/tmp/actual.csv', index=False)
    print("✓ Created actual data: /tmp/actual.csv")
    return data


print("\n📋 WORKFLOW CONFIGURATION")
print("=" * 70)
print("Forecast Source: /tmp/forecast.csv (pivot format)")
print("Actual Source:   /tmp/actual.csv (raw format)")
print("Output:          /tmp/anomalies.db (anomalies table)")
print("Confidence:      80% (q10 to q90)")
print()

# Create sample data
forecast_data = create_forecast_csv()
actual_data = create_actual_csv()

print("\n📊 FORECAST DATA (with quantiles)")
print("=" * 70)
print(forecast_data.to_string(index=False))

print("\n📊 ACTUAL DATA")
print("=" * 70)
print(actual_data.to_string(index=False))

print("\n\n🔧 WORKFLOW CODE")
print("=" * 70)

workflow_code = '''
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter
from chronomaly.infrastructure.anomaly_detectors import ForecastActualAnomalyDetector
from chronomaly.infrastructure.transformers import DataTransformer

# Step 1: Configure forecast reader
forecast_reader = CSVDataReader(
    file_path='/tmp/forecast.csv',
    date_column='date'
)

# Step 2: Configure actual reader
actual_reader = CSVDataReader(
    file_path='/tmp/actual.csv',
    date_column='date'
)

# Step 3: Configure transformer (to pivot actual data)
transformer = DataTransformer(
    index='date',
    columns=['platform', 'channel'],
    values='sessions'
)

# Step 4: Configure anomaly detector
detector = ForecastActualAnomalyDetector(
    transformer=transformer,
    date_column='date',
    dimension_names=['platform', 'channel'],
    lower_quantile_idx=1,   # q10 (10th percentile)
    upper_quantile_idx=9    # q90 (90th percentile)
)

# Step 5: Configure writer
writer = SQLiteDataWriter(
    database_path='/tmp/anomalies.db',
    table_name='anomalies',
    if_exists='replace'
)

# Step 6: Create and run workflow
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=writer
)

# Run anomaly detection
results = workflow.run()

print(f"\\n✓ Anomaly detection complete!")
print(f"  Total metrics analyzed: {len(results)}")
print(f"  Saved to: /tmp/anomalies.db")
'''

print(workflow_code)

print("\n\n📈 EXAMPLE OUTPUT")
print("=" * 70)

# Simulate expected output
expected_output = pd.DataFrame({
    'date': [datetime(2024, 11, 10)] * 4,
    'platform': ['desktop', 'desktop', 'mobile', 'mobile'],
    'channel': ['organic', 'paid', 'organic', 'paid'],
    'actual': [950, 600, 650, 290],
    'forecast': [1000, 500, 800, 300],
    'lower_bound': [900, 450, 700, 250],
    'upper_bound': [1100, 550, 900, 350],
    'status': ['IN_RANGE', 'ABOVE_UPPER', 'BELOW_LOWER', 'IN_RANGE'],
    'deviation_pct': [0.0, 9.09, 7.14, 0.0]
})

print(expected_output.to_string(index=False))

print("\n\n🔍 QUERY RESULTS")
print("=" * 70)
print("""
# Query only anomalies
sqlite3 /tmp/anomalies.db "
  SELECT * FROM anomalies
  WHERE status IN ('ABOVE_UPPER', 'BELOW_LOWER')
"

# Or with pandas
import sqlite3
import pandas as pd

conn = sqlite3.connect('/tmp/anomalies.db')
anomalies = pd.read_sql(
    "SELECT * FROM anomalies WHERE status != 'IN_RANGE'",
    conn
)
conn.close()

print(f"Found {len(anomalies)} anomalies:")
print(anomalies)
""")

print("\n\n💡 UNDERSTANDING THE OUTPUT")
print("=" * 70)
print("""
Status Types:
- IN_RANGE:     Actual value within confidence interval [q10, q90]
- BELOW_LOWER:  Actual < q10 (lower than expected)
- ABOVE_UPPER:  Actual > q90 (higher than expected)
- NO_FORECAST:  No valid forecast available

Deviation Percentage:
- How far the actual is from the confidence bound
- BELOW_LOWER: ((q10 - actual) / q10) * 100
- ABOVE_UPPER: ((actual - q90) / q90) * 100

Example:
- desktop_paid: actual=600, q90=550
- Deviation: ((600-550)/550)*100 = 9.09%
- This means actual is 9.09% higher than upper bound
""")

print("\n\n🎯 NEXT STEPS")
print("=" * 70)
print("""
1. Run this example to see basic anomaly detection

2. Add filters for better results:
   python examples/advanced/anomaly_with_filters.py

3. Customize confidence intervals:
   python examples/advanced/custom_confidence_intervals.py

4. Set up alerting:
   - Email alerts for critical anomalies
   - Slack notifications
   - Dashboard integration
""")

print("\n" + "=" * 70)
print("Example complete! Run the code above to detect anomalies.")
print("=" * 70)
