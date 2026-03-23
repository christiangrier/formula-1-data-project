import logging
import os
from pathlib import Path
import duckdb
import pandas as pd
from dotenv import load_dotenv
from ingestion.silver.helpers import log_silver_summary, write_to_silver

logger = logging.getLogger(__name__)

def clean_driver_standings(df: pd.DataFrame) -> pd.DataFrame:
    df["driver_dob"] = pd.to_datetime(df["driver_dob"], format="%Y-%m-%d").dt.date
    df["ingested_at"] = pd.to_datetime(df["ingested_at"], utc=True)
    df["driver_id"] = (df["driver_id"].str.strip().str.lower().str.replace(" ", "_", regex=False))
    df["constructor"] = (df["constructor"].str.strip().str.lower().str.replace(" ", "_", regex=False))

    df["driver_country"] = df["driver_country"].fillna("Unknown")
    df["constructor_country"] = df["constructor_country"].fillna("Unknown")
    df["driver_code"] = df["driver_code"].fillna("UNK")
    df["driver_name"] = df["driver_name"].fillna("Unknown Driver")

    before = len(df)
    df = df.drop_duplicates(subset=["season", "round", "driver_id"], keep="last")
    dupes = before - len(df)
    if dupes:
        logger.warning("Dropped %d duplicate rows on (season, round, driver_id)", dupes)

    return df

def run(con: duckdb.DuckDBPyConnection) -> None:
    table = "jolpica_driver_standings"
    logger.info("Reading bronze.%s", table)
    df = con.execute("SELECT * FROM bronze.jolpica_driver_standings").df()
    bronze_count = len(df)
 
    logger.info("Cleaning %d rows", bronze_count)
    df = clean_driver_standings(df)
 
    write_to_silver(df, con, table)
    log_silver_summary(table, bronze_count, len(df))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")
 
    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env")
 
    db_path = os.getenv("DUCKDB_PATH", "data/f1_local.duckdb")
 
    with duckdb.connect(str(repo_root / db_path)) as con:
        run(con)