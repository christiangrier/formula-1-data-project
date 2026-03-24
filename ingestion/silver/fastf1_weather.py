import logging
import os
from pathlib import Path
import duckdb
import pandas as pd
from dotenv import load_dotenv
from ingestion.silver.helpers import log_silver_summary, nanoseconds_to_seconds, write_to_silver

logger = logging.getLogger(__name__)

def clean_fastf1_weather(df: pd.DataFrame) -> pd.DataFrame:
    df["time_seconds"] = nanoseconds_to_seconds(df["time"])
    df = df.drop(columns=["time"])
    df["ingested_at"] = pd.to_datetime(df["ingested_at"], utc=True)
    df = df.sort_values(["season", "round", "time_seconds"])
    df["air_temp"] = df.groupby(["season", "round"])["air_temp"].ffill()
    df["track_temp"] = df.groupby(["season", "round"])["track_temp"].ffill()

    for col in ["air_temp", "track_temp"]:
        remaining_nulls = df[col].isna().sum()
        if remaining_nulls:
            logger.warning("%d null values remain in %s after forward-fill", remaining_nulls, col)

    before = len(df)
    df = df.drop_duplicates(subset=["season", "round", "time_seconds"], keep="last")
    dupes = before - len(df)
    if dupes:
        logger.warning("Dropped %d duplicate rows on (season, round, time_seconds)", dupes)

    return df

def run(con: duckdb.DuckDBPyConnection) -> None:
    table = "fastf1_weather"
    logger.info("Reading bronze.%s", table)
    df = con.execute("SELECT * FROM bronze.fastf1_weather").df()
    bronze_count = len(df)

    logger.info("Cleaning %d rows", bronze_count)
    df = clean_fastf1_weather(df)

    write_to_silver(df, con, table)
    log_silver_summary(table, bronze_count, len(df))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")

    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env")

    db_path = os.getenv("DUCKDB_PATH", "data/f1_local.duckdb")

    with duckdb.connect(str(repo_root / db_path)) as con:
        run(con)