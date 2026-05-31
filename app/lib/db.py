"""DuckDB connection — read-only singleton."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

_FULL_DB = Path(__file__).parents[2] / "warehouse" / "cohort_compass.duckdb"
_SAMPLE_DB = Path(__file__).parents[2] / "warehouse" / "cohort_compass_sample.duckdb"
# Use full DB locally if it exists; fall back to sample DB (committed to git for Streamlit Cloud)
_DEFAULT_DB = _FULL_DB if _FULL_DB.exists() else _SAMPLE_DB


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
