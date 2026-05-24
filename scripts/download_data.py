"""Download REES46 eCommerce Behavior Data from Kaggle.

Idempotent: skips files already present in data/raw/.
Requires KAGGLE_USERNAME and KAGGLE_KEY in environment (or ~/.kaggle/kaggle.json).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

RAW_DIR = Path("data/raw")
KAGGLE_DATASET = "mkechinov/ecommerce-behavior-data-from-multi-category-store"

MONTHS = [
    "2019-Oct", "2019-Nov", "2019-Dec",
    "2020-Jan", "2020-Feb", "2020-Mar", "2020-Apr",
]


def expected_files() -> list[str]:
    return [f"{m}.csv" for m in MONTHS]


def already_downloaded(filename: str) -> bool:
    return (RAW_DIR / filename).exists()


def download_all() -> None:
    load_dotenv()
    if not (os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY")):
        print("ERROR: set KAGGLE_USERNAME and KAGGLE_KEY (see .env.example)")
        sys.exit(1)

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for filename in expected_files():
        if already_downloaded(filename):
            print(f"  ✓ {filename} already present, skipping")
            continue
        print(f"  ↓ downloading {filename}...")
        api.dataset_download_file(KAGGLE_DATASET, filename, path=str(RAW_DIR))
        zip_path = RAW_DIR / f"{filename}.zip"
        if zip_path.exists():
            import zipfile
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(RAW_DIR)
            zip_path.unlink()

    print(f"Done. Files in {RAW_DIR}/")


if __name__ == "__main__":
    download_all()
