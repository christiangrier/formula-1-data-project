import logging 
import pandas as pd
import duckdb

logger = logging.getLogger(__name__)

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