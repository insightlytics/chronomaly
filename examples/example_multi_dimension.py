"""
Example: Multi-dimensional forecasting (multiple grouping columns)
"""

from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader, SQLiteDataReader
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.forecasters import TimesFMForecaster
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter, SQLiteDataWriter

def main():
    # Step 1: Configure data source
    data_reader = CSVDataReader(
        file_path="data/sales_multi.csv",
        date_column="date"
    )

    # Step 2: Configure transformer with multiple columns
    # This will create timeseries IDs like "product1_region1", "product1_region2", etc.
    transformer = DataTransformer(
        index="date",
        columns=["product_id", "region"],  # Multiple grouping columns
        values="sales"
    )

    # Step 3: Configure forecaster
    forecaster = TimesFMForecaster()

    # Step 4: Configure output writer
    data_writer = SQLiteDataWriter(
        database_path="output/forecasts.db",
        table_name="multi_dimension_forecast",
        if_exists="replace"
    )

    # Step 5: Create and run pipeline
    workflow = ForecastWorkflow(
        data_reader=data_reader,
        forecaster=forecaster,
        data_writer=data_writer,
        transformer=transformer
    )

    # Generate forecast
    forecast_df = workflow.run(horizon=28)

    print("Multi-dimensional forecast completed!")
    print(forecast_df.head())


if __name__ == "__main__":
    main()
