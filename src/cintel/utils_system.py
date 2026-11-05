"""utils_system.py.

Shared helper functions
for the system-metrics monitoring domain.

Used by:
- src/cintel/signal_design.py (cintel-03)
- src/cintel/rolling_monitor.py (cintel-04)
- src/cintel/drift_detector.py (cintel-05)
- src/cintel/continuous_intelligence.py (cintel-06)
- app.py in each of the above

All four projects share the same schema (requests, errors,
total_latency_ms), so their functions live together here.
"""

from pathlib import Path

import polars as pl


def load_clickstream(data_file: Path) -> pl.DataFrame:
    """Read raw clickstream metrics from a CSV file.

    Used for plain snapshots (cintel-03, cintel-06) and for the reference/
    current period files in cintel-05, which share the same three columns.
    """
    return pl.read_csv(data_file, has_header=True).with_columns(
        pl.col("event_time")
        .str.replace(" UTC", "")
        .str.to_datetime("%Y-%m-%d %H:%M:%S")
    )


def load_timeseries_metrics(data_file: Path) -> pl.DataFrame:
    """Read time-series system metrics from a CSV file, sorted by timestamp."""
    return pl.read_csv(data_file).sort("timestamp")


# === cintel-03: SIGNAL DESIGN ===


def design_signals(df: pl.DataFrame) -> pl.DataFrame:
    """Add derived signal columns: error_rate, avg_latency_ms, throughput.

    Per-request signals are only computed when requests > 0, to avoid
    dividing by zero; otherwise they default to 0.0.
    """
    is_requests_positive = pl.col("requests") > 0

    return df.with_columns(
        [
            pl.when(is_requests_positive)
            .then(pl.col("errors") / pl.col("requests"))
            .otherwise(0.0)
            .alias("error_rate"),
            pl.when(is_requests_positive)
            .then(pl.col("total_latency_ms") / pl.col("requests"))
            .otherwise(0.0)
            .alias("avg_latency_ms"),
            pl.col("requests").alias("throughput"),
        ]
    ).select(
        [
            "requests",
            "errors",
            "total_latency_ms",
            "error_rate",
            "avg_latency_ms",
            "throughput",
        ]
    )


# === cintel-03 Customized: Clickstream ===

# df = pl.read_csv('data/2020-Jan.csv').with_columns(
#     pl.col("event_time").str.replace(" UTC", "").str.to_datetime("%Y-%m-%d %H:%M:%S")
# )
# # print(df.head(50))


def design_clickstream_metrics(df: pl.DataFrame) -> pl.DataFrame:
    """Add derived signal columns for clickstream data.

    This is a placeholder for any clickstream-specific signal design logic.
    """
    # Example: Add a signal for user session duration

    session_metrics = (
        df.group_by("user_session")
        .agg(
            [
                pl.col("event_time").max().alias("session_end_time"),
                pl.col("event_time").min().alias("session_start_time"),
                (pl.col("event_time").max() - pl.col("event_time").min())
                .dt.to_string()
                .alias("session_duration"),
                pl.len().alias("total_events"),
                pl.col("user_session")
                .filter(pl.col("event_type") == "view")
                .len()
                .alias("views"),
                pl.col("user_session")
                .filter(pl.col("event_type") == "cart")
                .len()
                .alias("carts"),
                pl.col("user_session")
                .filter(pl.col("event_type") == "remove_from_cart")
                .len()
                .alias("remove_from_carts"),
                pl.col("user_session")
                .filter(pl.col("event_type") == "purchase")
                .len()
                .alias("purchases"),
            ]
        )
        .select(
            "user_session",
            "session_start_time",
            "session_end_time",
            "session_duration",
            "total_events",
            "views",
            "carts",
            "remove_from_carts",
            "purchases",
        )
    )

    session_metrics = session_metrics.with_columns(
        [
            # FUNNEL STEP 1: Cart-to-View Ratio (Micro-conversion)
            pl.when(pl.col("views") > 0)
            .then(pl.col("carts") / pl.col("views"))
            .otherwise(0.0)
            .alias("cart_to_view_ratio"),
            # FUNNEL STEP 2: Purchase-to-Cart Ratio (Checkout completion efficiency)
            pl.when(pl.col("carts") > 0)
            .then(pl.col("purchases") / pl.col("carts"))
            .otherwise(0.0)
            .alias("purchase_to_cart_ratio"),
            # FUNNEL STEP 3: Overall Session Conversion Rate (Total Funnel Yield)
            pl.when(pl.col("views") > 0)
            .then(pl.col("purchases") / pl.col("views"))
            .otherwise(0.0)
            .alias("session_conversion_rate"),
            # FUNNEL STEP 4: Cart Abandonment Flags
            pl.when((pl.col("carts") > 0) & (pl.col("purchases") == 0))
            .then(True)
            .otherwise(False)
            .alias("abandoned_cart"),
        ]
    )
    return session_metrics.select(
        "user_session",
        "session_start_time",
        "session_end_time",
        "session_duration",
        "total_events",
        "views",
        "carts",
        "remove_from_carts",
        "purchases",
        "cart_to_view_ratio",
        "purchase_to_cart_ratio",
        "session_conversion_rate",
        "abandoned_cart",
    )


# === cintel-04: ROLLING MONITORING ===


def compute_rolling_metrics(df: pl.DataFrame, window_size: int) -> pl.DataFrame:
    """Add rolling-mean columns for requests, errors, and total_latency_ms.

    Assumes df is already sorted by timestamp (see load_timeseries_metrics).
    """
    return df.with_columns(
        [
            pl.col("requests").rolling_mean(window_size).alias("requests_rolling_mean"),
            pl.col("errors").rolling_mean(window_size).alias("errors_rolling_mean"),
            pl.col("total_latency_ms")
            .rolling_mean(window_size)
            .alias("latency_rolling_mean"),
        ]
    )


# === cintel-05: DRIFT DETECTION ===


def compute_drift_summary(
    reference_df: pl.DataFrame,
    current_df: pl.DataFrame,
    requests_threshold: float,
    errors_threshold: float,
    latency_threshold: float,
) -> pl.DataFrame:
    """Compare mean requests/errors/latency between two periods and flag drift.

    Returns a one-row summary with each period's averages, the difference
    between them, and a boolean drift flag per metric.
    """
    reference_summary = reference_df.select(
        [
            pl.col("requests").mean().alias("reference_avg_requests"),
            pl.col("errors").mean().alias("reference_avg_errors"),
            pl.col("total_latency_ms").mean().alias("reference_avg_latency_ms"),
        ]
    )
    current_summary = current_df.select(
        [
            pl.col("requests").mean().alias("current_avg_requests"),
            pl.col("errors").mean().alias("current_avg_errors"),
            pl.col("total_latency_ms").mean().alias("current_avg_latency_ms"),
        ]
    )
    combined = pl.concat(
        [reference_summary, current_summary], how="horizontal"
    ).with_columns(
        [
            (pl.col("current_avg_requests") - pl.col("reference_avg_requests"))
            .round(2)
            .alias("requests_mean_difference"),
            (pl.col("current_avg_errors") - pl.col("reference_avg_errors"))
            .round(2)
            .alias("errors_mean_difference"),
            (pl.col("current_avg_latency_ms") - pl.col("reference_avg_latency_ms"))
            .round(2)
            .alias("latency_mean_difference_ms"),
        ]
    )

    return combined.with_columns(
        [
            (pl.col("requests_mean_difference").abs() > requests_threshold).alias(
                "requests_is_drifting_flag"
            ),
            (pl.col("errors_mean_difference").abs() > errors_threshold).alias(
                "errors_is_drifting_flag"
            ),
            (pl.col("latency_mean_difference_ms").abs() > latency_threshold).alias(
                "latency_is_drifting_flag"
            ),
        ]
    )
