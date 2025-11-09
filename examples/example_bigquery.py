"""
Example: Forecasting from BigQuery data source
"""

from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.forecasters import TimesFMForecaster
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter


def main():
    # Step 1: Configure BigQuery data reader
    data_reader = BigQueryDataReader(
        service_account_file="path/to/service_account.json",
        project="your-gcp-project-id",
        query="""
            SELECT
                DATE(timestamp) as date,
                product_id,
                SUM(sales_amount) as sales
            FROM `your-project.dataset.sales_table`
            WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
            GROUP BY date, product_id
            ORDER BY date
        """,
        date_column="date"
    )

    # Step 2: Configure transformer for pivot
    transformer = DataTransformer(
        index="date",
        columns="product_id",
        values="sales"
    )

    # Step 3: Configure forecaster with custom settings
    forecaster = TimesFMForecaster(
        max_context=1024,
        max_horizon=256,
        normalize_inputs=True
    )

    # Step 4: Configure data writer
    data_writer = SQLiteDataWriter(
        database_path="output/forecasts.db",
        table_name="bigquery_forecast",
        if_exists="replace"
    )

    # Step 5: Create and run workflow
    workflow = ForecastWorkflow(
        data_reader=data_reader,
        forecaster=forecaster,
        data_writer=data_writer,
        transformer=transformer
    )

    # Generate 60-day forecast
    forecast_df = workflow.run(horizon=60)

    print("Forecast completed!")
    print(forecast_df.head())


if __name__ == "__main__":
    main()
