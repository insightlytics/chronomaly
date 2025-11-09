# Chronomaly

A flexible and extensible Python library for time series forecasting using Google TimesFM.

## Features

- **Multiple Data Sources**: Load data from CSV, SQLite, and BigQuery
- **Flexible Transformations**: Built-in pivot functionality for time series data
- **TimesFM Integration**: Leverage Google's powerful TimesFM model for forecasting
- **Quantile Forecasts**: Support for both point and quantile predictions
- **Extensible Architecture**: Easy to add new data sources, forecasters, or output formats
- **Type-Safe Design**: Built with abstract base classes for clear interfaces

## Installation

### Python Version Compatibility

**Requires Python 3.13+**

TimesFM is installed directly from GitHub source for compatibility.

### Installation Steps

```bash
# Clone the repository
git clone https://github.com/insightlytics/chronomaly.git
cd chronomaly

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install TimesFM from GitHub
pip install git+https://github.com/google-research/timesfm.git

# Install Chronomaly in editable mode
pip install -e .
```

### Optional Installation Extras

```bash
# For BigQuery support
pip install -e ".[bigquery]"

# For TimesFM Flax/JAX backend (alternative to PyTorch)
pip install -e ".[flax]"

# For TimesFM cross-regression features
pip install -e ".[xreg]"

# For development tools (pytest, black, flake8)
pip install -e ".[dev]"

# For all features (BigQuery + dev tools)
pip install -e ".[all]"
```

### About TimesFM Backend Options

TimesFM supports multiple backend implementations and features:

- **torch** (PyTorch): ✅ **Default backend** - Already included in Chronomaly's base dependencies
  - No extra installation needed
  - Works out of the box

- **flax** (Flax/JAX): Alternative backend for TimesFM
  - Install with: `pip install -e ".[flax]"`
  - Includes: flax, optax, einshape, orbax-checkpoint, jaxtyping, jax[cuda]
  - Use if you prefer JAX/Flax over PyTorch

- **xreg**: Cross-regression features for TimesFM
  - Install with: `pip install -e ".[xreg]"`
  - Includes: jax[cuda], scikit-learn
  - Adds additional regression capabilities

**Note:** Chronomaly uses the PyTorch backend by default. Only install `flax` or `xreg` extras if you specifically need those TimesFM features.

### Requirements

- Python >= 3.13
- pandas >= 2.0.0
- numpy >= 1.24.0
- torch >= 2.0.0
- timesfm (latest from GitHub)
- google-cloud-bigquery >= 3.10.0 (optional, for BigQuery support)
- At least 16GB RAM recommended for TimesFM

## Quick Start

### Basic Example (CSV to SQLite)

```python
from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.forecasters import TimesFMForecaster
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter

# Configure data source
data_reader = CSVDataReader(
    file_path="data/sales.csv",
    date_column="date"
)

# Configure transformer
transformer = DataTransformer(
    index="date",
    columns="product_id",
    values="sales"
)

# Configure forecaster
forecaster = TimesFMForecaster()

# Configure output
data_writer = SQLiteDataWriter(
    database_path="output/forecasts.db",
    table_name="sales_forecast"
)

# Create and run workflow
workflow = ForecastWorkflow(
    data_reader=data_reader,
    forecaster=forecaster,
    data_writer=data_writer,
    transformer=transformer
)

# Generate 28-day forecast
forecast_df = workflow.run(horizon=28)
```

## Architecture

The library follows a modular architecture with Strategy Pattern:

```
ForecastWorkflow (Orchestrator)
├── DataReader (ABC)
│   ├── CSVDataReader
│   ├── SQLiteDataReader
│   └── BigQueryDataReader
├── DataTransformer
├── Forecaster (ABC)
│   └── TimesFMForecaster
└── DataWriter (ABC)
    ├── SQLiteDataWriter
    └── BigQueryDataWriter
```

## Components

### Data Readers

#### CSVDataReader
```python
data_reader = CSVDataReader(
    file_path="data/sales.csv",
    date_column="date",
    # Any pandas.read_csv() parameters
    encoding='utf-8',
    sep=','
)
```

#### SQLiteDataReader
```python
data_reader = SQLiteDataReader(
    database_path="data/sales.db",
    query="SELECT date, product_id, sales FROM transactions",
    date_column="date"
)
```

#### BigQueryDataReader
```python
data_reader = BigQueryDataReader(
    service_account_file="path/to/service_account.json",
    project="your-gcp-project",
    query="SELECT * FROM `project.dataset.table`",
    date_column="date"
)
```

### Data Transformer

Transforms long-format data into wide-format pivot tables suitable for forecasting:

```python
# Single dimension
transformer = DataTransformer(
    index="date",
    columns="product_id",
    values="sales"
)

# Multiple columns (creates combined IDs)
transformer = DataTransformer(
    index="date",
    columns=["product_id", "region"],  # Creates product_id_region
    values="sales"
)

# Multiple index columns (creates MultiIndex)
# ⚠️ Warning: MultiIndex may not be compatible with TimesFM
# Use this only if you plan to flatten or reset index before forecasting
transformer = DataTransformer(
    index=["date", "store_id"],  # Creates MultiIndex
    columns="product_id",
    values="sales"
)

# Both multiple (MultiIndex + combined column IDs)
transformer = DataTransformer(
    index=["date", "region"],           # MultiIndex
    columns=["product_id", "category"],  # Combined IDs
    values="sales"
)
```

**Note:** For TimesFM compatibility, it's recommended to use a **single index column** (typically `date`) and multiple columns for time series grouping.

### Forecaster

#### TimesFMForecaster

```python
forecaster = TimesFMForecaster(
    model_name='google/timesfm-2.5-200m-pytorch',
    max_context=1024,
    max_horizon=256,
    normalize_inputs=True,
    use_continuous_quantile_head=True,
    force_flip_invariance=True,
    infer_is_positive=True,
    fix_quantile_crossing=True
)
```

**Forecast Types:**
- **Quantile Forecast** (default): Returns predictions with quantile values separated by `|`
- **Point Forecast**: Returns single point predictions

```python
# Quantile forecast
forecast_df = workflow.run(horizon=28, return_point=False)

# Point forecast
forecast_df = workflow.run(horizon=28, return_point=True)
```

### Output Writers

#### SQLiteDataWriter

```python
data_writer = SQLiteDataWriter(
    database_path="output/forecasts.db",
    table_name="sales_forecast",
    if_exists='replace'  # or 'append', 'fail'
)
```

#### BigQueryDataWriter

```python
data_writer = BigQueryDataWriter(
    service_account_file="path/to/service_account.json",
    project="your-gcp-project",
    dataset="your_dataset",
    table="forecast_results",
    create_disposition='CREATE_IF_NEEDED',  # or 'CREATE_NEVER'
    write_disposition='WRITE_TRUNCATE'  # or 'WRITE_APPEND', 'WRITE_EMPTY'
)
```

## Usage Examples

### 1. CSV with Multi-Dimensional Grouping

```python
from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.forecasters import TimesFMForecaster
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter

data_reader = CSVDataReader(
    file_path="data/sales.csv",
    date_column="date"
)

# Multiple grouping columns
transformer = DataTransformer(
    index="date",
    columns=["product_id", "region"],
    values="sales"
)

forecaster = TimesFMForecaster()

data_writer = SQLiteDataWriter(
    database_path="output/forecasts.db",
    table_name="multi_dim_forecast"
)

workflow = ForecastWorkflow(
    data_reader=data_reader,
    forecaster=forecaster,
    data_writer=data_writer,
    transformer=transformer
)

forecast_df = workflow.run(horizon=30)
```

### 2. SQLite Source

```python
data_reader = SQLiteDataReader(
    database_path="data/transactions.db",
    query="""
        SELECT date, product_id, SUM(amount) as sales
        FROM transactions
        WHERE date >= '2023-01-01'
        GROUP BY date, product_id
    """,
    date_column="date"
)

# ... rest of the pipeline
```

### 3. BigQuery Source

```python
data_reader = BigQueryDataReader(
    service_account_file="credentials/service_account.json",
    project="my-project",
    query="""
        SELECT
            DATE(timestamp) as date,
            product_id,
            SUM(sales) as sales
        FROM `project.dataset.sales`
        WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
        GROUP BY date, product_id
    """,
    date_column="date"
)

# ... rest of the pipeline
```

### 4. Without Transformation (Pre-Pivoted Data)

```python
# If your data is already in pivot format
data_reader = CSVDataReader(
    file_path="data/sales_pivot.csv",
    date_column="date",
    index_col="date",
    parse_dates=True
)

workflow = ForecastWorkflow(
    data_reader=data_reader,
    forecaster=forecaster,
    data_writer=data_writer,
    transformer=None  # No transformation needed
)

forecast_df = workflow.run(horizon=28)
```

### 5. Preview Without Writing

```python
# Generate forecast without writing to output
forecast_df = workflow.run_without_output(horizon=28)

print(forecast_df.head())

# Later, write manually if satisfied
data_writer.write(forecast_df)
```

### 6. Multi-Index Usage (Advanced)

```python
from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.forecasters import TimesFMForecaster
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter

data_reader = CSVDataReader(
    file_path="data/hierarchical_sales.csv",
    date_column="date"
)

# Using multiple index columns creates MultiIndex
# ⚠️ This may require additional processing for TimesFM
transformer = DataTransformer(
    index=["date", "store_id"],  # MultiIndex: (date, store_id)
    columns="product_id",
    values="sales"
)

forecaster = TimesFMForecaster()

data_writer = SQLiteDataWriter(
    database_path="output/forecasts.db",
    table_name="hierarchical_forecast"
)

workflow = ForecastWorkflow(
    data_reader=data_reader,
    forecaster=forecaster,
    data_writer=data_writer,
    transformer=transformer
)

# Get forecast with MultiIndex
forecast_df = workflow.run_without_output(horizon=28)

# If needed, flatten MultiIndex before using
# forecast_df = forecast_df.reset_index()
```

**Note:** MultiIndex support is available but may require additional handling. For standard TimesFM usage, single index (date) with multiple columns is recommended.

## Output Format

### Quantile Forecast Output

```
date       | product_1           | product_2           | ...
-----------|---------------------|---------------------|----
2024-01-01 | 0.1|0.5|0.9         | 0.2|0.6|1.0         | ...
2024-01-02 | 0.15|0.55|0.95      | 0.25|0.65|1.05      | ...
...
```

Values are separated by `|` representing different quantiles (e.g., 10th, 50th, 90th percentiles).

### Point Forecast Output

```
date       | product_1 | product_2 | ...
-----------|-----------|-----------|----
2024-01-01 | 0.5       | 0.6       | ...
2024-01-02 | 0.55      | 0.65      | ...
...
```

## Project Structure

```
chronomaly/
├── __init__.py                                    # Package root (v0.1.0)
├── application/
│   ├── __init__.py
│   └── workflows/
│       ├── __init__.py                            # Exports: ForecastWorkflow
│       └── forecast_workflow.py                   # Main orchestrator class
├── infrastructure/
│   ├── __init__.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── readers/
│   │   │   ├── __init__.py                        # Exports: DataReader
│   │   │   ├── base.py                            # DataReader ABC
│   │   │   ├── files/
│   │   │   │   ├── __init__.py                    # Exports: CSVDataReader
│   │   │   │   └── csv.py                         # CSV implementation
│   │   │   ├── databases/
│   │   │   │   ├── __init__.py                    # Exports: BigQueryDataReader, SQLiteDataReader
│   │   │   │   ├── bigquery.py                    # BigQuery reader
│   │   │   │   └── sqlite.py                      # SQLite reader
│   │   │   └── apis/
│   │   │       └── __init__.py                    # API readers (placeholder)
│   │   └── writers/
│   │       ├── __init__.py                        # Exports: DataWriter
│   │       ├── base.py                            # DataWriter ABC
│   │       └── databases/
│   │           ├── __init__.py                    # Exports: BigQueryDataWriter, SQLiteDataWriter
│   │           ├── bigquery.py                    # BigQuery writer
│   │           └── sqlite.py                      # SQLite writer
│   ├── forecasters/
│   │   ├── __init__.py                            # Exports: Forecaster, TimesFMForecaster
│   │   ├── base.py                                # Forecaster ABC
│   │   └── timesfm.py                             # TimesFM implementation
│   ├── transformers/
│   │   ├── __init__.py                            # Exports: DataTransformer
│   │   └── pivot.py                               # Pivot table transformer
│   ├── comparators/
│   │   └── __init__.py                            # Comparators (placeholder)
│   ├── notifiers/
│   │   └── __init__.py                            # Notifiers (placeholder)
│   └── visualizers/
│       └── __init__.py                            # Visualizers (placeholder)
└── shared/
    └── __init__.py                                # Shared utilities

examples/
├── example_csv.py                                 # CSV example
├── example_sqlite.py                              # SQLite example
├── example_bigquery.py                            # BigQuery reader example
├── example_bigquery_to_bigquery.py                # BigQuery reader to BigQuery writer
├── example_multi_dimension.py                     # Multi-column grouping
├── example_multi_index.py                         # Multi-index usage (advanced)
├── example_point_forecast.py                      # Point forecast
└── example_without_transform.py                   # Pre-pivoted data
```

## Extending the Library

### Adding a New Data Source

```python
from chronomaly.infrastructure.data.readers.base import DataReader
import pandas as pd

class CustomDataReader(DataReader):
    def __init__(self, **kwargs):
        # Your initialization
        pass

    def load(self) -> pd.DataFrame:
        # Your data loading logic
        df = load_your_data()
        return df
```

### Adding a New Forecaster

```python
from chronomaly.infrastructure.forecasters.base import Forecaster
import pandas as pd

class CustomForecaster(Forecaster):
    def __init__(self, **kwargs):
        # Your initialization
        pass

    def forecast(self, dataframe: pd.DataFrame, horizon: int) -> pd.DataFrame:
        # Your forecasting logic
        forecast_df = your_forecast_logic(dataframe, horizon)
        return forecast_df
```

### Adding a New Output Writer

```python
from chronomaly.infrastructure.data.writers.base import DataWriter
import pandas as pd

class CustomDataWriter(DataWriter):
    def __init__(self, **kwargs):
        # Your initialization
        pass

    def write(self, dataframe: pd.DataFrame) -> None:
        # Your output logic
        write_your_output(dataframe)
```

## Troubleshooting

### ModuleNotFoundError: No module named 'chronomaly'

**Error:** `ModuleNotFoundError: No module named 'chronomaly'`

**Solution:** The package needs to be installed before use. From the project root directory:

```bash
# Install in editable mode
pip install -e .

# Or with all features
pip install -e ".[all]"
```

### TimesFM Installation Issues

**Error:** `ERROR: Could not find a version that satisfies the requirement timesfm`

**Solution:** Always install TimesFM from GitHub source:

```bash
pip install git+https://github.com/google-research/timesfm.git
```

### Memory Issues

**Error:** Out of memory when loading TimesFM model

**Solution:** TimesFM requires at least 16GB RAM. Consider:
- Using a machine with more memory
- Closing other applications
- Using smaller batch sizes in your forecasts

## Future Enhancements

The architecture supports easy addition of:

- **Anomaly Detection**: `AnomalyDetector` class for detecting outliers
- **Notifications**: `NotificationService` for email/Slack alerts
- **Actuals Loading**: `ActualsLoader` for loading realized values
- **Additional Forecasters**: Prophet, ARIMA, custom models
- **Additional Data Sources**: REST APIs, Snowflake, PostgreSQL, etc.
- **Additional Outputs**: S3, Parquet, CSV, JSON, etc.

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Built with [Google TimesFM](https://github.com/google-research/timesfm)
- Inspired by modern data pipeline architectures
