# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chronomaly is a Python library for time series forecasting and anomaly detection using Google's TimesFM model. It follows Clean Architecture principles with a layered structure that separates workflows, infrastructure implementations, and shared utilities.

## Development Commands

### Environment Setup
```bash
# Install core dependencies
pip install -r requirements.txt

# Install TimesFM from GitHub (required)
pip install git+https://github.com/google-research/timesfm.git

# Install in editable mode
pip install -e .

# Install with BigQuery support
pip install -e ".[bigquery]"

# Install development tools
pip install -e ".[dev]"

# Install all optional dependencies
pip install -e ".[all]"
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_forecasters.py

# Run tests with verbose output
pytest -v

# Run tests with coverage
pytest --cov=chronomaly
```

### Code Quality
```bash
# Format code with Black
black chronomaly/

# Lint with flake8
flake8 chronomaly/

# Run both formatting and linting
black chronomaly/ && flake8 chronomaly/
```

## Architecture

### Layer Structure

The codebase follows Clean Architecture with three main layers:

1. **Application Layer** (`chronomaly/application/`): Orchestrates business workflows
   - `ForecastWorkflow`: Coordinates data reading → forecasting → writing
   - `AnomalyDetectionWorkflow`: Coordinates forecast reading → actual reading → anomaly detection → writing
   - `NotificationWorkflow`: Handles notification delivery with retry logic

2. **Infrastructure Layer** (`chronomaly/infrastructure/`): Concrete implementations
   - **Forecasters**: Model implementations (TimesFM)
   - **Anomaly Detectors**: Detection algorithms (ForecastActualAnomalyDetector)
   - **Data Readers**: Input sources (CSV, SQLite, BigQuery, DataFrame, APIs)
   - **Data Writers**: Output destinations (SQLite, BigQuery)
   - **Transformers**: Data transformations (Pivot, Filters, Formatters)
   - **Notifiers**: Notification channels (Email)

3. **Shared Layer** (`chronomaly/shared/`): Cross-cutting utilities
   - `TransformableMixin`: Provides transformer application functionality to components

### Key Design Patterns

**TransformableMixin Pattern**: Components that need data transformation capabilities inherit from `TransformableMixin` and accept a `transformers` parameter. Transformers are organized by stage:
- `'before'`: Applied before the component's main operation (e.g., before forecasting)
- `'after'`: Applied after the component's main operation (e.g., after detection)

Example:
```python
reader = BigQueryDataReader(
    ...,
    transformers={
        'after': [PivotTransformer(...)]  # Applied after loading data
    }
)

forecaster = TimesFMForecaster(
    ...,
    transformers={
        'before': [ValueFilter(...)],     # Applied before forecasting
        'after': [ColumnFormatter(...)]   # Applied after forecasting
    }
)
```

**Abstract Base Classes**: All major components (DataReader, DataWriter, Forecaster, AnomalyDetector) inherit from abstract base classes defining their interface.

**Workflow Orchestration**: Workflows are simple orchestrators that delegate to components. They do NOT handle transformations themselves - transformations are configured at the component level.

### Data Flow Patterns

**Forecast Flow**:
1. DataReader loads data (with optional 'after' transformers for pivoting)
2. Forecaster applies 'before' transformers → forecasts → applies 'after' transformers
3. DataWriter applies 'before' transformers → writes data

**Anomaly Detection Flow**:
1. ForecastReader loads forecast data (already in wide format)
2. ActualReader loads actual data (with optional 'after' transformers for pivoting to wide format)
3. AnomalyDetector compares → applies 'after' transformers for filtering/formatting
4. DataWriter writes anomalies

**Important**: The AnomalyDetector expects actual_df to be in pivoted (wide) format. Use PivotTransformer in ActualReader's 'after' transformers if source data is in long format.

### Quantile Format

TimesFM forecasts return quantiles as pipe-separated strings (e.g., "10.5|12.3|15.7|...") representing 10 quantile values. The ForecastActualAnomalyDetector:
- Uses index 0 for point forecast
- Uses index 1 (default) for lower bound (q10)
- Uses index 9 (default) for upper bound (q90)

## Important Implementation Details

### TimesFM Forecaster
- Requires `frequency` parameter ('D', 'H', 'W', 'M') to correctly generate forecast dates
- Validates horizon against `max_horizon` configuration
- Supports both point forecasts (`return_point=True`) and quantile forecasts (default)
- Input DataFrame columns represent individual time series to forecast
- Index must be datetime or convertible to datetime

### Data Readers
- All readers inherit from `DataReader` base class
- Must implement `load()` method returning pandas DataFrame
- Support optional `transformers` parameter with 'before' and 'after' stages
- BigQueryDataReader accepts SQL query or table name
- DataFrameReader is for in-memory DataFrames (useful for testing or chaining workflows)

### Data Writers
- All writers inherit from `DataWriter` base class
- Must implement `write()` method accepting pandas DataFrame
- BigQueryDataWriter supports `write_disposition` ('WRITE_APPEND', 'WRITE_TRUNCATE')
- SQLiteDataWriter creates tables if they don't exist

### Anomaly Detection
- Compares forecast quantiles against actual values
- Returns status: 'BELOW_LOWER', 'IN_RANGE', 'ABOVE_UPPER'
- Includes deviation metrics (absolute and percentage)
- Can split metric names into dimensions using `dimension_names` parameter
- Apply filters in 'after' transformers to get only significant anomalies

### Transformers
- **PivotTransformer**: Converts long format to wide format (date × metrics)
- **ValueFilter**: Filters rows by column values (include/exclude modes)
- **CumulativeThresholdFilter**: Keeps top N% by cumulative value
- **ColumnFormatter**: Formats column values (includes percentage helper)
- **ColumnSelector**: Selects or drops specific columns

All transformers can be chained in the `transformers` dict at component level.

## Testing Patterns

Tests are organized by feature:
- `test_forecasters.py`: Forecaster implementations
- `test_data_sources.py`: Data readers and writers
- `test_bug_fixes.py`: Regression tests for fixed bugs

When writing tests:
- Use pytest fixtures defined in `conftest.py`
- Create minimal test data (small DataFrames)
- Test both happy paths and error cases
- Include type validation tests
- Test transformer integration at component level

## Common Pitfalls

1. **Don't add transformers to workflows** - They belong on components (readers, forecasters, detectors, writers)

2. **Actual data must be pivoted for anomaly detection** - Use PivotTransformer in ActualReader's 'after' transformers

3. **TimesFM requires datetime index** - Ensure DataFrames have datetime index or convertible index

4. **Horizon validation** - TimesFM validates horizon ≤ max_horizon (default 256)

5. **Import paths** - Use absolute imports from chronomaly package root:
   ```python
   from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
   from chronomaly.application.workflows import ForecastWorkflow
   from chronomaly.shared import TransformableMixin  # Correct
   # NOT: from chronomaly.shared.mixins import TransformableMixin
   ```

6. **Empty DataFrame validation** - Most components validate against empty DataFrames and raise ValueError

## Configuration

The project uses:
- `pyproject.toml` for package metadata and dependencies
- `requirements.txt` for pip dependencies
- `.env` for environment variables (see `.env.example`)
- Environment variables for email notifications:
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
  - `EMAIL_FROM`, `EMAIL_TO` (comma-separated)

## Commit Conventions

Follow Conventional Commits format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test additions or fixes
- `chore:` Maintenance tasks

## Adding New Components

### New Data Reader
1. Create file in `chronomaly/infrastructure/data/readers/`
2. Inherit from `DataReader` and `TransformableMixin`
3. Implement `load()` method
4. Add `transformers` parameter support
5. Add to `__init__.py` exports
6. Write tests in `tests/test_data_sources.py`

### New Forecaster
1. Create file in `chronomaly/infrastructure/forecasters/`
2. Inherit from `Forecaster` and `TransformableMixin`
3. Implement `forecast()` method with signature: `forecast(dataframe, horizon, **kwargs)`
4. Add `transformers` parameter support
5. Add to `__init__.py` exports
6. Write tests in `tests/test_forecasters.py`

### New Transformer
1. Create file in appropriate `chronomaly/infrastructure/transformers/` subdirectory
2. Implement appropriate method (`filter()`, `format()`, or be callable)
3. Add clear docstring explaining purpose and parameters
4. Add to `__init__.py` exports
5. Add integration tests with components that will use it
