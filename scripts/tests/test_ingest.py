import duckdb
import pandas as pd

from scripts.ingest import build_external_view, chunk_csv_to_parquet


def test_chunk_csv_to_parquet_creates_partitioned_files(tmp_path):
    csv = tmp_path / "small.csv"
    csv.write_text(
        "event_time,event_type,product_id,category_id,category_code,brand,price,user_id,user_session\n"
        "2019-10-01 00:00:00 UTC,view,1,100,electronics,apple,100.0,1001,s1\n"
        "2019-10-15 12:00:00 UTC,purchase,1,100,electronics,apple,100.0,1001,s1\n"
        "2019-11-01 00:00:00 UTC,view,2,100,electronics,samsung,200.0,1002,s2\n"
    )
    out_dir = tmp_path / "parquet"
    chunk_csv_to_parquet(csv, out_dir, chunk_size=2)

    files = sorted(str(p.relative_to(out_dir)) for p in out_dir.rglob("*.parquet"))
    assert any("2019-10" in f for f in files)
    assert any("2019-11" in f for f in files)


def test_build_external_view_returns_count(tmp_path):
    parquet_dir = tmp_path / "parquet"
    parquet_dir.mkdir()
    df = pd.DataFrame({
        "event_time": pd.to_datetime(["2019-10-01", "2019-10-02"]),
        "event_type": ["view", "purchase"],
        "product_id": [1, 2],
        "category_id": [10, 20],
        "category_code": ["a", "b"],
        "brand": ["x", "y"],
        "price": [1.0, 2.0],
        "user_id": [100, 200],
        "user_session": ["s1", "s2"],
        "event_date": ["2019-10", "2019-10"],
    })
    subdir = parquet_dir / "event_date=2019-10"
    subdir.mkdir()
    df.to_parquet(subdir / "part.parquet", index=False)

    db_path = tmp_path / "test.duckdb"
    count = build_external_view(parquet_dir, db_path)
    assert count == 2

    con = duckdb.connect(str(db_path), read_only=True)
    res = con.execute("SELECT COUNT(*) FROM raw_events").fetchone()
    assert res[0] == 2
