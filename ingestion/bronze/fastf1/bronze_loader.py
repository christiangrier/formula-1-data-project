import os
import duckdb
import logging
from pathlib import Path
from dotenv import load_dotenv

ROOT_REPO = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_REPO / ".env")

logger = logging.getLogger(__name__)

ENDPOINTS = [
    "laps",
    "results",
    "telemetry",
    "weather"
]

def config_s3(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"""
        SET s3_access_key_id = '{os.getenv("AWS_ACCESS_KEY_ID")}';
        SET s3_secret_access_key = '{os.getenv("AWS_SECRET_ACCESS_KEY")}';
        SET s3_region = '{os.getenv("AWS_REGION")}';
        SET http_timeout = 1200;
    """
    )
    logger.info("Duckdb connection config for S3 success")

def load_table(con: duckdb.DuckDBPyConnection, s3_path: str, table_name: str, year: int, round_number: int) -> None:
    table_exists = con.execute(
        """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema || '.' || table_name = ?
        """,
        [table_name],
    ).fetchone()[0] > 0

    if not table_exists:
        con.execute(f"""
            CREATE TABLE {table_name} AS
            SELECT * FROM read_parquet('{s3_path}')
            LIMIT 0
        """)
        logger.info(f"{table_name} did not exist, created empty table from schema")

    con.execute(
        f"DELETE FROM {table_name} WHERE season = ? AND round = ?",
        [year, round_number],
    )
    con.execute(f"""
        INSERT INTO {table_name}
        SELECT * FROM read_parquet('{s3_path}')
    """)

    row_count = con.execute(
        f"SELECT COUNT(*) FROM {table_name} WHERE season = ? AND round = ?",
        [year, round_number],
    ).fetchone()[0]

    total_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

    logger.info(
        f"{table_name}: {row_count} rows loaded for round {round_number} "
        f"(table total={total_count})"
    )


def load_fastf1_bronze(con: duckdb.DuckDBPyConnection, year: int, round_number: int, bucket: str = None) -> None:
    if bucket is None:
        bucket = os.getenv("S3_BUCKET_RAW")
    
    config_s3(con)

    for endpoint in ENDPOINTS:
        s3_path = f"s3://{bucket}/fastf1/{year}/{round_number}/{endpoint}.parquet"
        table_name = f"bronze.fastf1_{endpoint}"
        logger.info(f"Loading {s3_path} to {table_name}")
        load_table(con, s3_path, table_name, year, round_number)

def verify_bronze_tables(con: duckdb.DuckDBPyConnection) -> None:

    for endpoint in ENDPOINTS:
        table_name = f"bronze.fastf1_{endpoint}"
        try:
            row_count = con.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]
 
            round_count = con.execute(
                f"SELECT COUNT(DISTINCT round) FROM {table_name}"
            ).fetchone()[0]
 
            print(
                f"{table_name:<40} "
                f"rows={row_count:<6} "
                f"rounds={round_count}"
            )
        except Exception as e:
            print(f"{table_name:<40} ERROR: {e}")