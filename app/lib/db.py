"""DuckDB connection — read-only singleton."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

_DEFAULT_DB = Path(__file__).parents[2] / "warehouse" / "cohort_compass.duckdb"


@st.cache_resource
def get_connection() -> duckdb.DuckDBPyConnection:
    """Return a cached read-only DuckDB connection."""
    db_path = os.getenv("DUCKDB_PATH", str(_DEFAULT_DB))
    # Resolve relative path from repo root (guards against CWD != repo root on Streamlit Cloud)
    if not Path(db_path).is_absolute():
        db_path = str(Path(__file__).parents[2] / db_path)
    return duckdb.connect(db_path, read_only=True)


def query(sql: str) -> "pd.DataFrame":  # noqa: F821
    """Execute SQL and return DataFrame."""
    return get_connection().execute(sql).df()
