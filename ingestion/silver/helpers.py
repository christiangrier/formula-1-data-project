import logging 
import pandas as pd
import duckdb

logger = logging.getLogger(__name__)

_NS_PER_SECONDS = 1_000_000_000

def nanoseconds_to_seconds(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce") / _NS_PER_SECONDS

def write_to_silver_fastf1(df: pd.DataFrame, con: duckdb.DuckDBPyConnection, table_name: str, year: int, round_number: int) -> None:
    qualified = f"silver.{table_name}"

    con.execute("CREATE SCHEMA IF NOT EXISTS silver")

    table_exists = con.execute(
        """
        SELECT COUNT(*) FROM duckdb_tables()
        WHERE schema_name = 'silver' AND table_name = ?
        """,
        [table_name],
    ).fetchone()[0] > 0

    if not table_exists:
        con.execute(f"CREATE TABLE {qualified} AS SELECT * FROM df LIMIT 0")
        logger.info("%s did not exist, created empty table from schema", qualified)
    
    con.execute(f"DELETE FROM {qualified} WHERE season = ? AND round = ?", [year, round_number])
    con.execute(f"INSERT INTO {qualified} SELECT * FROM df")
    logger.info("Written %d rows to %s for round %d", len(df), qualified, round_number)

def write_to_silver(df: pd.DataFrame, con: duckdb.DuckDBPyConnection, table_name: str) -> None:
    qualified = f"silver.{table_name}"

    con.execute("CREATE SCHEMA IF NOT EXISTS silver")
    con.execute(f"CREATE OR REPLACE TABLE {qualified} AS SELECT * FROM df")
    logger.info("Written %d rows to %s", len(df), qualified)


def log_silver_summary(table_name: str, bronze_count: int, silver_count: int) -> None:
    dropped = bronze_count - silver_count
    pct = (dropped / bronze_count * 100) if bronze_count > 0 else 0.0
    logger.info(
        "[%s] bronze=%d  silver=%d  dropped=%d (%.1f%%)",
        table_name,
        bronze_count,
        silver_count,
        dropped,
        pct,
    )

    if pct > 10:
        logger.warning(
            "[%s] More than 10%% of rows dropped during cleaning — review cleaning logic.",
            table_name
        )