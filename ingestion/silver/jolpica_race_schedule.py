import logging
import os
from pathlib import Path
import duckdb
import pandas as pd
from dotenv import load_dotenv
from ingestion.silver.helpers import log_silver_summary, write_to_silver

logger = logging.getLogger(__name__)

SESSION_COLUMNS = [
    ("race_date", "race_start_time", "race_datetime"),
    ("fp1_date", "fp1_time", "fp1_datetime"),
    ("fp2_date", "fp2_time", "fp2_datetime"),
    ("fp3_date", "fp3_time", "fp3_datetime"),
    ("sprint_qualy_date", "sprint_qualy_time", "sprint_qualy_datetime"),
    ("qualy_date", "qualy_time", "qualy_datetime")
]

def combine_date_time(date_series: pd.Series, time_series: pd.Series) -> pd.Series:
    combined = date_series.str.strip() + "T" + time_series.str.strip()
    return pd.to_datetime(combined, utc=True, errors="coerce")

def clean_race_schedule(df: pd.DataFrame) -> pd.DataFrame:
    cols_to_drop = []
    for date_col, time_col, output_col in SESSION_COLUMNS:
        if date_col in df.columns and time_col in df.columns:
            df[output_col] = combine_date_time(df[date_col], df[time_col])
            cols_to_drop.extend([date_col, time_col])
        else:
            logger.warning("Expected columns %r and %r not found — skipping %r", date_col, time_col, output_col)
    
    df = df.drop(columns=cols_to_drop)

    df["ingested_at"] = pd.to_datetime(df["ingested_at"], utc=True)
    df["race_name"] = df["race_name"].fillna("Unknown Race")
    df["circuit"] = df["circuit"].fillna("Unknown Circuit")

    before = len(df)
    df = df.drop_duplicates(subset=["season", "round"], keep="last")
    dupes = before - len(df)
    if dupes:
        logger.warning("Dropped %d duplicate rows on (season, round)", dupes)
 
    return df

def run(con: duckdb.DuckDBPyConnection) -> None:
    table = "jolpica_race_schedule"
    logger.info("Reading bronze.%s", table)
    df = con.execute("SELECT * FROM bronze.jolpica_race_schedule").df()
    bronze_count = len(df)
 
    logger.info("Cleaning %d rows", bronze_count)
    df = clean_race_schedule(df)
 
    write_to_silver(df, con, table)
    log_silver_summary(table, bronze_count, len(df))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")
 
    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env")
 
    db_path = os.getenv("DUCKDB_PATH", "data/f1_local.duckdb")
 
    with duckdb.connect(str(repo_root / db_path)) as con:
        run(con)