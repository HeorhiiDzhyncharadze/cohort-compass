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
import pandas as pd
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_ROOT       = Path(__file__).parents[1]
SRC_PATH    = os.getenv("DUCKDB_PATH", str(_ROOT / "warehouse" / "cohort_compass.duckdb"))
DEST_PATH   = str(_ROOT / "warehouse" / "cohort_compass_sample.duckdb")
SAMPLE_SEED = 42
SAMPLE_FRAC = 0.10   # 10% of users ≈ ~200k from 2M

# Tables to copy verbatim (small lookup / aggregate tables)
# NOTE: mart_journey excluded — computed in a separate pass after src is closed
VERBATIM_TABLES = [
    "mart_funnel",
    "mart_cohorts",
    "mart_anomalies",
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

    # Register in src so JOIN queries against src tables can see it
    src.register("_sampled_users", sampled_users)

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
    # 5. fct_events — view over fct_purchases (purchase events only)
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
    print("  ✓  fct_events: view over fct_purchases (purchase events only)")

    # ------------------------------------------------------------------
    # 6. mart_journey — read ONE Parquet file directly via pyarrow
    #    (bypasses DuckDB entirely; stg_events scan needs ~12.4 GB which
    #     exceeds the 12.5 GB DuckDB limit on a 16 GB machine)
    # ------------------------------------------------------------------
    src.close()
    print("  Computing mart_journey (pyarrow, first Parquet partition) …")
    try:
        parquet_dir = _ROOT / "data" / "parquet"
        parquet_files = sorted(parquet_dir.glob("**/*.parquet"))
        if not parquet_files:
            raise FileNotFoundError(f"No Parquet files found in {parquet_dir}")

        # Read only the first partition — enough to cover all 4×4 transitions
        raw = pq.read_table(
            parquet_files[0],
            columns=["user_session", "event_type", "event_time"],
        ).to_pandas()

        raw = raw.sort_values(["user_session", "event_time"])
        raw["from_event"] = raw.groupby("user_session")["event_type"].shift(1)

        journey_df = (
            raw[raw["from_event"].notna()]
            .groupby(["from_event", "event_type"])
            .size()
            .reset_index(name="transition_count")
            .rename(columns={"event_type": "to_event"})
            .sort_values("transition_count", ascending=False)
            .reset_index(drop=True)
        )

        dest.execute("DROP TABLE IF EXISTS mart_journey")
        dest.register("_tmp_journey", journey_df)
        dest.execute("CREATE TABLE mart_journey AS SELECT * FROM _tmp_journey")
        dest.unregister("_tmp_journey")
        print(f"  ✓  mart_journey: {len(journey_df):,} rows")
    except Exception as e:
        print(f"  ⚠  mart_journey skipped: {e}")

    dest.close()

    size_mb = Path(DEST_PATH).stat().st_size / 1_048_576
    print(f"\nDone → {DEST_PATH}  ({size_mb:.1f} MB)")
    print("\nNext steps:")
    print("  1. git add warehouse/cohort_compass_sample.duckdb")
    print("  2. git push")
    print("  3. Streamlit Cloud → Secrets: DUCKDB_PATH = 'warehouse/cohort_compass_sample.duckdb'")


if __name__ == "__main__":
    main()
