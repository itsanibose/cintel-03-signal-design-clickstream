"""signal_design.py - Project script (example).

Author: Anindya Bose
Date: 2026-11-04

System Metrics Data

- Data is same clickstream data from online webstore.
- The data is structured and static for this example.
- Each row represents one observation of system behavior.
- The CSV file includes these columns:
  - event_time
  - event_type
  - product_id
  - category_id
  - category_code
  - brand
  - price
  - user_id
  - user_session


Purpose

- Read clickstream data (data/2020-Jan.csv) from a CSV (comma-separated values) file.
- Design useful signals from the raw measurements.
- Save the resulting signals as a new CSV artifact.
- Log the pipeline process to assist with debugging and transparency.

Questions to Consider

- What should we measure to understand system behavior?
- Which signals are more informative than the raw input values?
- How can derived signals help us detect problems more clearly?

Paths (relative to repo root)

    INPUT FILE: data/2020-Jan.csv
    OUTPUT FILE: artifacts/metrics.csv

Terminal command to run this file from the root project folder

    uv run python -m cintel.signal_design

DESIGN:

Use this file to first learn and then apply your skills.

Reusable functions that do the work are kept in a utils file.
We import functions and pass in what they need through their parentheses.
Shared utility functions can be imported into a Python
module or a reactive marimo notebook app.

Reusable visualization functions may come from sources such as eda-vizkit.

SKILLS:

- Reading CSV files into Polars DataFrames.
- Defining and using calculated measures.
- Logging for debugging and transparency.
- Designing signals based on domain-specific rules.
"""

# === DECLARE IMPORTS (packages we will use in this project) ===

# First from the Python standard library (no installation needed)
import logging
from pathlib import Path
import time
from typing import Final

from datafun_toolkit.logger import get_logger, log_header, log_path
import polars as pl

from cintel.utils_system import design_clickstream_metrics, load_clickstream

# === CONFIGURE LOGGER ONCE PER MODULE (FILE) ===

LOG: logging.Logger = get_logger("P3", level="DEBUG")

# === DECLARE GLOBAL CONSTANTS FOR FOLDER PATHS (directories) ===

ROOT_DIR: Final[Path] = Path.cwd()
DATA_DIR: Final[Path] = ROOT_DIR / "data"
ARTIFACTS_DIR: Final[Path] = ROOT_DIR / "artifacts"

# === DECLARE GLOBAL CONSTANTS FOR FILE PATHS ===

DATA_FILE: Final[Path] = DATA_DIR / "2020-Jan.csv"
OUTPUT_FILE: Final[Path] = ARTIFACTS_DIR / "metrics.csv"


# === DEFINE THE MAIN FUNCTION ===


def main() -> None:
    """Run the pipeline.

    log_header() logs a standard run header.
    log_path() logs repo-relative paths (privacy-safe).
    """
    log_header(LOG, "CINTEL")

    LOG.info("========================")
    LOG.info("START main()")
    LOG.info("========================")

    log_path(LOG, "ROOT_DIR", ROOT_DIR)
    log_path(LOG, "DATA_FILE", DATA_FILE)
    log_path(LOG, "OUTPUT_FILE", OUTPUT_FILE)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    log_path(LOG, "ARTIFACTS_DIR", ARTIFACTS_DIR)

    # ----------------------------------------------------
    # STEP 1: READ CSV DATA FILE INTO A POLARS DATAFRAME (TABLE)
    # ----------------------------------------------------
    start = time.perf_counter()  # Start timer for performance measurement

    df: pl.DataFrame = load_clickstream(DATA_FILE)

    LOG.info(f"Loaded {df.height} clickstream records")

    # ----------------------------------------------------
    # STEP 2: DESIGN SIGNALS FROM RAW METRICS
    # ----------------------------------------------------
    LOG.info("Designing behaviour metrics from the clickstream data...")

    clickstream_df: pl.DataFrame = design_clickstream_metrics(df)

    LOG.info(
        "Created signal columns: session_start_time, session_end_time, session_duration, views, carts, removes, purchases, total_events etc.."
    )
    LOG.info(f"Enhanced signals table has {clickstream_df.height} rows")

    # ----------------------------------------------------
    # STEP 3: SAVE THE SIGNALS TABLE AS AN ARTIFACT
    # ----------------------------------------------------
    clickstream_df.write_csv(OUTPUT_FILE)

    end = time.perf_counter()  # End timer for performance measurement
    elapsed_time = end - start
    LOG.info(f"Pipeline executed in {elapsed_time:.2f} seconds")
    LOG.info(f"Wrote clickstream metrics file: {OUTPUT_FILE}")

    LOG.info("========================")
    LOG.info("Pipeline executed successfully!")
    LOG.info("========================")
    LOG.info("END main()")


# === CONDITIONAL EXECUTION GUARD ===

if __name__ == "__main__":
    main()
