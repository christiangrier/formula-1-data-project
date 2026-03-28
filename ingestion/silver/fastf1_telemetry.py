import logging
import os
from pathlib import Path
import duckdb
import pandas as pd
from dotenv import load_dotenv
from ingestion.silver.helpers import log_silver_summary, nanoseconds_to_seconds, write_to_silver

logger = logging.getLogger(__name__)

def clean_fastf1_telemetry(df: pd.DataFrame) -> pd.DataFrame:
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    df["session_time_seconds"] = nanoseconds_to_seconds(df["session_time"])
    df = df.drop(columns=["session_time"])
    df["lap_time_seconds"] = nanoseconds_to_seconds(df["time"])
    df = df.drop(columns=["time"])
    df["ingested_at"] = pd.to_datetime(df["ingested_at"], utc=True)

    df["abbreviation"] = df["driver"]
    df["team"] = (df["team"].str.strip().str.lower().str.replace(" ", "_", regex=False))
    df["driver_ahead"] = df["driver_ahead"].replace("", None)
    df["status"] = df["status"].replace("", None)

    before = len(df)
    df = df.dropna(subset=["distance"])
    dropped = before - len(df)
    if dropped:
        logger.warning("Dropped %d rows with null distance", dropped)

    before = len(df)
    df = df.drop_duplicates(subset=["season", "round", "driver", "lap_number", "date"], keep="last")
    dupes = before - len(df)
    if dupes:
        logger.warning("Dropped %d duplicate rows on (season, round, driver, lap_number, date)", dupes)

    return df

def run(con: duckdb.DuckDBPyConnection) -> None:
    table = "fastf1_telemetry"
    logger.info("Reading bronze.%s", table)
    df = con.execute("SELECT * FROM bronze.fastf1_telemetry").df()
    bronze_count = len(df)

    logger.info("Cleaning %d rows", bronze_count)
    df = clean_fastf1_telemetry(df)

    write_to_silver(df, con, table)
    log_silver_summary(table, bronze_count, len(df))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")

    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env")

    db_path = os.getenv("DUCKDB_PATH", "data/f1_local.duckdb")

    with duckdb.connect(str(repo_root / db_path)) as con:
        run(con)