"""
Example: Forecasting from SQLite data source
"""

from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.databases import SQLiteDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.forecasters import TimesFMForecaster
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter


def main():
    # Step 1: Configure data reader
    data_reader = SQLiteDataReader(
        database_path="data/sales.db",
        query="""
            SELECT date, product_id, SUM(quantity) as sales
            FROM sales_transactions
            WHERE date >= '2023-01-01'
            GROUP BY date, product_id
        """,
        date_column="date"
    )

    # Step 2: Configure transformer for pivot
    transformer = DataTransformer(
        index="date",
        columns="product_id",
        values="sales"
    )

    # Step 3: Configure forecaster
    forecaster = TimesFMForecaster()

    # Step 4: Configure data writer
    data_writer = SQLiteDataWriter(
        database_path="output/forecasts.db",
        table_name="sales_forecast_from_sqlite",
        if_exists="replace"
    )

    # Step 5: Create and run workflow
    workflow = ForecastWorkflow(
        data_reader=data_reader,
        forecaster=forecaster,
        data_writer=data_writer,
        transformer=transformer
    )

    # Generate 30-day forecast
    forecast_df = workflow.run(horizon=30)

    print("Forecast completed!")
    print(forecast_df.head())


if __name__ == "__main__":
    main()
