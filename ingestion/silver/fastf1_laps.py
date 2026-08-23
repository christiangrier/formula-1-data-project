import logging
import os
from pathlib import Path
import duckdb
import pandas as pd
from dotenv import load_dotenv
from ingestion.silver.helpers import log_silver_summary, nanoseconds_to_seconds, write_to_silver_fastf1

logger = logging.getLogger(__name__)

_NS_TIME_COLUMNS = [
    "time",
    "lap_time",
    "pit_out_time",
    "pit_in_time",
    "sector1_time",
    "sector2_time",
    "sector3_time",
    "sector1_session_time",
    "sector2_session_time",
    "sector3_session_time",
    "lap_start_time",
]

def clean_fastf1_laps(df: pd.DataFrame) -> pd.DataFrame:
    for col in _NS_TIME_COLUMNS:
        if col in df.columns:
            df[f"{col}_seconds"] = nanoseconds_to_seconds(df[col])
            df = df.drop(columns=[col])
    
    df["lap_start_date"] = pd.to_datetime(df["lap_start_date"], utc=True, errors="coerce")
    for col in ["lap_number", "stint", "tyre_life", "position"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    df["deleted"] = df["deleted"].astype("boolean")
    df["ingested_at"] = pd.to_datetime(df["ingested_at"], utc=True)
    df["abbreviation"] = df["driver"]
    df["team"] = (df["team"].str.strip().str.lower().str.replace(" ", "_", regex=False))
    df["deleted_reason"] = df["deleted_reason"].replace("", None)
    df["track_status"] = df["track_status"].replace("", None)
    df["compound"] = df["compound"].fillna("UNKNOWN")

    before = len(df)
    df = df.drop_duplicates(subset=["season", "round", "driver", "lap_number"], keep="last")
    dupes = before - len(df)
    if dupes:
        logger.warning("Dropped %d duplicate rows on (season, round, driver, lap_number)", dupes)

    return df

def run(con: duckdb.DuckDBPyConnection, year: int, round_number: int) -> None:
    table = "fastf1_laps"
    logger.info("Reading bronze.%s for round %d", table, round_number)
        
    df = con.execute("SELECT * FROM bronze.fastf1_laps WHERE season = ? AND round = ?", [year, round_number]).df()
    bronze_count = len(df)
    
    logger.info("Cleaning %d rows", bronze_count)
    df = clean_fastf1_laps(df)
    
    write_to_silver_fastf1(df, con, table, year, round_number)
    log_silver_summary(table, bronze_count, len(df))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")

    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env")

    db_path = os.getenv("DUCKDB_PATH", "data/f1_local.duckdb")

    with duckdb.connect(str(repo_root / db_path)) as con:
        run(con)