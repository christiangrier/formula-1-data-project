"""
Full ingestion orchestration: API → Bronze (S3 + DuckDB) → Silver (DuckDB)

Usage:
    python -m ingestion.run_pipeline --year 2026 --round 3

The script runs five stages in order:
    1. Jolpica API   → S3 (year-level endpoints + round-level pit stops)
    2. FastF1 API    → S3 (laps, results, weather, telemetry for the round)
    3. S3            → bronze.* DuckDB tables (Jolpica + FastF1)
    4. bronze.*      → silver.* DuckDB tables (9 cleaning scripts)

Run `dbt run` separately afterwards to rebuild the gold mart tables.
"""

import argparse
import logging
import os
import sys
import duckdb
from pathlib import Path
from dotenv import load_dotenv

# ── Repo setup ─────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pipeline")

# ── Imports (after path is set) ─────────────────────────────────────────────────
from ingestion.bronze.jolpica.race_results import get_race_results
from ingestion.bronze.jolpica.driver_standings import get_driver_standings
from ingestion.bronze.jolpica.constructor_standings import get_constructor_standings
from ingestion.bronze.jolpica.race_schedule import get_season_race_data
from ingestion.bronze.jolpica.pit_stops import get_pit_stop_time_data
from ingestion.bronze.jolpica.writer import df_write_to_s3_raw
from ingestion.bronze.jolpica.bronze_loader import load_jolpica_bronze, verify_bronze_tables
from ingestion.bronze.fastf1.pipeline import fastf1_pipeline
from ingestion.bronze.fastf1.bronze_loader import load_fastf1_bronze, verify_bronze_tables as verify_fastf1_bronze

from ingestion.silver import (
    fastf1_laps,
    fastf1_results,
    fastf1_telemetry,
    fastf1_weather,
    jolpica_race_results,
    jolpica_driver_standings,
    jolpica_constructor_standings,
    jolpica_pit_stops,
    jolpica_race_schedule,
)

_SILVER_MODULES = [
    fastf1_laps,
    fastf1_results,
    fastf1_telemetry,
    fastf1_weather,
    jolpica_race_results,
    jolpica_driver_standings,
    jolpica_constructor_standings,
    jolpica_pit_stops,
    jolpica_race_schedule,
]

_JOLPICA_YEAR_ENDPOINTS = [
    (get_race_results,          "race_results"),
    (get_driver_standings,      "driver_standings"),
    (get_constructor_standings, "constructor_standings"),
    (get_season_race_data,      "race_schedule"),
]


# ── Stage functions ────────────────────────────────────────────────────────────

def stage_jolpica_api(year: int, round_number: int) -> None:
    """Fetch Jolpica data and write to S3."""
    logger.info("── Stage 1: Jolpica API → S3 ──")

    for fetch_fn, endpoint in _JOLPICA_YEAR_ENDPOINTS:
        logger.info("Fetching jolpica/%s for year %s", endpoint, year)
        try:
            df = fetch_fn(year)
            df_write_to_s3_raw(df, source="jolpica", year=year, endpoint=endpoint)
        except Exception as e:
            logger.error("Failed to fetch %s: %s", endpoint, e)
            raise

    logger.info("Fetching jolpica/pit_stops for year %s round %s", year, round_number)
    try:
        df = get_pit_stop_time_data(year, round_number)
        df_write_to_s3_raw(
            df, source="jolpica", year=year, endpoint=f"pit_stops/{round_number}"
        )
    except Exception as e:
        logger.error("Failed to fetch pit_stops: %s", e)
        raise

    logger.info("Stage 1 complete")


def stage_fastf1_api(year: int, round_number: int) -> None:
    """Fetch FastF1 session data and write to S3."""
    logger.info("── Stage 2: FastF1 API → S3 ──")
    fastf1_pipeline(year=year, round_number=round_number)
    logger.info("Stage 2 complete")


def stage_bronze_load(con: duckdb.DuckDBPyConnection, year: int) -> None:
    """Load S3 Parquet files into bronze.* DuckDB tables."""
    logger.info("── Stage 3: S3 → Bronze DuckDB ──")

    load_jolpica_bronze(con, year=year)
    load_fastf1_bronze(con, year=year)

    logger.info("Bronze table verification:")
    verify_bronze_tables(con)
    verify_fastf1_bronze(con)

    logger.info("Stage 3 complete")


def stage_silver(con: duckdb.DuckDBPyConnection) -> None:
    """Run all silver cleaning scripts against bronze.* tables."""
    logger.info("── Stage 4: Bronze → Silver DuckDB ──")

    for module in _SILVER_MODULES:
        name = module.__name__.split(".")[-1]
        logger.info("Cleaning %s", name)
        try:
            module.run(con)
        except Exception as e:
            logger.error("Silver cleaning failed for %s: %s", name, e)
            raise

    logger.info("Stage 4 complete")


# ── Main ──────────────────────────────────────────────────────────────────────

def run(year: int, round_number: int, start_from: int = 1) -> None:
    db_path = REPO_ROOT / os.getenv("DUCKDB_PATH", "dbt/data/f1_local.duckdb")

    logger.info("=" * 60)
    logger.info("F1 Ingestion Pipeline")
    logger.info("  Year:         %s", year)
    logger.info("  Round:        %s", round_number)
    logger.info("  Starting from stage %s", start_from)
    logger.info("  Database:     %s", db_path)
    logger.info("=" * 60)

    if start_from <= 1:
        stage_jolpica_api(year, round_number)

    if start_from <= 2:
        stage_fastf1_api(year, round_number)

    with duckdb.connect(str(db_path)) as con:
        if start_from <= 3:
            stage_bronze_load(con, year)

        if start_from <= 4:
            stage_silver(con)

    logger.info("=" * 60)
    logger.info("Pipeline complete. Run `dbt run` to rebuild gold marts.")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the F1 ingestion pipeline from API through to silver tables."
    )
    parser.add_argument("--year",  type=int, required=True, help="Season year (e.g. 2026)")
    parser.add_argument("--round", type=int, required=True, help="Race round number (e.g. 3)")
    parser.add_argument(
        "--start-from",
        type=int,
        default=1,
        choices=[1, 2, 3, 4],
        metavar="{1,2,3,4}",
        help=(
            "Skip earlier stages and start from a specific stage. "
            "1=Jolpica API (default), 2=FastF1 API, 3=Bronze load, 4=Silver clean"
        ),
    )
    args = parser.parse_args()

    try:
        run(year=args.year, round_number=args.round, start_from=args.start_from)
    except Exception as e:
        logger.error("Pipeline failed: %s", e)
        sys.exit(1)
