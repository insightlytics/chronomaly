"""
Example: Full-featured Anomaly Detection matching original implementation

This example demonstrates all features of the ForecastActualComparator:
- Reading forecast and actual data
- Creating dimension mappings from actual data
- Pivoting actual data to match forecast format
- Comparing with confidence intervals
- Splitting metrics into dimension columns
- Applying cumulative threshold filtering (top 95%)
- Filtering only anomalies with minimum deviation
- Formatting deviation as percentage string

This matches the functionality of the original anomaly detection script.
"""

from chronomaly.application.workflows import AnomalyDetectionWorkflow
from chronomaly.infrastructure.data.readers.databases import BigQueryDataReader
from chronomaly.infrastructure.transformers import DataTransformer
from chronomaly.infrastructure.comparators import ForecastActualComparator
from chronomaly.infrastructure.data.writers.databases import BigQueryDataWriter
from datetime import datetime, timedelta


def main():
    """
    Run anomaly detection with all features enabled.

    This matches the original script's behavior exactly.
    """

    # Calculate dates (yesterday)
    days_ago_1 = datetime.now() - timedelta(days=1)
    target_date = days_ago_1.strftime('%Y-%m-%d')

    print(f"Running anomaly detection for date: {target_date}")
    print("=" * 80)

    # ============================================================================
    # Step 1: Configure forecast data reader
    # ============================================================================
    forecast_reader = BigQueryDataReader(
        service_account_file="path/to/service-account.json",
        project="your-project-id",
        query=f"""
            SELECT *
            FROM `your-project.dataset.forecast`
            WHERE date = '{target_date}'
            ORDER BY date
        """
    )

    # ============================================================================
    # Step 2: Configure actual data reader
    # ============================================================================
    actual_reader = BigQueryDataReader(
        service_account_file="path/to/service-account.json",
        project="your-project-id",
        query=f"""
            SELECT
                date,
                platform,
                default_channel_group,
                landing_page_group,
                SUM(sessions) AS sessions
            FROM `your-project.dataset.traffic_data_*`
            WHERE date = '{target_date}'
            GROUP BY date, platform, default_channel_group, landing_page_group
            ORDER BY date
        """
    )

    # ============================================================================
    # Step 3: Load actual data to create dimension mappings
    # ============================================================================
    # This preserves original dimension names (with spaces, capitalization, etc.)
    print("\n1. Creating dimension mappings from actual data...")
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

    print(f"   - Platform mappings: {len(platform_map)} values")
    print(f"   - Channel mappings: {len(channel_map)} values")
    print(f"   - Landing page mappings: {len(landing_page_map)} values")

    # ============================================================================
    # Step 4: Configure transformer for actual data pivot
    # ============================================================================
    print("\n2. Configuring data transformer...")
    transformer = DataTransformer(
        index="date",
        columns=["platform", "default_channel_group", "landing_page_group"],
        values="sessions"
    )

    # ============================================================================
    # Step 5: Configure anomaly detector with ALL features
    # ============================================================================
    print("\n3. Configuring anomaly detector with full feature set...")
    anomaly_detector = ForecastActualComparator(
        transformer=transformer,
        date_column="date",
        exclude_columns=["date"],
        # Split metrics into separate dimension columns
        dimension_names=["platform", "default_channel_group", "landing_page_group"],
        # Apply dimension mappings to restore original names
        dimension_mappings={
            "platform": platform_map,
            "default_channel_group": channel_map,
            "landing_page_group": landing_page_map
        },
        # Filter to top 95% of metrics by forecast value
        cumulative_threshold=0.95,
        # Return only anomalies (BELOW_P10, ABOVE_P90)
        return_only_anomalies=True,
        # Minimum 5% deviation to report
        min_deviation_threshold=5.0,
        # Format deviation as "15.3%" string
        format_deviation_as_string=True
    )

    # ============================================================================
    # Step 6: Configure output writer
    # ============================================================================
    print("\n4. Configuring output writer...")
    data_writer = BigQueryDataWriter(
        service_account_file="path/to/service-account.json",
        project="your-project-id",
        dataset="anomaly_detection",
        table="daily_anomalies",
        if_exists="append"  # Append for historical tracking
    )

    # ============================================================================
    # Step 7: Create and run workflow
    # ============================================================================
    print("\n5. Running anomaly detection workflow...")
    workflow = AnomalyDetectionWorkflow(
        forecast_reader=forecast_reader,
        actual_reader=actual_reader,
        anomaly_detector=anomaly_detector,
        data_writer=data_writer
    )

    # Run detection
    anomaly_df = workflow.run()

    # ============================================================================
    # Step 8: Display results
    # ============================================================================
    print("\n" + "=" * 80)
    print("ANOMALY DETECTION COMPLETED")
    print("=" * 80)

    if anomaly_df.empty:
        print("\n✓ No anomalies detected - all metrics within expected range!")
    else:
        print(f"\n⚠ {len(anomaly_df)} anomalies detected")

        print("\nStatus breakdown:")
        print(anomaly_df['status'].value_counts())

        print("\nTop 10 anomalies by deviation:")
        print(anomaly_df.nlargest(10, 'deviation_pct')[[
            'date', 'platform', 'default_channel_group', 'landing_page_group',
            'actual', 'forecast', 'q10', 'q90', 'status', 'deviation_pct'
        ]].to_string(index=False))

        print(f"\nFull results written to: your-project.anomaly_detection.daily_anomalies")


def example_without_workflow():
    """
    Alternative example: Manual detection without workflow.

    Useful when you want more control over the process or need to
    perform additional transformations before writing results.
    """

    print("\n" + "=" * 80)
    print("MANUAL DETECTION EXAMPLE")
    print("=" * 80)

    # Configure readers
    target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    forecast_reader = BigQueryDataReader(
        service_account_file="path/to/service-account.json",
        project="your-project-id",
        query=f"SELECT * FROM `your-project.dataset.forecast` WHERE date = '{target_date}'"
    )

    actual_reader = BigQueryDataReader(
        service_account_file="path/to/service-account.json",
        project="your-project-id",
        query=f"""
            SELECT date, platform, channel, SUM(sessions) as sessions
            FROM `your-project.dataset.traffic` WHERE date = '{target_date}'
            GROUP BY date, platform, channel
        """
    )

    # Load data
    print(f"\nLoading data for {target_date}...")
    forecast_df = forecast_reader.load()
    actual_df = actual_reader.load()

    # Create mappings
    print("\nCreating dimension mappings...")
    platform_map = ForecastActualComparator.create_mapping_from_dataframe(actual_df, 'platform')
    channel_map = ForecastActualComparator.create_mapping_from_dataframe(actual_df, 'channel')

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
        dimension_mappings={
            "platform": platform_map,
            "channel": channel_map
        },
        cumulative_threshold=0.95,
        return_only_anomalies=True,
        min_deviation_threshold=5.0,
        format_deviation_as_string=True
    )

    # Run detection
    print("\nDetecting anomalies...")
    anomaly_df = detector.detect(forecast_df, actual_df)

    # Display results
    if anomaly_df.empty:
        print("\n✓ No anomalies detected!")
    else:
        print(f"\n⚠ {len(anomaly_df)} anomalies detected:")
        print(anomaly_df.to_string(index=False))

    return anomaly_df


def example_progressive_filtering():
    """
    Example showing how to use different filtering strategies.
    """

    print("\n" + "=" * 80)
    print("PROGRESSIVE FILTERING EXAMPLE")
    print("=" * 80)

    # Setup (simplified for example)
    target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    forecast_reader = BigQueryDataReader(
        service_account_file="path/to/service-account.json",
        project="your-project-id",
        query=f"SELECT * FROM `your-project.dataset.forecast` WHERE date = '{target_date}'"
    )

    actual_reader = BigQueryDataReader(
        service_account_file="path/to/service-account.json",
        project="your-project-id",
        query=f"SELECT date, platform, channel, SUM(sessions) as sessions FROM `your-project.dataset.traffic` WHERE date = '{target_date}' GROUP BY date, platform, channel"
    )

    forecast_df = forecast_reader.load()
    actual_df = actual_reader.load()

    transformer = DataTransformer(index="date", columns=["platform", "channel"], values="sessions")

    # Strategy 1: No filtering - see everything
    print("\n1. No filtering (all results):")
    detector1 = ForecastActualComparator(transformer=transformer, date_column="date")
    results1 = detector1.detect(forecast_df, actual_df)
    print(f"   Total results: {len(results1)}")

    # Strategy 2: Top 95% by forecast value
    print("\n2. Top 95% of metrics:")
    detector2 = ForecastActualComparator(
        transformer=transformer,
        date_column="date",
        cumulative_threshold=0.95
    )
    results2 = detector2.detect(forecast_df, actual_df)
    print(f"   Filtered results: {len(results2)}")

    # Strategy 3: Only anomalies
    print("\n3. Only anomalies (BELOW_P10, ABOVE_P90):")
    detector3 = ForecastActualComparator(
        transformer=transformer,
        date_column="date",
        return_only_anomalies=True
    )
    results3 = detector3.detect(forecast_df, actual_df)
    print(f"   Anomalies: {len(results3)}")

    # Strategy 4: Only significant anomalies (>5% deviation)
    print("\n4. Significant anomalies (>5% deviation):")
    detector4 = ForecastActualComparator(
        transformer=transformer,
        date_column="date",
        return_only_anomalies=True,
        min_deviation_threshold=5.0
    )
    results4 = detector4.detect(forecast_df, actual_df)
    print(f"   Significant anomalies: {len(results4)}")

    # Strategy 5: Full featured (top 95% + anomalies + >5% deviation)
    print("\n5. Full featured (top 95% + anomalies + >5%):")
    detector5 = ForecastActualComparator(
        transformer=transformer,
        date_column="date",
        cumulative_threshold=0.95,
        return_only_anomalies=True,
        min_deviation_threshold=5.0,
        format_deviation_as_string=True
    )
    results5 = detector5.detect(forecast_df, actual_df)
    print(f"   Final filtered results: {len(results5)}")

    if not results5.empty:
        print("\nFinal results:")
        print(results5.to_string(index=False))


if __name__ == "__main__":
    # Run main example
    main()

    # Uncomment to run alternative examples:
    # example_without_workflow()
    # example_progressive_filtering()
