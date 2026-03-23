import logging
import os
from pathlib import Path
import duckdb
import pandas as pd
from dotenv import load_dotenv
from ingestion.silver.helpers import log_silver_summary, write_to_silver

logger = logging.getLogger(__name__)

def parse_duration_to_seconds(val: str) -> float | None:
    if pd.isna(val) or str(val).strip() == "":
        return None
    val = str(val).strip()
    try:
        if ":" in val:
            parts = val.split(":")
            return float(parts[0]) * 60 + float(parts[1])
        return float(val)
    except (ValueError, IndexError):
        logger.warning("Could not parse pit_stop_duration value: %r", val)
        return None

def clean_pit_stops(df: pd.DataFrame) -> pd.DataFrame:
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d").dt.date
    df["ingested_at"] = pd.to_datetime(df["ingested_at"], utc=True)
    df["lap_pitted"] = pd.to_numeric(df["lap_pitted"], errors="coerce").astype("Int64")
    df["stop_num"] = pd.to_numeric(df["stop_num"], errors="coerce").astype("Int64")
    df["pit_in_time"] = pd.to_datetime(df["pit_in_time"], format="%H:%M:%S", errors="coerce").dt.time
    df["pit_stop_duration"] = df["pit_stop_duration"].apply(parse_duration_to_seconds)
    df["driver_id"] = (df["driver_id"].str.strip().str.lower().str.replace(" ", "_", regex=False))

    before = len(df)
    df = df.dropna(subset=["pit_stop_duration"])
    dropped = before - len(df)
    if dropped:
        logger.warning("Dropped %d rows with unparseable or missing pit_stop_duration", dropped)

    before = len(df)
    df = df.drop_duplicates(subset=["season", "round", "driver_id", "stop_num"], keep="last")
    dupes = before - len(df)
    if dupes:
        logger.warning("Dropped %d duplicate rows on (season, round, driver_id, stop_num)", dupes)
 
    return df

def run(con: duckdb.DuckDBPyConnection) -> None:
    table = "jolpica_pit_stops"
    logger.info("Reading bronze.%s", table)
    df = con.execute("SELECT * FROM bronze.jolpica_pit_stops").df()
    bronze_count = len(df)
 
    logger.info("Cleaning %d rows", bronze_count)
    df = clean_pit_stops(df)
 
    write_to_silver(df, con, table)
    log_silver_summary(table, bronze_count, len(df))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")
 
    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env")
 
    db_path = os.getenv("DUCKDB_PATH", "data/f1_local.duckdb")
 
    with duckdb.connect(str(repo_root / db_path)) as con:
        run(con)