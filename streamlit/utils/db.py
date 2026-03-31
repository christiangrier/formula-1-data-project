"""
Database connection helper.

Single function used by every page — swap the connection string here
when migrating to Stage 2 (Databricks).
"""

import duckdb
import streamlit as st
from pathlib import Path


def get_db_path() -> Path:
    # __file__ = streamlit/utils/db.py
    # parents[0] = utils/, parents[1] = streamlit/, parents[2] = repo root
    return Path(__file__).resolve().parents[2] / "dbt" / "data" / "f1_local.duckdb"


@st.cache_resource
def get_connection() -> duckdb.DuckDBPyConnection:
    """
    Return a cached read-only DuckDB connection.
    Cached at the resource level — one connection shared across all reruns.
    """
    db_path = get_db_path()
    if not db_path.exists():
        st.error(f"Database not found at {db_path}. Run the ingestion pipeline first.")
        st.stop()
    return duckdb.connect(str(db_path), read_only=True)
