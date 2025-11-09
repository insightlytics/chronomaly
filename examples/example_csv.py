"""
Example: Forecasting from CSV data source
"""

from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.forecasters import TimesFMForecaster
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter


def main():
    # Step 1: Configure data reader
    data_reader = CSVDataReader(
        file_path="data/sales.csv",
        date_column="date"
    )

    # Step 2: Configure transformer for pivot
    transformer = DataTransformer(
        index="date",
        columns="product_id",
        values="sales"
    )

    # Step 3: Configure forecaster
    forecaster = TimesFMForecaster(
        max_context=1024,
        max_horizon=256,
        normalize_inputs=True,
        use_continuous_quantile_head=True
    )

    # Step 4: Configure data writer
    data_writer = SQLiteDataWriter(
        database_path="output/forecasts.db",
        table_name="sales_forecast",
        if_exists="replace"
    )

    # Step 5: Create and run workflow
    workflow = ForecastWorkflow(
        data_reader=data_reader,
        forecaster=forecaster,
        data_writer=data_writer,
        transformer=transformer
    )

    # Generate 28-day forecast with quantile predictions
    forecast_df = workflow.run(horizon=28, return_point=False)

    print("Forecast completed!")
    print(f"Shape: {forecast_df.shape}")
    print("\nFirst few rows:")
    print(forecast_df.head())


if __name__ == "__main__":
    main()
