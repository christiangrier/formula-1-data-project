import logging
import os
from pathlib import Path
import duckdb
import pandas as pd
from dotenv import load_dotenv
from ingestion.silver.helpers import log_silver_summary, nanoseconds_to_seconds, write_to_silver_fastf1

logger = logging.getLogger(__name__)

def clean_fastf1_results(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop(columns=["headshot_url"], errors="ignore")
    df["ingested_at"] = pd.to_datetime(df["ingested_at"], utc=True)
    df["position"] = pd.to_numeric(df["position"], errors="coerce").astype("Int64")
    df["grid_position"] = pd.to_numeric(df["grid_position"], errors="coerce").astype("Int64")
    df["laps"] = pd.to_numeric(df["laps"], errors="coerce").astype("Int64")
    df["time_seconds"] = nanoseconds_to_seconds(df["time"])

    df = df.drop(columns=["time"])
    for col in ["q1", "q2", "q3"]:
        # df[f"{col}_seconds"] = nanoseconds_to_seconds(df[col])
        df = df.drop(columns=[col])
    df = df.drop(columns=["country_code"])

    df["driver_id"] = (df["driver_id"].str.strip().str.lower().str.replace(" ", "_", regex=False))
    df["team_id"] = (df["team_id"].str.strip().str.lower().str.replace(" ", "_", regex=False))

    df["status"] = df["status"].fillna("Unknown")
    df["classified_position"] = df["classified_position"].fillna("Unknown")
    df["first_name"] = df["first_name"].fillna("Unknown")
    df["last_name"] = df["last_name"].fillna("Unknown")
    df["full_name"] = df["full_name"].fillna("Unknown Driver")

    before = len(df)
    df = df.drop_duplicates(subset=["season", "round", "driver_id"], keep="last")
    dupes = before - len(df)
    if dupes:
        logger.warning("Dropped %d duplicate rows on (season, round, driver_id)", dupes)

    return df

def run(con: duckdb.DuckDBPyConnection, year:int, round_number:int) -> None:
    table = "fastf1_results"
    logger.info("Reading bronze.%s for round %d", table, round_number)
    
    df = con.execute("SELECT * FROM bronze.fastf1_results WHERE season = ? AND round = ?", [year, round_number]).df()
    bronze_count = len(df)

    logger.info("Cleaning %d rows", bronze_count)
    df = clean_fastf1_results(df)

    write_to_silver_fastf1(df, con, table, year, round_number)
    log_silver_summary(table, bronze_count, len(df))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")

    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env")

    db_path = os.getenv("DUCKDB_PATH", "data/f1_local.duckdb")

    with duckdb.connect(str(repo_root / db_path)) as con:
        run(con)