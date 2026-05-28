"""Build a sampled DuckDB for Streamlit Community Cloud deployment.

Samples 10% of users (reproducible via random seed) and materialises only
the mart-layer tables needed by the app. The resulting file is small enough
to commit to git (typically < 80 MB).

Usage:
    uv run python scripts/sample_for_deploy.py

Output:
    warehouse/cohort_compass_sample.duckdb   (~50–80 MB, safe to commit)

The Streamlit app reads DUCKDB_PATH from the environment. Set it in
Streamlit Cloud → App settings → Secrets:

    DUCKDB_PATH = "warehouse/cohort_compass_sample.duckdb"
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_ROOT       = Path(__file__).parents[1]
SRC_PATH    = os.getenv("DUCKDB_PATH", str(_ROOT / "warehouse" / "cohort_compass.duckdb"))
DEST_PATH   = str(_ROOT / "warehouse" / "cohort_compass_sample.duckdb")
SAMPLE_SEED = 42
SAMPLE_FRAC = 0.10   # 10% of users ≈ ~200k from 2M

# Tables to copy verbatim (small lookup / aggregate tables)
VERBATIM_TABLES = [
    "mart_funnel",
    "mart_cohorts",
    "mart_anomalies",
    "mart_journey",
]

# Tables that need user-level sampling
USER_TABLES = [
    "dim_users",
    "mart_rfm",
    "mart_ltv",
    "mart_churn_features",
    "scored_users",
]

# Fact tables — sampled via user_id join
FACT_TABLES = [
    "fct_purchases",
]


def main() -> None:
    print(f"Source:      {SRC_PATH}")
    print(f"Destination: {DEST_PATH}")
    print(f"Sample:      {SAMPLE_FRAC * 100:.0f}% of users (seed={SAMPLE_SEED})")

    src  = duckdb.connect(SRC_PATH, read_only=True)
    dest = duckdb.connect(DEST_PATH, read_only=False)

    # ------------------------------------------------------------------
    # 1. Sample user_ids
    # ------------------------------------------------------------------
    print("\nSampling users …")
    sampled_users = src.execute(f"""
        SELECT user_id
        FROM dim_users
        USING SAMPLE {int(SAMPLE_FRAC * 100)}% (bernoulli, {SAMPLE_SEED})
    """).df()
    n_users = len(sampled_users)
    print(f"  → {n_users:,} users selected")

    # Register in dest so we can use it as a filter
    dest.register("_sampled_users", sampled_users)

    # ------------------------------------------------------------------
    # 2. Verbatim aggregate tables
    # ------------------------------------------------------------------
    for table in VERBATIM_TABLES:
        try:
            df = src.execute(f"SELECT * FROM {table}").df()
            dest.execute(f"DROP TABLE IF EXISTS {table}")
            dest.register(f"_tmp_{table}", df)
            dest.execute(f"CREATE TABLE {table} AS SELECT * FROM _tmp_{table}")
            dest.unregister(f"_tmp_{table}")
            print(f"  ✓  {table}: {len(df):,} rows")
        except Exception as e:
            print(f"  ⚠  {table} skipped: {e}")

    # ------------------------------------------------------------------
    # 3. User-level tables — filter to sampled users
    # ------------------------------------------------------------------
    for table in USER_TABLES:
        try:
            df = src.execute(f"""
                SELECT t.*
                FROM {table} t
                INNER JOIN _sampled_users s ON t.user_id = s.user_id
            """).df()
            dest.execute(f"DROP TABLE IF EXISTS {table}")
            dest.register(f"_tmp_{table}", df)
            dest.execute(f"CREATE TABLE {table} AS SELECT * FROM _tmp_{table}")
            dest.unregister(f"_tmp_{table}")
            print(f"  ✓  {table}: {len(df):,} rows")
        except Exception as e:
            print(f"  ⚠  {table} skipped: {e}")

    # ------------------------------------------------------------------
    # 4. Fact tables — filter to sampled users
    # ------------------------------------------------------------------
    for table in FACT_TABLES:
        try:
            df = src.execute(f"""
                SELECT t.*
                FROM {table} t
                INNER JOIN _sampled_users s ON t.user_id = s.user_id
            """).df()
            dest.execute(f"DROP TABLE IF EXISTS {table}")
            dest.register(f"_tmp_{table}", df)
            dest.execute(f"CREATE TABLE {table} AS SELECT * FROM _tmp_{table}")
            dest.unregister(f"_tmp_{table}")
            print(f"  ✓  {table}: {len(df):,} rows")
        except Exception as e:
            print(f"  ⚠  {table} skipped: {e}")

    # ------------------------------------------------------------------
    # 5. fct_events — too large even at 10%; create a view from fct_purchases
    # ------------------------------------------------------------------
    dest.execute("DROP VIEW IF EXISTS fct_events")
    dest.execute("""
        CREATE VIEW fct_events AS
        SELECT
            user_id, event_time, 'purchase' AS event_type,
            product_id, category_id, category_code, brand, price,
            user_session, event_date
        FROM fct_purchases
    """)
    print(f"  ✓  fct_events: view over fct_purchases (purchase events only)")

    src.close()
    dest.close()

    size_mb = Path(DEST_PATH).stat().st_size / 1_048_576
    print(f"\nDone → {DEST_PATH}  ({size_mb:.1f} MB)")
    print("\nNext steps:")
    print("  1. git add warehouse/cohort_compass_sample.duckdb")
    print("  2. git push")
    print("  3. Streamlit Cloud → Secrets: DUCKDB_PATH = 'warehouse/cohort_compass_sample.duckdb'")


if __name__ == "__main__":
    main()
