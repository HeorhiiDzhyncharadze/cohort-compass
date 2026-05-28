"""Train churn model and write scored_users back to DuckDB.

Usage:
    uv run python -m ml.train_churn

Output:
    - Prints train/test AUC to stdout.
    - Writes table `scored_users` (user_id, churn_probability, churn_label)
      into warehouse/cohort_compass.duckdb.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_DEFAULT_DB = Path(__file__).parents[1] / "warehouse" / "cohort_compass.duckdb"
DB_PATH     = os.getenv("DUCKDB_PATH", str(_DEFAULT_DB))

FEATURES = [
    "total_purchases",
    "total_spend",
    # days_since_last_purchase excluded — directly encodes is_churned (direct leakage)
    "avg_days_between_purchases",
    # r_score excluded — NTILE on last_purchase_date, near-direct leakage
    "f_score",
    "m_score",
    # cohort_month_num excluded — indirect leakage: newer cohorts can't be churned by
    # definition (< 60 days in dataset), so num correlates with label via label logic
    "spend_per_purchase", # avg order value — pure behavioral signal
]
LABEL = "is_churned"


# ---------------------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------------------
def load_features() -> pd.DataFrame:
    con = duckdb.connect(DB_PATH, read_only=True)
    df  = con.execute("SELECT * FROM mart_churn_features").df()
    con.close()
    return df


# ---------------------------------------------------------------------------
# 2. Prepare X, y
# ---------------------------------------------------------------------------
def prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    # Fill nulls in avg_days_between_purchases with column median
    median_gap = df["avg_days_between_purchases"].median()
    df["avg_days_between_purchases"] = df["avg_days_between_purchases"].fillna(median_gap)

    # cohort_month_num: months since Oct-2019 (dataset start)
    # Based on first_purchase_date, NOT last_purchase_date — no leakage.
    # Captures lifecycle stage: Oct cohort had 6 months, Apr cohort had weeks.
    cohort = pd.to_datetime(df["cohort_month"])
    df["cohort_month_num"] = (cohort.dt.year - 2019) * 12 + (cohort.dt.month - 10)

    # spend_per_purchase: avg order value — pure behavioral signal
    df["spend_per_purchase"] = df["total_spend"] / df["total_purchases"].clip(lower=1)

    X = df[FEATURES].copy()
    y = df[LABEL].astype(int)
    return X, y


# ---------------------------------------------------------------------------
# 3. Train
# ---------------------------------------------------------------------------
def train(X: pd.DataFrame, y: pd.Series) -> tuple[Pipeline, float]:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    LogisticRegression(max_iter=1000, random_state=42)),
    ])
    pipe.fit(X_train, y_train)

    y_prob = pipe.predict_proba(X_test)[:, 1]
    auc    = roc_auc_score(y_test, y_prob)

    return pipe, auc


# ---------------------------------------------------------------------------
# 4. Score all users and write to DuckDB
# ---------------------------------------------------------------------------
def write_scores(df: pd.DataFrame, pipe: Pipeline) -> None:
    X_all = df[FEATURES].copy()
    X_all["avg_days_between_purchases"] = X_all["avg_days_between_purchases"].fillna(
        X_all["avg_days_between_purchases"].median()
    )

    proba  = pipe.predict_proba(X_all)[:, 1]
    labels = pipe.predict(X_all)

    scored = pd.DataFrame({
        "user_id":           df["user_id"].values,
        "churn_probability": np.round(proba, 4),
        "churn_label":       labels.astype(int),
    })

    con = duckdb.connect(DB_PATH, read_only=False)
    con.execute("DROP TABLE IF EXISTS scored_users")
    con.register("_scored_tmp", scored)
    con.execute("CREATE TABLE scored_users AS SELECT * FROM _scored_tmp")
    con.unregister("_scored_tmp")
    con.close()

    print(f"  Wrote {len(scored):,} rows → scored_users")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    print("Loading mart_churn_features …")
    df = load_features()
    print(f"  {len(df):,} users loaded")

    X, y = prepare(df)
    churn_pct = y.mean() * 100
    print(f"  Churn rate: {churn_pct:.1f}%  |  Class balance: {y.value_counts().to_dict()}")

    print("Training LogisticRegression …")
    pipe, auc = train(X, y)
    print(f"  Test AUC: {auc:.4f}", "✅" if auc >= 0.70 else "⚠️  below 0.70 target")

    print("Scoring all users …")
    write_scores(df, pipe)

    print("Done.")


if __name__ == "__main__":
    main()
