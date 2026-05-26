"""Download REES46 eCommerce Behavior Data from Kaggle.

Idempotent: skips files already present in data/raw/.
Requires KAGGLE_USERNAME and KAGGLE_KEY in environment (or ~/.kaggle/kaggle.json).
"""

from __future__ import annotations

import os
import subprocess
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


def _kaggle_cli() -> Path:
    """Return path to kaggle CLI in the current venv."""
    scripts = Path(sys.executable).parent
    return scripts / ("kaggle.exe" if sys.platform == "win32" else "kaggle")


def download_all() -> None:
    load_dotenv()
    if not (os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY")):
        print("ERROR: set KAGGLE_USERNAME and KAGGLE_KEY (see .env.example)")
        sys.exit(1)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    kaggle = _kaggle_cli()

    for filename in expected_files():
        if already_downloaded(filename):
            print(f"  ✓ {filename} already present, skipping")
            continue
        print(f"  ↓ downloading {filename}...")
        subprocess.run(
            [
                str(kaggle), "datasets", "download",
                "-d", KAGGLE_DATASET,
                "-f", filename,
                "--path", str(RAW_DIR),
                "--unzip",
            ],
            check=True,
        )

    print(f"Done. Files in {RAW_DIR}/")


if __name__ == "__main__":
    download_all()
