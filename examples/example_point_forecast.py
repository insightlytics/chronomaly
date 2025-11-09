"""
Example: Point forecast (instead of quantile forecast)
"""

from chronomaly.application.workflows import ForecastWorkflow
from chronomaly.infrastructure.data.readers.files import CSVDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.forecasters import TimesFMForecaster
from chronomaly.infrastructure.data.writers.databases import SQLiteDataWriter


def main():
    # Configure components
    data_reader = CSVDataReader(
        file_path="data/sales.csv",
        date_column="date"
    )

    transformer = DataTransformer(
        index="date",
        columns="product_id",
        values="sales"
    )

    forecaster = TimesFMForecaster()

    data_writer = SQLiteDataWriter(
        database_path="output/forecasts.db",
        table_name="point_forecast",
        if_exists="replace"
    )

    # Create workflow
    workflow = ForecastWorkflow(
        data_reader=data_reader,
        forecaster=forecaster,
        data_writer=data_writer,
        transformer=transformer
    )

    # Generate point forecast (not quantile)
    forecast_df = workflow.run(horizon=28, return_point=True)

    print("Point forecast completed!")
    print(forecast_df.head())


if __name__ == "__main__":
    main()
