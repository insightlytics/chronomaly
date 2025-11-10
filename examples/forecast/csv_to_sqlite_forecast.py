"""
Forecast Workflow: CSV → Forecast → SQLite

This example shows how to:
1. Read historical data from CSV
2. Generate forecasts using TimesFM
3. Write forecast results to SQLite database

Use Case: Store forecasts in a database for later anomaly detection

Requirements:
    pip install pandas timesfm-torch

Usage:
    python examples/forecast/csv_to_sqlite_forecast.py
"""

import pandas as pd
from datetime import datetime, timedelta

# NOTE: This example is informational only
# TimesFM requires additional dependencies and model files
# See: https://github.com/google-research/timesfm

print("""
╔══════════════════════════════════════════════════════════════════════╗
║           FORECAST WORKFLOW: CSV → SQLite                            ║
║                                                                      ║
║  Pipeline: CSV File → TimesFM Forecaster → SQLite Database          ║
╚══════════════════════════════════════════════════════════════════════╝
""")

# Create sample historical data
def create_sample_data():
    """Create sample historical time series data."""
    dates = pd.date_range(start='2024-01-01', periods=90, freq='D')

    data = pd.DataFrame({
        'date': dates,
        'metric': 'desktop_organic',
        'value': [100 + i * 2 + (i % 7) * 10 for i in range(90)]
    })

    data.to_csv('/tmp/historical_data.csv', index=False)
    print(f"✓ Created sample data: /tmp/historical_data.csv")
    print(f"  Rows: {len(data)}")
    print(f"  Date range: {data['date'].min()} to {data['date'].max()}")
    return data


# Display configuration
print("\n📋 WORKFLOW CONFIGURATION")
print("=" * 70)
print("Data Source:    CSV file (/tmp/historical_data.csv)")
print("Forecaster:     TimesFM (Google Research)")
print("Output:         SQLite database (/tmp/forecasts.db)")
print("Horizon:        7 days ahead")
print("Quantiles:      10 quantiles (q10, q20, ..., q90)")
print()

# Create sample data
sample_data = create_sample_data()

print("\n📊 SAMPLE DATA PREVIEW")
print("=" * 70)
print(sample_data.tail(10).to_string(index=False))

print("\n\n🔧 WORKFLOW CODE")
print("=" * 70)

workflow_code = '''
from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter
from chronomaly.infrastructure.forecasters import TimesFMForecaster

# Step 1: Configure data reader
reader = CSVDataReader(
    file_path='/tmp/historical_data.csv',
    date_column='date'
)

# Step 2: Configure forecaster
forecaster = TimesFMForecaster(
    context_length=90,        # Use 90 days of history
    horizon=7,                # Forecast 7 days ahead
    freq='D',                 # Daily frequency
    num_quantiles=10          # Generate 10 quantiles
)

# Step 3: Configure writer
writer = SQLiteDataWriter(
    database_path='/tmp/forecasts.db',
    table_name='forecasts',
    if_exists='replace'
)

# Step 4: Create and run workflow
workflow = ForecastWorkflow(
    data_reader=reader,
    forecaster=forecaster,
    data_writer=writer
)

# Run the forecast
results = workflow.run()

print(f"✓ Forecast complete!")
print(f"  Generated {len(results)} forecast rows")
print(f"  Saved to: /tmp/forecasts.db")
'''

print(workflow_code)

print("\n\n📈 EXPECTED OUTPUT FORMAT")
print("=" * 70)
print("""
Forecast results will be saved to SQLite with columns:

| date       | metric          | forecast_value                              |
|------------|-----------------|---------------------------------------------|
| 2024-04-01 | desktop_organic | 280|260|265|270|275|280|285|290|295|300 |
| 2024-04-02 | desktop_organic | 282|262|267|272|277|282|287|292|297|302 |
| ...        | ...             | ...                                         |

Format: point|q10|q20|q30|q40|q50|q60|q70|q80|q90

This format is optimized for:
- Anomaly detection (using q10 and q90 as confidence bounds)
- Uncertainty quantification
- Risk assessment
""")

print("\n\n💡 NEXT STEPS")
print("=" * 70)
print("""
1. Install TimesFM:
   pip install timesfm-torch

2. Run this workflow to generate forecasts

3. Use forecasts for anomaly detection:
   python examples/anomaly/sqlite_anomaly.py

4. Or query forecasts directly:
   sqlite3 /tmp/forecasts.db "SELECT * FROM forecasts LIMIT 5"
""")

print("\n\n⚠️  NOTE")
print("=" * 70)
print("""
TimesFM requires:
- PyTorch installation
- Pre-trained model weights
- GPU recommended for large datasets

For a simpler starting point, see:
- csv_to_csv_forecast.py (no external dependencies)
""")

print("\n" + "=" * 70)
print("Example complete!")
print("=" * 70)
