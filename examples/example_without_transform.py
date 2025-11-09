"""
Example: Forecasting without transformation (data already in pivot format)
"""

from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader, SQLiteDataReader
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.forecasters import TimesFMForecaster
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter, SQLiteDataWriter

def main():
    # Step 1: Configure data source
    # Assuming CSV is already in pivot format with date as index
    # and each column representing a different time series
    data_reader = CSVDataReader(
        file_path="data/sales_pivot.csv",
        date_column="date",
        index_col="date",  # Set date as index
        parse_dates=True
    )

    # Step 2: Configure forecaster
    forecaster = TimesFMForecaster()

    # Step 3: Configure output writer
    data_writer = SQLiteDataWriter(
        database_path="output/forecasts.db",
        table_name="no_transform_forecast",
        if_exists="replace"
    )

    # Step 4: Create pipeline WITHOUT transformer
    workflow = ForecastWorkflow(
        data_reader=data_reader,
        forecaster=forecaster,
        data_writer=data_writer,
        transformer=None  # No transformation needed
    )

    # Generate forecast
    forecast_df = workflow.run(horizon=28)

    print("Forecast completed without transformation!")
    print(forecast_df.head())


if __name__ == "__main__":
    main()
