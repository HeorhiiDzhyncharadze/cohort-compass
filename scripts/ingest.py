"""Convert REES46 CSVs to month-partitioned Parquet, then register as DuckDB external view.

Pipeline:
1. Read each CSV in chunks (pandas).
2. Add event_date partition column (YYYY-MM string).
3. Write Parquet partitioned by event_date into data/parquet/.
4. Create `raw_events` view in DuckDB pointing at the Parquet glob.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd
from dotenv import load_dotenv

RAW_DIR = Path("data/raw")
PARQUET_DIR = Path("data/parquet")
DEFAULT_DB = Path("warehouse/cohort_compass.duckdb")

COLUMN_TYPES = {
    "event_type": "string",
    "product_id": "int64",
    "category_id": "int64",
    "category_code": "string",
    "brand": "string",
    "price": "float64",
    "user_id": "int64",
    "user_session": "string",
}

CHUNK = 2_000_000


def chunk_csv_to_parquet(csv_path: Path, out_dir: Path, chunk_size: int = CHUNK) -> int:
    """Read CSV in chunks, write Parquet partitioned by year-month. Returns row count."""
    out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    reader = pd.read_csv(
        csv_path,
        chunksize=chunk_size,
        parse_dates=["event_time"],
        dtype=COLUMN_TYPES,
    )
    for i, chunk in enumerate(reader):
        chunk["event_date"] = chunk["event_time"].dt.strftime("%Y-%m")
        for month, sub in chunk.groupby("event_date"):
            target_dir = out_dir / f"event_date={month}"
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / f"{csv_path.stem}-chunk{i:04d}.parquet"
            sub.drop(columns=["event_date"]).to_parquet(
                target_file, index=False, compression="snappy"
            )
        total += len(chunk)
        print(f"    chunk {i}: {len(chunk):>9,} rows  (total: {total:>11,})")
    return total


def build_external_view(parquet_dir: Path, db_path: Path) -> int:
    """Register Parquet glob as DuckDB view `raw_events`. Returns row count."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    pattern = str(parquet_dir / "event_date=*" / "*.parquet").replace("\\", "/")
    con.execute(
        f"""
        CREATE OR REPLACE VIEW raw_events AS
        SELECT
            event_time,
            event_type,
            product_id,
            category_id,
            category_code,
            brand,
            price,
            user_id,
            user_session,
            CAST(strftime(event_time, '%Y-%m') AS VARCHAR) AS event_date
        FROM read_parquet('{pattern}', hive_partitioning = false);
        """
    )
    count = con.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    con.close()
    return count


def main() -> None:
    load_dotenv()
    db_path = Path(os.getenv("DUCKDB_PATH", str(DEFAULT_DB)))

    csvs = sorted(RAW_DIR.glob("*.csv"))
    if not csvs:
        raise SystemExit(f"No CSVs in {RAW_DIR}/. Run `make data` first.")

    for csv in csvs:
        print(f"→ {csv.name}")
        chunk_csv_to_parquet(csv, PARQUET_DIR)

    print("\n→ Registering DuckDB view raw_events...")
    n = build_external_view(PARQUET_DIR, db_path)
    print(f"Done. {n:,} rows in raw_events.")


if __name__ == "__main__":
    main()
