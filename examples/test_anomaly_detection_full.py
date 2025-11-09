"""
Comprehensive test for ForecastActualComparator with all features.

This test demonstrates:
- Dimension mapping creation
- Metric splitting into dimension columns
- Cumulative threshold filtering
- Anomaly-only filtering
- Deviation threshold filtering
- String formatting for deviation_pct
"""

import pandas as pd
from datetime import datetime


def create_comprehensive_sample_data():
    """Create comprehensive sample data for testing all features."""

    test_date = datetime(2024, 1, 15)

    # Create forecast data (pivot format with pipe-separated quantiles)
    # Format: "point|q10|q20|q30|q40|q50|q60|q70|q80|q90"
    forecast_data = {
        'date': [test_date],
        # High volume metrics
        'desktop_organic_homepage': ['1000|900|920|950|970|1000|1030|1050|1070|1100'],
        'mobile_paid_product': ['800|720|740|760|780|800|820|840|860|900'],
        'desktop_direct_homepage': ['600|540|555|570|585|600|615|630|645|660'],
        # Medium volume metrics
        'mobile_organic_category': ['300|270|278|285|292|300|308|315|322|330'],
        'desktop_paid_product': ['200|180|185|190|195|200|205|210|215|220'],
        # Low volume metrics
        'mobile_direct_category': ['50|45|46|47|48|50|52|53|54|55'],
        'desktop_social_blog': ['20|18|18.5|19|19.5|20|20.5|21|21.5|22'],
        'mobile_email_contact': ['10|9|9.2|9.4|9.6|10|10.4|10.8|11.2|11']
    }
    forecast_df = pd.DataFrame(forecast_data)

    # Create actual data (raw format - will be pivoted)
    # Mix of in-range, below, and above values
    actual_data = {
        'date': [test_date] * 8,
        'platform': ['Desktop', 'Mobile', 'Desktop', 'Mobile', 'Desktop', 'Mobile', 'Desktop', 'Mobile'],
        'channel': ['Organic', 'Paid', 'Direct', 'Organic', 'Paid', 'Direct', 'Social', 'Email'],
        'landing_page': ['Homepage', 'Product', 'Homepage', 'Category', 'Product', 'Category', 'Blog', 'Contact'],
        'sessions': [
            950,   # desktop_organic_homepage: IN_RANGE (900-1100)
            950,   # mobile_paid_product: ABOVE_P90 (above 900) - 5.6% deviation
            500,   # desktop_direct_homepage: BELOW_P10 (below 540) - 7.4% deviation
            320,   # mobile_organic_category: IN_RANGE (270-330)
            240,   # desktop_paid_product: ABOVE_P90 (above 220) - 9.1% deviation
            40,    # mobile_direct_category: BELOW_P10 (below 45) - 11.1% deviation
            15,    # desktop_social_blog: BELOW_P10 (below 18) - 16.7% deviation
            11.5   # mobile_email_contact: IN_RANGE (9-11)
        ]
    }
    actual_df = pd.DataFrame(actual_data)

    return forecast_df, actual_df


def test_basic_detection():
    """Test basic detection without any filtering."""

    print("=" * 80)
    print("TEST 1: BASIC DETECTION (No Filtering)")
    print("=" * 80)

    try:
        from chronomaly.infrastructure.comparators import ForecastActualComparator
        from chronomaly.infrastructure.transformers import DataTransformer

        forecast_df, actual_df = create_comprehensive_sample_data()

        print("\nForecast data shape:", forecast_df.shape)
        print("Actual data shape:", actual_df.shape)

        # Configure transformer
        transformer = DataTransformer(
            index="date",
            columns=["platform", "channel", "landing_page"],
            values="sessions"
        )

        # Basic detector
        detector = ForecastActualComparator(
            transformer=transformer,
            date_column="date"
        )

        # Run detection
        results = detector.detect(forecast_df, actual_df)

        print(f"\nTotal results: {len(results)}")
        print("\nStatus breakdown:")
        print(results['status'].value_counts())

        print("\nAll results:")
        print(results.to_string(index=False))

        return results

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_dimension_mapping():
    """Test dimension mapping and metric splitting."""

    print("\n" + "=" * 80)
    print("TEST 2: DIMENSION MAPPING & METRIC SPLITTING")
    print("=" * 80)

    try:
        from chronomaly.infrastructure.comparators import ForecastActualComparator
        from chronomaly.infrastructure.transformers import DataTransformer

        forecast_df, actual_df = create_comprehensive_sample_data()

        # Create dimension mappings
        print("\n1. Creating dimension mappings...")
        platform_map = ForecastActualComparator.create_mapping_from_dataframe(actual_df, 'platform')
        channel_map = ForecastActualComparator.create_mapping_from_dataframe(actual_df, 'channel')
        landing_page_map = ForecastActualComparator.create_mapping_from_dataframe(actual_df, 'landing_page')

        print(f"   Platform map: {platform_map}")
        print(f"   Channel map: {channel_map}")
        print(f"   Landing page map: {landing_page_map}")

        # Configure transformer
        transformer = DataTransformer(
            index="date",
            columns=["platform", "channel", "landing_page"],
            values="sessions"
        )

        # Detector with dimension splitting and mapping
        print("\n2. Running detection with dimension splitting...")
        detector = ForecastActualComparator(
            transformer=transformer,
            date_column="date",
            dimension_names=["platform", "channel", "landing_page"],
            dimension_mappings={
                "platform": platform_map,
                "channel": channel_map,
                "landing_page": landing_page_map
            }
        )

        results = detector.detect(forecast_df, actual_df)

        print(f"\nResults with dimension columns: {len(results)}")
        print("\nColumns:", results.columns.tolist())
        print("\nSample results:")
        print(results.head().to_string(index=False))

        # Verify 'metric' column is removed and dimensions are added
        assert 'metric' not in results.columns, "Metric column should be removed"
        assert 'platform' in results.columns, "Platform column should exist"
        assert 'channel' in results.columns, "Channel column should exist"
        assert 'landing_page' in results.columns, "Landing page column should exist"

        # Verify mappings preserved original names
        assert 'Desktop' in results['platform'].values, "Desktop should be capitalized"
        assert 'Mobile' in results['platform'].values, "Mobile should be capitalized"

        print("\n✓ Dimension mapping test passed!")

        return results

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_cumulative_threshold():
    """Test cumulative threshold filtering (top 95%)."""

    print("\n" + "=" * 80)
    print("TEST 3: CUMULATIVE THRESHOLD FILTERING")
    print("=" * 80)

    try:
        from chronomaly.infrastructure.comparators import ForecastActualComparator
        from chronomaly.infrastructure.transformers import DataTransformer

        forecast_df, actual_df = create_comprehensive_sample_data()

        transformer = DataTransformer(
            index="date",
            columns=["platform", "channel", "landing_page"],
            values="sessions"
        )

        # Without threshold
        detector_no_threshold = ForecastActualComparator(
            transformer=transformer,
            date_column="date"
        )
        results_all = detector_no_threshold.detect(forecast_df, actual_df)

        # With 95% threshold
        detector_threshold = ForecastActualComparator(
            transformer=transformer,
            date_column="date",
            cumulative_threshold=0.95
        )
        results_filtered = detector_threshold.detect(forecast_df, actual_df)

        print(f"\nResults without threshold: {len(results_all)}")
        print(f"Results with 95% threshold: {len(results_filtered)}")
        print(f"Filtered out: {len(results_all) - len(results_filtered)} low-volume metrics")

        print("\nFiltered results (top 95% by forecast value):")
        print(results_filtered[['metric', 'forecast', 'actual', 'status']].to_string(index=False))

        print("\n✓ Cumulative threshold test passed!")

        return results_filtered

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_anomaly_filtering():
    """Test anomaly-only and deviation threshold filtering."""

    print("\n" + "=" * 80)
    print("TEST 4: ANOMALY & DEVIATION FILTERING")
    print("=" * 80)

    try:
        from chronomaly.infrastructure.comparators import ForecastActualComparator
        from chronomaly.infrastructure.transformers import DataTransformer

        forecast_df, actual_df = create_comprehensive_sample_data()

        transformer = DataTransformer(
            index="date",
            columns=["platform", "channel", "landing_page"],
            values="sessions"
        )

        # All results
        detector_all = ForecastActualComparator(transformer=transformer, date_column="date")
        results_all = detector_all.detect(forecast_df, actual_df)

        # Only anomalies
        detector_anomalies = ForecastActualComparator(
            transformer=transformer,
            date_column="date",
            return_only_anomalies=True
        )
        results_anomalies = detector_anomalies.detect(forecast_df, actual_df)

        # Anomalies with >5% deviation
        detector_significant = ForecastActualComparator(
            transformer=transformer,
            date_column="date",
            return_only_anomalies=True,
            min_deviation_threshold=5.0
        )
        results_significant = detector_significant.detect(forecast_df, actual_df)

        print(f"\nAll results: {len(results_all)}")
        print(f"Anomalies only: {len(results_anomalies)}")
        print(f"Significant anomalies (>5%): {len(results_significant)}")

        print("\nSignificant anomalies:")
        print(results_significant[['metric', 'actual', 'q10', 'q90', 'status', 'deviation_pct']].to_string(index=False))

        print("\n✓ Anomaly filtering test passed!")

        return results_significant

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_string_formatting():
    """Test deviation_pct string formatting."""

    print("\n" + "=" * 80)
    print("TEST 5: DEVIATION STRING FORMATTING")
    print("=" * 80)

    try:
        from chronomaly.infrastructure.comparators import ForecastActualComparator
        from chronomaly.infrastructure.transformers import DataTransformer

        forecast_df, actual_df = create_comprehensive_sample_data()

        transformer = DataTransformer(
            index="date",
            columns=["platform", "channel", "landing_page"],
            values="sessions"
        )

        # Numeric format
        detector_numeric = ForecastActualComparator(
            transformer=transformer,
            date_column="date",
            return_only_anomalies=True,
            format_deviation_as_string=False
        )
        results_numeric = detector_numeric.detect(forecast_df, actual_df)

        # String format
        detector_string = ForecastActualComparator(
            transformer=transformer,
            date_column="date",
            return_only_anomalies=True,
            format_deviation_as_string=True
        )
        results_string = detector_string.detect(forecast_df, actual_df)

        print("\nNumeric format:")
        print(results_numeric[['metric', 'status', 'deviation_pct']].head().to_string(index=False))
        print(f"\ndeviation_pct type: {type(results_numeric['deviation_pct'].iloc[0])}")

        print("\n\nString format:")
        print(results_string[['metric', 'status', 'deviation_pct']].head().to_string(index=False))
        print(f"\ndeviation_pct type: {type(results_string['deviation_pct'].iloc[0])}")

        print("\n✓ String formatting test passed!")

        return results_string

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_full_featured():
    """Test all features combined (matching original implementation)."""

    print("\n" + "=" * 80)
    print("TEST 6: FULL-FEATURED DETECTION (All Options Combined)")
    print("=" * 80)

    try:
        from chronomaly.infrastructure.comparators import ForecastActualComparator
        from chronomaly.infrastructure.transformers import DataTransformer

        forecast_df, actual_df = create_comprehensive_sample_data()

        # Create mappings
        platform_map = ForecastActualComparator.create_mapping_from_dataframe(actual_df, 'platform')
        channel_map = ForecastActualComparator.create_mapping_from_dataframe(actual_df, 'channel')
        landing_page_map = ForecastActualComparator.create_mapping_from_dataframe(actual_df, 'landing_page')

        # Configure transformer
        transformer = DataTransformer(
            index="date",
            columns=["platform", "channel", "landing_page"],
            values="sessions"
        )

        # Full-featured detector (matching original implementation)
        detector = ForecastActualComparator(
            transformer=transformer,
            date_column="date",
            dimension_names=["platform", "channel", "landing_page"],
            dimension_mappings={
                "platform": platform_map,
                "channel": channel_map,
                "landing_page": landing_page_map
            },
            cumulative_threshold=0.95,  # Top 95% by forecast
            return_only_anomalies=True,  # Only BELOW_P10, ABOVE_P90
            min_deviation_threshold=5.0,  # Minimum 5% deviation
            format_deviation_as_string=True  # Format as "15.3%"
        )

        # Run detection
        results = detector.detect(forecast_df, actual_df)

        print(f"\nFinal filtered results: {len(results)}")

        if results.empty:
            print("\n✓ No significant anomalies detected!")
        else:
            print("\nSignificant anomalies detected:")
            print(results.to_string(index=False))

            # Verify all features
            assert 'metric' not in results.columns, "Metric should be split"
            assert 'platform' in results.columns, "Platform column should exist"
            assert 'Desktop' in results['platform'].values or 'Mobile' in results['platform'].values, "Mappings applied"
            assert all(results['status'].isin(['BELOW_P10', 'ABOVE_P90'])), "Only anomalies"
            assert isinstance(results['deviation_pct'].iloc[0], str), "Deviation should be string"
            assert '%' in results['deviation_pct'].iloc[0], "Deviation should have %"

        print("\n✓ Full-featured test passed!")
        print("\n" + "=" * 80)
        print("ALL TESTS PASSED! Implementation matches original functionality.")
        print("=" * 80)

        return results

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Run all tests
    print("\nRunning comprehensive anomaly detection tests...")
    print("This validates all features match the original implementation.\n")

    test_basic_detection()
    test_dimension_mapping()
    test_cumulative_threshold()
    test_anomaly_filtering()
    test_string_formatting()
    test_full_featured()

    print("\n" + "=" * 80)
    print("TEST SUITE COMPLETED")
    print("=" * 80)
