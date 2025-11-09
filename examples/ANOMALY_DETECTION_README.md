# Anomaly Detection Workflow

Complete guide to using the `AnomalyDetectionWorkflow` for comparing forecast predictions against actual values.

## Overview

The Anomaly Detection Workflow compares forecast data (with confidence intervals) against actual observed data to identify anomalies. It matches the functionality of the original implementation and includes advanced filtering and transformation options.

**Key Features:**
- Automatic pivoting of raw actual data
- 80% confidence interval comparison (q10-q90)
- Dimension name mapping and metric splitting
- Cumulative threshold filtering (e.g., top 95% of metrics)
- Flexible anomaly filtering
- Deviation percentage calculation and formatting

## How It Works

### 1. Data Format Requirements

**Forecast Data (Pivot Format)**
- Wide/pivot format with one column per metric
- Pipe-separated quantiles: `point|q10|q20|q30|q40|q50|q60|q70|q80|q90`
- q10 at index 1, q90 at index 9 (80% confidence interval)

Example:
```
date        | desktop_organic_homepage | mobile_paid_product
2024-01-15  | 100|90|92|95|98|100|102|105|108|110 | 50|45|46|47|48|50|52|53|55|60
```

**Actual Data (Raw Format)**
- Long format (will be automatically pivoted)
- Contains dimension columns (platform, channel, etc.)

Example:
```
date        | platform | channel  | landing_page | sessions
2024-01-15  | desktop  | organic  | homepage     | 95
2024-01-15  | mobile   | paid     | product      | 65
```

### 2. Anomaly Detection Logic

For each metric:

1. **Extract confidence interval**: q10 and q90 from forecast (80% CI)
2. **Compare actual value**:
   - `IN_RANGE`: q10 ≤ actual ≤ q90
   - `BELOW_P10`: actual < q10 (lower than expected)
   - `ABOVE_P90`: actual > q90 (higher than expected)
   - `NO_FORECAST`: no valid forecast (q10=0 and q90=0)

3. **Calculate deviation**:
   - Below q10: `((q10 - actual) / q10) * 100`
   - Above q90: `((actual - q90) / q90) * 100`

### 3. Advanced Features

**Dimension Mapping**
- Preserves original dimension names (e.g., "Mobile App" instead of "mobileapp")
- Creates mapping from actual data column values
- Applies during metric splitting

**Metric Splitting**
- Converts `desktop_organic_homepage` to separate columns:
  - `platform`: "Desktop"
  - `channel`: "Organic"
  - `landing_page`: "Homepage"

**Cumulative Threshold Filtering**
- Filters to top X% of metrics by forecast value
- Example: `cumulative_threshold=0.95` keeps top 95%
- Focuses analysis on high-impact metrics

**Anomaly Filtering**
- `return_only_anomalies=True`: Only BELOW_P10, ABOVE_P90
- `min_deviation_threshold=5.0`: Minimum 5% deviation
- Combines for significant anomalies only

**String Formatting**
- `format_deviation_as_string=True`: "15.3%" instead of 15.3
- Useful for reports and dashboards

## Usage Examples

### Example 1: Basic Detection

Simple detection without advanced features:

```python
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.databases import SQLiteDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.comparators import ForecastActualComparator
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter

# Configure readers
forecast_reader = SQLiteDataReader(
    database_path="forecasts.db",
    query="SELECT * FROM forecast WHERE date = '2024-01-15'",
    date_column="date"
)

actual_reader = SQLiteDataReader(
    database_path="actuals.db",
    query="""
        SELECT date, platform, channel, SUM(sessions) as sessions
        FROM traffic WHERE date = '2024-01-15'
        GROUP BY date, platform, channel
    """,
    date_column="date"
)

# Configure transformer
transformer = DataTransformer(
    index="date",
    columns=["platform", "channel"],
    values="sessions"
)

# Basic detector
detector = ForecastActualComparator(
    transformer=transformer,
    date_column="date"
)

# Configure writer
writer = SQLiteDataWriter(
    database_path="output.db",
    table_name="anomalies"
)

# Run workflow
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=writer
)

results = workflow.run()
```

### Example 2: Full-Featured Detection (Matching Original Implementation)

Complete example with all features:

```python
from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.comparators import ForecastActualComparator
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter

# Read forecast data
forecast_reader = BigQueryDataReader(
    service_account_file="credentials.json",
    project="my-project",
    query="""
        SELECT * FROM `my-project.dataset.forecast`
        WHERE date = '2024-01-15'
    """
)

# Read actual data
actual_reader = BigQueryDataReader(
    service_account_file="credentials.json",
    project="my-project",
    query="""
        SELECT
            date,
            platform,
            default_channel_group,
            landing_page_group,
            SUM(sessions) AS sessions
        FROM `my-project.dataset.traffic`
        WHERE date = '2024-01-15'
        GROUP BY date, platform, default_channel_group, landing_page_group
    """
)

# Load actual data to create dimension mappings
actual_df = actual_reader.load()

platform_map = ForecastActualComparator.create_mapping_from_dataframe(
    actual_df, 'platform'
)
channel_map = ForecastActualComparator.create_mapping_from_dataframe(
    actual_df, 'default_channel_group'
)
landing_page_map = ForecastActualComparator.create_mapping_from_dataframe(
    actual_df, 'landing_page_group'
)

# Configure transformer
transformer = DataTransformer(
    index="date",
    columns=["platform", "default_channel_group", "landing_page_group"],
    values="sessions"
)

# Full-featured detector
detector = ForecastActualComparator(
    transformer=transformer,
    date_column="date",
    exclude_columns=["date"],
    # Split metrics into dimension columns
    dimension_names=["platform", "default_channel_group", "landing_page_group"],
    # Apply dimension mappings
    dimension_mappings={
        "platform": platform_map,
        "default_channel_group": channel_map,
        "landing_page_group": landing_page_map
    },
    # Filter to top 95% of metrics
    cumulative_threshold=0.95,
    # Return only anomalies
    return_only_anomalies=True,
    # Minimum 5% deviation
    min_deviation_threshold=5.0,
    # Format as "15.3%"
    format_deviation_as_string=True
)

# Configure writer
writer = BigQueryDataWriter(
    service_account_file="credentials.json",
    project="my-project",
    dataset="anomalies",
    table="daily_anomalies",
    if_exists="append"
)

# Run workflow
workflow = AnomalyDetectionWorkflow(
    forecast_reader=forecast_reader,
    actual_reader=actual_reader,
    anomaly_detector=detector,
    data_writer=writer
)

results = workflow.run()

print(f"Detected {len(results)} anomalies")
```

### Example 3: Manual Detection Without Workflow

More control by loading data manually:

```python
# Load data
forecast_df = forecast_reader.load()
actual_df = actual_reader.load()

# Create mappings
platform_map = ForecastActualComparator.create_mapping_from_dataframe(
    actual_df, 'platform'
)

# Configure detector
transformer = DataTransformer(
    index="date",
    columns=["platform", "channel"],
    values="sessions"
)

detector = ForecastActualComparator(
    transformer=transformer,
    date_column="date",
    dimension_names=["platform", "channel"],
    dimension_mappings={"platform": platform_map},
    cumulative_threshold=0.95,
    return_only_anomalies=True,
    min_deviation_threshold=5.0
)

# Detect anomalies
results = detector.detect(forecast_df, actual_df)

# Custom processing
if not results.empty:
    # Filter for critical anomalies (>10% deviation)
    critical = results[results['deviation_pct'] > 10.0]
    print(f"Critical anomalies: {len(critical)}")
```

### Example 4: Progressive Filtering

Different filtering strategies:

```python
transformer = DataTransformer(
    index="date",
    columns=["platform", "channel"],
    values="sessions"
)

# Strategy 1: All results
detector1 = ForecastActualComparator(
    transformer=transformer,
    date_column="date"
)
all_results = detector1.detect(forecast_df, actual_df)

# Strategy 2: Top 95% by forecast
detector2 = ForecastActualComparator(
    transformer=transformer,
    date_column="date",
    cumulative_threshold=0.95
)
top95 = detector2.detect(forecast_df, actual_df)

# Strategy 3: Only anomalies
detector3 = ForecastActualComparator(
    transformer=transformer,
    date_column="date",
    return_only_anomalies=True
)
anomalies = detector3.detect(forecast_df, actual_df)

# Strategy 4: Significant anomalies (>5% deviation)
detector4 = ForecastActualComparator(
    transformer=transformer,
    date_column="date",
    return_only_anomalies=True,
    min_deviation_threshold=5.0
)
significant = detector4.detect(forecast_df, actual_df)

print(f"All: {len(all_results)}")
print(f"Top 95%: {len(top95)}")
print(f"Anomalies: {len(anomalies)}")
print(f"Significant: {len(significant)}")
```

## Configuration Options

### ForecastActualComparator Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `transformer` | DataTransformer | **required** | Transforms actual data to pivot format |
| `date_column` | str | `'date'` | Name of date column |
| `exclude_columns` | List[str] | `[date_column]` | Columns to exclude from comparison |
| `dimension_names` | List[str] | `None` | Dimension names to extract from metric |
| `dimension_mappings` | Dict | `{}` | Mappings for dimension values |
| `cumulative_threshold` | float | `None` | Filter to top X% (e.g., 0.95) |
| `return_only_anomalies` | bool | `False` | Return only BELOW_P10, ABOVE_P90 |
| `min_deviation_threshold` | float | `0.0` | Minimum deviation % to include |
| `format_deviation_as_string` | bool | `False` | Format as "15.3%" vs 15.3 |

### DataTransformer Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `index` | str/List[str] | Column(s) for index (typically 'date') |
| `columns` | str/List[str] | Column(s) for pivot columns |
| `values` | str | Column for values (metric to aggregate) |

## Output Formats

### Basic Output (No Dimension Splitting)

```
date       | metric                  | actual | forecast | q10 | q90 | status    | deviation_pct
2024-01-15 | desktop_organic_homepage| 950    | 1000     | 900 | 1100| IN_RANGE  | 0.0
2024-01-15 | mobile_paid_product     | 950    | 800      | 720 | 900 | ABOVE_P90 | 5.6
```

### With Dimension Splitting

```
date       | platform | channel | landing_page | actual | forecast | q10 | q90 | status    | deviation_pct
2024-01-15 | Desktop  | Organic | Homepage     | 950    | 1000     | 900 | 1100| IN_RANGE  | 0.0
2024-01-15 | Mobile   | Paid    | Product      | 950    | 800      | 720 | 900 | ABOVE_P90 | 5.6%
```

## Best Practices

1. **Create Dimension Mappings**: Always create mappings from actual data to preserve original names
2. **Use Cumulative Threshold**: Focus on high-impact metrics with `cumulative_threshold=0.95`
3. **Filter Intelligently**: Combine `return_only_anomalies=True` and `min_deviation_threshold=5.0`
4. **Historical Tracking**: Use `if_exists="append"` in writers for trend analysis
5. **Test Incrementally**: Start with basic detection, then add features as needed

## Troubleshooting

**Problem**: "Forecast DataFrame is empty"
- **Solution**: Check query returns data for the specified date

**Problem**: "Required columns not found in DataFrame"
- **Solution**: Verify actual data contains columns specified in transformer

**Problem**: "All results show NO_FORECAST"
- **Solution**: Verify forecast format is pipe-separated with 10 values

**Problem**: "Metrics don't match"
- **Solution**: Check pivot column names match forecast column names exactly

**Problem**: "Dimension mapping not applied"
- **Solution**: Ensure `dimension_names` matches order of `columns` in transformer

## Complete Examples

See these files for complete working examples:

- `example_anomaly_detection_sqlite.py` - Basic SQLite example
- `example_anomaly_detection_bigquery.py` - BigQuery example
- `example_anomaly_detection_full_featured.py` - All features (matches original)
- `test_anomaly_detection_full.py` - Comprehensive test suite

## Comparison with Original Implementation

This implementation provides the same functionality as the original script:

| Original Feature | Implementation |
|-----------------|----------------|
| `create_mapping()` | `ForecastActualComparator.create_mapping_from_dataframe()` |
| `filter_cumulative_threshold()` | `cumulative_threshold` parameter |
| Metric splitting | `dimension_names` parameter |
| Dimension mapping | `dimension_mappings` parameter |
| Anomaly filtering | `return_only_anomalies` parameter |
| Deviation threshold | `min_deviation_threshold` parameter |
| String formatting | `format_deviation_as_string` parameter |

**Key Difference**: Original processes company loop; this version assumes single company data (as per requirement).
