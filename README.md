# Chronomaly

**Chronomaly** is a flexible and extensible Python library for time series forecasting and anomaly detection using Google TimesFM.

## Table of Contents

- [Problem / Motivation](#problem--motivation)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Forecast Workflow](#forecast-workflow)
  - [Anomaly Detection Workflow](#anomaly-detection-workflow)
  - [Transformers](#transformers)
  - [Data Sources](#data-sources)
  - [Notification System](#notification-system)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)
- [Contact / Support](#contact--support)
- [Roadmap](#roadmap)

---

## Problem / Motivation

Time series forecasting and anomaly detection are critical needs in modern data analytics. However:

- **Complexity**: Setting up and managing powerful forecasting models (e.g., Google TimesFM) is technically challenging
- **Data Integration**: Reading from and writing to different sources (BigQuery, SQLite, CSV, APIs) requires repetitive code
- **Lack of Flexibility**: Most solutions are not flexible enough for data transformations, filtering, and formatting
- **Anomaly Detection**: Comparing forecasted values with actual values to detect anomalies is a manual process

**Chronomaly** is designed to solve these problems:

- Provides powerful forecasts using Google's state-of-the-art TimesFM model
- Offers ready-to-use reader/writer implementations for multiple data sources
- Supports flexible data transformations with a pipeline-based architecture
- Automatically detects anomalies by comparing forecast and actual data
- Easily extensible thanks to its modular design

---

## Features

- **Google TimesFM Integration**: State-of-the-art time series forecasting model support (TimesFM 2.5-200M)
- **Multiple Data Sources**:
  - Readers: DataFrame, CSV, SQLite, BigQuery
  - Writers: SQLite, BigQuery
  - Extensible reader/writer architecture
- **Flexible Workflow Orchestration**:
  - ForecastWorkflow: Data reading, transformation, forecasting, writing
  - AnomalyDetectionWorkflow: Forecast vs actual comparison
  - NotificationWorkflow: Multi-channel notification delivery with retry logic
- **Data Transformations**:
  - PivotTransformer: Converts long-format to wide-format data
  - Filters: DateRangeFilter, ValueFilter, CumulativeThresholdFilter
  - Formatters: ColumnFormatter (with percentage helper), ColumnSelector
  - Composable transformer pipeline at any component level
- **Anomaly Detection**: Quantile-based anomaly detection (BELOW_LOWER, IN_RANGE, ABOVE_UPPER)
- **Notification System**: Email notifications with HTML formatting and customizable filtering
- **Modular Architecture**: Each component can be used independently and is easily extensible
- **Type Safety**: Full type hints throughout the codebase
- **Security**: Built-in protections against path traversal and SQL injection

---

## Installation

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Basic Installation

```bash
# Clone the repository
git clone https://github.com/insightlytics/chronomaly.git
cd chronomaly

# Install core dependencies
pip install -r requirements.txt

# Install TimesFM from GitHub (required)
pip install git+https://github.com/google-research/timesfm.git

# Install Chronomaly in editable mode
pip install -e .
```

### Optional Dependencies

```bash
# For BigQuery support
pip install -e ".[bigquery]"

# For development tools (pytest, black, flake8)
pip install -e ".[dev]"

# TimesFM backend options
pip install -e ".[torch]"   # PyTorch backend (recommended)
pip install -e ".[flax]"    # Flax/JAX backend
pip install -e ".[xreg]"    # External regressors support

# All optional dependencies
pip install -e ".[all]"
```

---

## Quick Start

Here's a complete example showing forecasting and anomaly detection:

```python
from chronomaly.application.workflows import ForecastWorkflow, AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.data.readers import DataFrameDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter
from chronomaly.infrastructure.forecasters import TimesFMForecaster
from chronomaly.infrastructure.anomaly_detectors import ForecastActualAnomalyDetector
from chronomaly.infrastructure.transformers import PivotTransformer
from chronomaly.infrastructure.transformers.filters import ValueFilter

# Step 1: Generate Forecast
# ========================

# Load and pivot historical data
reader = CSVDataReader(
    file_path="data/historical.csv",
    date_column="date",
    transformers={
        'after': [
            PivotTransformer(
                index='date',
                columns=['platform', 'channel'],
                values='sessions'
            )
        ]
    }
)

# Configure forecaster
forecaster = TimesFMForecaster(frequency='D')

# Configure writer
writer = SQLiteDataWriter(
    db_path="output/forecasts.db",
    table_name="forecasts"
)

# Run forecast workflow
forecast_workflow = ForecastWorkflow(
    data_reader=reader,
    forecaster=forecaster,
    data_writer=writer
)

forecast_df = forecast_workflow.run(horizon=7)
print("Generated forecast for next 7 days")

# Step 2: Detect Anomalies
# ========================

# Load forecast results (from previous step)
forecast_reader = DataFrameDataReader(
    dataframe=forecast_df,
    date_column='date'
)

# Load actual data (today's actual values)
actual_reader = CSVDataReader(
    file_path="data/actuals.csv",
    date_column="date",
    transformers={
        'after': [
            PivotTransformer(
                index='date',
                columns=['platform', 'channel'],
                values='sessions'
            )
        ]
    }
)

# Configure anomaly detector
detector = ForecastActualAnomalyDetector(
    date_column='date',
    dimension_names=['platform', 'channel'],
    lower_quantile_idx=1,  # q10
    upper_quantile_idx=9,  # q90
    transformers={
        'after': [
            # Only keep anomalies (not IN_RANGE)
            ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER'], mode='include'),
            # Minimum 5% deviation
            ValueFilter('deviation_pct', min_value=0.05)
        ]
    }
)

# Configure writer
anomaly_writer = SQLiteDataWriter(
    db_path="output/anomalies.db",
    table_name="anomalies"
)

# Run anomaly detection workflow
anomaly_workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=anomaly_writer
)

anomalies_df = anomaly_workflow.run()
print(f"Detected {len(anomalies_df)} anomalies")
print(anomalies_df[['date', 'metric', 'status', 'deviation_pct']])
```

---

## Usage

### Forecast Workflow

ForecastWorkflow orchestrates data reading, transformation, forecast generation, and writing.

#### Example: Reading from CSV and Pivot Transformation

```python
from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter
from chronomaly.infrastructure.forecasters import TimesFMForecaster
from chronomaly.infrastructure.transformers import PivotTransformer

# CSV reader with pivot transformation applied after loading
reader = CSVDataReader(
    file_path="data/raw_data.csv",
    date_column="date",
    transformers={
        'after': [
            PivotTransformer(
                index='date',
                columns=['platform', 'channel'],  # Dimensions
                values='sessions'  # Value column
            )
        ]
    }
)

# SQLite writer
writer = SQLiteDataWriter(
    db_path="output/forecasts.db",
    table_name="forecasts"
)

# Forecaster
forecaster = TimesFMForecaster(frequency='D')

# Workflow (no transformer parameter - transformations are at component level)
workflow = ForecastWorkflow(
    data_reader=reader,
    forecaster=forecaster,
    data_writer=writer
)

# 7-day forecast
forecast_df = workflow.run(horizon=7)
```

#### Example: Reading from BigQuery

```python
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter

# BigQuery reader
reader = BigQueryDataReader(
    service_account_file="path/to/service-account.json",
    project="my-gcp-project",
    query="""
        SELECT date, metric_name, value
        FROM `project.dataset.table`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    """,
    date_column="date"
)

# BigQuery writer
writer = BigQueryDataWriter(
    service_account_file="path/to/service-account.json",
    project="my-gcp-project",
    dataset="my_dataset",
    table="forecasts",
    write_disposition="WRITE_APPEND"
)

# Create and run workflow
workflow = ForecastWorkflow(
    data_reader=reader,
    forecaster=forecaster,
    data_writer=writer
)

forecast_df = workflow.run(horizon=14)
```

### Anomaly Detection Workflow

AnomalyDetectionWorkflow detects anomalies by comparing forecasted values with actual values.

#### Example: Basic Anomaly Detection

```python
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter
from chronomaly.infrastructure.anomaly_detectors import ForecastActualAnomalyDetector
from chronomaly.infrastructure.transformers import PivotTransformer

# Forecast data reader (reads forecast results from previous workflow run)
forecast_reader = BigQueryDataReader(
    service_account_file="path/to/service-account.json",
    project="my-project",
    query="SELECT * FROM `project.dataset.forecasts` WHERE date = CURRENT_DATE()",
    date_column="date"
)

# Actual data reader (reads real/observed values to compare against forecasts)
# Note: Pivot transformation is applied after loading the data
actual_reader = BigQueryDataReader(
    service_account_file="path/to/service-account.json",
    project="my-project",
    query="""
        SELECT date, platform, channel, sessions
        FROM `project.dataset.actuals`
        WHERE date = CURRENT_DATE()
    """,
    date_column="date",
    transformers={
        'after': [
            PivotTransformer(
                index='date',
                columns=['platform', 'channel'],
                values='sessions'
            )
        ]
    }
)

# Anomaly writer
anomaly_writer = BigQueryDataWriter(
    service_account_file="path/to/service-account.json",
    project="my-project",
    dataset="analytics",
    table="anomalies"
)

# Anomaly detector (no transformer parameter - data is already pivoted by reader)
detector = ForecastActualAnomalyDetector(
    date_column='date',
    dimension_names=['platform', 'channel'],  # Split metric into these dimensions
    lower_quantile_idx=1,  # q10
    upper_quantile_idx=9   # q90
)

# Workflow
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=anomaly_writer
)

# Detect anomalies
anomalies_df = workflow.run()
print(anomalies_df[anomalies_df['status'] != 'IN_RANGE'])
```

#### Example: Anomaly Detection with Filtering and Formatting

```python
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.transformers.filters import (
    ValueFilter,
    CumulativeThresholdFilter
)
from chronomaly.infrastructure.transformers.formatters import ColumnFormatter

# Configure transformations at detector level (not workflow level)
detector = ForecastActualAnomalyDetector(
    date_column='date',
    dimension_names=['platform', 'channel'],
    lower_quantile_idx=1,
    upper_quantile_idx=9,
    transformers={
        'after': [
            # Filter only significant anomalies
            CumulativeThresholdFilter('forecast', threshold_pct=0.95),
            # Filter only anomalies (exclude IN_RANGE)
            ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER'], mode='include'),
            # Filter minimum deviation
            ValueFilter('deviation_pct', min_value=0.05),  # 5% minimum deviation
            # Percentage formatting using helper method
            ColumnFormatter.percentage(
                columns='deviation_pct',
                decimal_places=1,
                multiply_by_100=True  # Convert 0.05 → "5.0%"
            )
        ]
    }
)

# Workflow (transformations are handled by detector)
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=anomaly_writer
)

anomalies_df = workflow.run()
```

### Transformers

Chronomaly provides a flexible transformer system that can be applied at any component level. Transformers are organized by stage ('before' or 'after') and can be chained together.

#### Available Transformers

**PivotTransformer** - Convert long-format to wide-format data:
```python
from chronomaly.infrastructure.transformers import PivotTransformer

# Convert data from long format (date, dimension, value) to wide format (date × dimensions)
transformer = PivotTransformer(
    index='date',                    # Row index (typically date)
    columns=['platform', 'channel'],  # Columns to pivot (dimensions)
    values='sessions'                # Value column
)
```

**DateRangeFilter** - Filter by date ranges:
```python
from chronomaly.infrastructure.transformers.filters import DateRangeFilter

# Filter data to specific date range
transformer = DateRangeFilter(
    start_date='2024-01-01',  # Optional, inclusive
    end_date='2024-12-31',    # Optional, inclusive
    date_column='date'        # Optional, uses index if None
)
```

**ValueFilter** - Filter by categorical values or numeric thresholds:
```python
from chronomaly.infrastructure.transformers.filters import ValueFilter

# Include only specific values
transformer = ValueFilter(
    column='status',
    values=['BELOW_LOWER', 'ABOVE_UPPER'],
    mode='include'  # or 'exclude'
)

# Filter by numeric thresholds
transformer = ValueFilter(
    column='deviation_pct',
    min_value=0.05,  # 5% minimum
    max_value=0.50   # 50% maximum (optional)
)
```

**CumulativeThresholdFilter** - Keep top N% by cumulative value:
```python
from chronomaly.infrastructure.transformers.filters import CumulativeThresholdFilter

# Keep top metrics that account for 95% of total value
transformer = CumulativeThresholdFilter(
    column='forecast',
    threshold_pct=0.95  # 0.95 = 95%
)
```

**ColumnFormatter** - Apply custom formatting functions:
```python
from chronomaly.infrastructure.transformers.formatters import ColumnFormatter

# Custom formatting
transformer = ColumnFormatter(
    formatters={
        'forecast': lambda x: f"{x:.2f}",
        'actual': lambda x: f"{x:.2f}"
    }
)

# Percentage formatting helper
transformer = ColumnFormatter.percentage(
    columns='deviation_pct',
    decimal_places=1,
    multiply_by_100=True  # Convert 0.05 → "5.0%"
)
```

**ColumnSelector** - Select or drop specific columns:
```python
from chronomaly.infrastructure.transformers.formatters import ColumnSelector

# Keep only specific columns
transformer = ColumnSelector(
    columns=['date', 'metric', 'forecast', 'actual', 'status'],
    mode='include'  # or 'exclude'
)
```

#### Using Transformers

Transformers can be applied at any component level using the `transformers` parameter:

```python
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.forecasters import TimesFMForecaster
from chronomaly.infrastructure.transformers import PivotTransformer
from chronomaly.infrastructure.transformers.filters import ValueFilter

# Apply transformers at reader level
reader = CSVDataReader(
    file_path="data.csv",
    date_column="date",
    transformers={
        'after': [
            PivotTransformer(index='date', columns='dimension', values='value'),
            ValueFilter(column='dimension', values=['important_metric'], mode='include')
        ]
    }
)

# Apply transformers at forecaster level
forecaster = TimesFMForecaster(
    frequency='D',
    transformers={
        'before': [ValueFilter(column='value', min_value=0)],  # Clean negatives before forecast
        'after': [ColumnFormatter.percentage(columns='forecast', decimal_places=2)]  # Format output
    }
)

# Transformers are executed in the order they appear in the list
```

### Data Sources

Chronomaly supports various data sources:

#### In-Memory DataFrame

```python
from chronomaly.infrastructure.data.readers import DataFrameDataReader
import pandas as pd

# Wrap an existing DataFrame (useful for chaining workflows)
df = pd.DataFrame({'date': [...], 'value': [...]})
reader = DataFrameDataReader(
    dataframe=df,
    date_column="date",
    transformers={'after': [PivotTransformer(...)]}  # Optional transformations
)
```

#### CSV Files

```python
from chronomaly.infrastructure.data.readers.files import CSVDataReader

# CSV reader with built-in path traversal protection
reader = CSVDataReader(
    file_path="data/input.csv",
    date_column="date",
    transformers={'after': [PivotTransformer(...)]}  # Optional transformations
)

# Note: CSV writer is not yet implemented. Use SQLite or BigQuery writers for output.
```

#### SQLite

```python
from chronomaly.infrastructure.data.readers.databases import SQLiteDataReader
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter

# SQLite reader with SQL injection protection
reader = SQLiteDataReader(
    database_path="data/mydb.sqlite",
    query="SELECT * FROM time_series WHERE date > ?",
    date_column="date",
    transformers={'after': [PivotTransformer(...)]}  # Optional transformations
)

# SQLite writer (creates tables if they don't exist)
writer = SQLiteDataWriter(
    db_path="output/forecasts.db",
    table_name="forecasts",
    transformers={'before': [ColumnSelector(...)]}  # Optional transformations
)
```

#### BigQuery

```python
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter

# BigQuery reader (supports both SQL queries and table names)
reader = BigQueryDataReader(
    service_account_file="path/to/credentials.json",
    project="my-gcp-project",
    query="SELECT * FROM `dataset.table` WHERE date > '2024-01-01'",
    date_column="date",
    transformers={'after': [PivotTransformer(...)]}  # Optional transformations
)

# BigQuery writer with write disposition control
writer = BigQueryDataWriter(
    service_account_file="path/to/credentials.json",
    project="my-gcp-project",
    dataset="analytics",
    table="forecasts",
    write_disposition="WRITE_APPEND",  # or "WRITE_TRUNCATE"
    transformers={'before': [ColumnSelector(...)]}  # Optional transformations
)
```

### Notification System

Send notifications when anomalies are detected:

```python
from chronomaly.application.workflows import NotificationWorkflow
from chronomaly.infrastructure.notifiers import EmailNotifier
from chronomaly.infrastructure.transformers.filters import ValueFilter

# Configure email notifier (reads SMTP settings from environment variables)
email_notifier = EmailNotifier(
    to=["data-team@example.com", "alerts@example.com"],  # Single email or list
    transformers={
        'before': [
            # Only notify for critical anomalies
            ValueFilter('status', values=['BELOW_LOWER', 'ABOVE_UPPER'], mode='include'),
            ValueFilter('deviation_pct', min_value=0.10)  # 10% minimum deviation
        ]
    }
)

# Create notification workflow
notification_workflow = NotificationWorkflow(
    anomaly_dataframe=anomalies_df,
    notifiers=[email_notifier]  # Can have multiple notifiers
)

# Send notifications
notification_workflow.run()
```

**Email Configuration (.env file):**
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=alerts@example.com  # Optional, defaults to SMTP_USER
EMAIL_SUBJECT=Chronomaly Alert: Anomalies Detected  # Optional
```

---

## Architecture

Chronomaly follows Clean Architecture principles with a layered structure:

```
chronomaly/
├── __init__.py           # Package initialization (loads .env)
├── application/          # Application layer (workflows)
│   ├── __init__.py       # Application layer exports
│   └── workflows/
│       ├── __init__.py   # Workflow exports
│       ├── forecast_workflow.py        # ForecastWorkflow
│       ├── anomaly_detection_workflow.py  # AnomalyDetectionWorkflow
│       └── notification_workflow.py    # NotificationWorkflow
├── infrastructure/       # Infrastructure layer (implementations)
│   ├── __init__.py       # Infrastructure layer exports
│   ├── forecasters/      # Forecasting models
│   │   ├── __init__.py   # Forecaster exports
│   │   ├── base.py       # Abstract Forecaster class
│   │   └── timesfm.py    # Google TimesFM implementation
│   ├── anomaly_detectors/  # Anomaly detection algorithms
│   │   ├── __init__.py   # Anomaly detector exports
│   │   ├── base.py       # Abstract AnomalyDetector class
│   │   └── forecast_actual.py  # Quantile-based anomaly detection
│   ├── transformers/     # Data transformations
│   │   ├── __init__.py   # Transformer exports
│   │   ├── pivot.py      # PivotTransformer (long → wide format)
│   │   ├── filters/      # Data filtering
│   │   │   ├── __init__.py   # Filter exports
│   │   │   ├── base.py   # Abstract DataFrameFilter class
│   │   │   ├── date_range_filter.py  # DateRangeFilter
│   │   │   ├── value_filter.py       # ValueFilter
│   │   │   └── cumulative_threshold.py  # CumulativeThresholdFilter
│   │   └── formatters/   # Data formatting
│   │       ├── __init__.py   # Formatter exports
│   │       ├── base.py   # Abstract DataFrameFormatter class
│   │       ├── column_formatter.py   # ColumnFormatter
│   │       └── column_selector.py    # ColumnSelector
│   ├── data/             # Data reading/writing
│   │   ├── __init__.py   # Data layer exports
│   │   ├── readers/
│   │   │   ├── __init__.py   # Reader exports
│   │   │   ├── base.py       # Abstract DataReader class
│   │   │   ├── dataframe_reader.py  # DataFrameDataReader
│   │   │   ├── files/        # File-based readers
│   │   │   │   ├── __init__.py   # File reader exports
│   │   │   │   └── csv.py    # CSVDataReader
│   │   │   ├── databases/    # Database readers
│   │   │   │   ├── __init__.py   # Database reader exports
│   │   │   │   ├── sqlite.py     # SQLiteDataReader
│   │   │   │   └── bigquery.py   # BigQueryDataReader
│   │   │   └── apis/         # API integrations (extensible)
│   │   │       └── __init__.py   # API reader exports
│   │   └── writers/
│   │       ├── __init__.py   # Writer exports
│   │       ├── base.py       # Abstract DataWriter class
│   │       └── databases/
│   │           ├── __init__.py   # Database writer exports
│   │           ├── sqlite.py     # SQLiteDataWriter
│   │           └── bigquery.py   # BigQueryDataWriter
│   ├── notifiers/        # Notification system
│   │   ├── __init__.py   # Notifier exports
│   │   ├── base.py       # Abstract Notifier class
│   │   └── email.py      # EmailNotifier
│   └── visualizers/      # Visualization components (planned)
│       └── __init__.py   # Visualizer exports
└── shared/               # Shared utilities
    ├── __init__.py       # Shared utilities exports
    └── mixins.py         # TransformableMixin (transformer application logic)
```

### Core Components

- **Workflows**: Orchestrate business workflows
  - `ForecastWorkflow`: Load → Forecast → Write pipeline
  - `AnomalyDetectionWorkflow`: Load Forecast → Load Actual → Detect → Write pipeline
  - `NotificationWorkflow`: Prepare → Send notifications pipeline
- **Forecasters**: Forecasting model implementations
  - `TimesFMForecaster`: Google TimesFM 2.5-200M model with quantile forecasts
- **AnomalyDetectors**: Anomaly detection algorithms
  - `ForecastActualAnomalyDetector`: Quantile-based comparison (q10/q90 default)
- **Transformers**: Composable data transformations
  - `PivotTransformer`: Convert long-format to wide-format
  - **Filters**: `DateRangeFilter`, `ValueFilter`, `CumulativeThresholdFilter`
  - **Formatters**: `ColumnFormatter`, `ColumnSelector`
- **DataReaders**: Data input sources
  - `DataFrameDataReader`: In-memory DataFrames
  - `CSVDataReader`: CSV files with path traversal protection
  - `SQLiteDataReader`: SQLite databases with SQL injection protection
  - `BigQueryDataReader`: Google BigQuery
- **DataWriters**: Data output destinations
  - `SQLiteDataWriter`: SQLite databases
  - `BigQueryDataWriter`: Google BigQuery
- **Notifiers**: Notification channels
  - `EmailNotifier`: HTML email notifications with SMTP
- **Visualizers**: Visualization components (planned)
  - Infrastructure ready for future visualization implementations
- **Shared Utilities**:
  - `TransformableMixin`: Enables transformer application at any component level

### Design Patterns

**TransformableMixin Pattern**: Components inherit `TransformableMixin` to support composable transformations at specific stages ('before' or 'after' main operations). Transformers are configured at the component level, not the workflow level.

**Abstract Base Classes**: All major component types use ABCs to define interfaces, ensuring consistency and extensibility.

**Layered Architecture**: Clear separation between orchestration (application layer), implementations (infrastructure layer), and utilities (shared layer).

---

## Contributing

We welcome contributions! Here's how you can contribute:

### Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Commit your changes: `git commit -m 'feat: Add new feature'`
4. Push your branch: `git push origin feature/new-feature`
5. Open a Pull Request

### Coding Standards

- **Type Hints**: Use type hints in all functions
- **Docstrings**: Add docstrings for every class and function
- **Testing**: Write tests for new features
- **Code Style**: Format code with Black and flake8

```bash
# Run tests
pytest

# Code formatting
black chronomaly/

# Linting
flake8 chronomaly/
```

### Commit Messages

Use Conventional Commits format:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Add/fix tests
- `chore:` Maintenance tasks

### Adding New Data Sources

To add a new data source:

1. Inherit from `DataReader` or `DataWriter` base class
2. Implement the `load()` or `write()` method
3. Write tests
4. Add documentation

Example:

```python
from chronomaly.infrastructure.data.readers.base import DataReader
import pandas as pd

class MyCustomReader(DataReader):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def load(self) -> pd.DataFrame:
        # Your implementation
        pass
```

---

## License

This project is licensed under the [Apache License 2.0](LICENSE).

---

## Contact / Support

### Issue Reporting

If you found a bug or have a suggestion:

- **GitHub Issues**: [https://github.com/insightlytics/chronomaly/issues](https://github.com/insightlytics/chronomaly/issues)
- When opening an issue, please:
  - Clearly describe the problem
  - Include steps to reproduce the error
  - Specify expected and actual behavior
  - Provide Python version and OS information

### Questions and Discussions

- **GitHub Discussions**: For general questions and discussions
- **Pull Requests**: For code contributions

### Documentation

- **GitHub Repository**: [https://github.com/insightlytics/chronomaly](https://github.com/insightlytics/chronomaly)
- In-code docstrings and type hints provide detailed usage information

---

**Build powerful time series forecasts and anomaly detection with Chronomaly!**
