# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Cohort Compass — end-to-end e-commerce retention & LTV analytics platform on 285M REES46 events. Portfolio project for Junior Data Analyst role. SQL-first: every chart in the app exposes its underlying SQL via a "Show SQL" toggle.

**Tutor mode:** The user writes all analytical SQL, dbt models, and ML logic themselves. Claude explains, reviews, and unblocks — does NOT auto-generate those. Boilerplate and scaffolding are fine to generate.

## Commands

```bash
make install        # uv sync
make data           # download REES46 via Kaggle API → data/raw/
make ingest         # CSV → Parquet partitions → DuckDB
make dbt-build      # dbt deps + seed + run + test
make dbt-test       # dbt test only
make dbt-docs       # generate + serve dbt docs at :8081
make ml             # train churn model + score users
make app            # streamlit run app/Home.py at :8501
make sample-deploy  # build sampled DB for Streamlit Cloud deploy
make lint           # ruff format + ruff check --fix
make test           # pytest
make clean          # wipe warehouse/ and data/parquet/
```

Single test: `uv run pytest ml/tests/test_features.py::test_name -v`

dbt single model: `cd dbt && uv run dbt run --select stg_events`

## Architecture

```
CSV (14GB) → scripts/ingest.py → Parquet (partitioned by event_date)
                                        ↓
                              DuckDB (warehouse/cohort_compass.duckdb)
                                        ↓
                    dbt-duckdb: staging → intermediate → marts
                                        ↓
                    app/ (Streamlit multipage) + ml/ (sklearn churn)
```

**dbt layer:**
- `staging/` — `stg_events`: clean, dedup, cast types from raw Parquet external tables
- `intermediate/` — `int_sessions` (window-function sessionization, 30-min gap), `int_purchases`, `int_users`
- `marts/` — `fct_events`, `fct_sessions`, `fct_purchases`, `dim_users`, `dim_products`, then analytics marts: `mart_funnel`, `mart_cohorts` (PIVOT retention matrix), `mart_rfm` (NTILE scoring), `mart_ltv`, `mart_churn_features`, `mart_journey` (LAG/LEAD transitions), `mart_anomalies` (rolling Z-score)

**App layer (`app/`):**
- `lib/db.py` — DuckDB connection (read-only)
- `lib/queries.py` — all SQL strings live here (single source for "Show SQL" toggle)
- `lib/filters.py` — sidebar filter widget (date range, category, brand, price tier)
- `lib/sql_toggle.py` — "Show SQL" component used on every chart
- `Home.py` + `pages/1_Funnel.py` through `pages/7_Data_Model.py`

**ML layer (`ml/`):** reads `mart_churn_features` → trains LogReg → writes `scored_users` back to DuckDB. Entry: `python -m ml.train_churn`.

## Key Conventions

- All SQL strings in `app/lib/queries.py` — never inline SQL in page files
- Streamlit imports: use `from lib import db, queries` (NOT `from app.lib import`) — Streamlit adds `app/` to sys.path, not project root
- `dbt/profiles.yml` is gitignored; connection via env var `DUCKDB_PATH`
- `data/` and `warehouse/` are gitignored; `make data && make ingest` rebuilds from scratch
- Streamlit Cloud deploy uses sampled DB (10% users) built by `scripts/sample_for_deploy.py`
- dbt incremental models use `materialized='incremental'` with `unique_key`; at least 3 models must be incremental
- RFM scoring uses `NTILE(5)` window functions, not CASE ladders
- Sessionization: 30-minute inactivity gap, implemented as window SUM over LAG diff
- `mart_journey` stays as VIEW (LAG over 411M rows can't materialize on 13GB RAM). Streamlit page uses `@st.cache_data(ttl=3600)` — first query ~30-60s, then cached
- `mart_anomalies` uses daily grain (`event_time::date`) + `approx_count_distinct` for memory efficiency

## Boundaries

- `scripts/` — one-shot operational scripts only (download, ingest, sample)
- `dbt/` — declarative SQL transformations; no Python business logic inside dbt
- `ml/` — pure Python; reads DuckDB, writes back to DuckDB
- `app/lib/` — reusable utilities; no Streamlit page logic
- `app/pages/` — page UI only; imports from `lib/`

## Dataset

REES46 eCommerce Behavior Data (`mkechinov/ecommerce-behavior-data-from-multi-category-store` on Kaggle). Schema: `event_time`, `event_type` (view/cart/remove_from_cart/purchase), `product_id`, `category_id`, `category_code`, `brand`, `price`, `user_id`, `user_session`. ~285M events, Oct 2019–Apr 2020.
