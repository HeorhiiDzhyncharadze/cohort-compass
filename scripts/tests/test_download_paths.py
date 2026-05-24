from pathlib import Path

from scripts.download_data import RAW_DIR, expected_files


def test_expected_files_lists_seven_months():
    files = expected_files()
    assert len(files) == 7
    assert "2019-Oct.csv" in files
    assert "2020-Apr.csv" in files


def test_raw_dir_is_data_raw():
    assert RAW_DIR == Path("data/raw")
