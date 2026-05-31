# Developer Guide — Cohort Compass

Personal reference for extending and maintaining this project.

---

## Quick Reference

| Command | What it does |
|---|---|
| `make install` | `uv sync` — install all dependencies |
| `make data` | Download REES46 CSVs via Kaggle API |
| `make ingest` | CSV → Parquet → DuckDB external view |
| `make dbt-build` | `dbt deps + seed + run + test` |
| `make dbt-test` | Run dbt tests only |
| `make dbt-docs` | Build + serve dbt docs at `:8081` |
| `make ml` | Train churn model + write `scored_users` to DuckDB |
| `make app` | `streamlit run app/Home.py` at `:8501` |
| `make sample-deploy` | Build 10%-sample DuckDB for Streamlit Cloud |
| `make lint` | `ruff format + check --fix` |
| `make test` | `pytest scripts/tests/ -v` |
| `make clean` | Wipe `warehouse/` and `data/parquet/` |

Single dbt model: `cd dbt && uv run dbt run --select mart_cohorts`

Single test: `uv run pytest scripts/tests/test_ingest.py::test_name -v`

---

## Adding a New dbt Mart Model

### Step-by-step

1. **Create SQL file:**
   ```
   dbt/models/marts/mart_yourname.sql
   ```

2. **Write the model** (example template):
   ```sql
   {{
     config(
       materialized='table'
     )
   }}

   with base as (
       select * from {{ ref('dim_users') }}
   )

   select
       user_id,
       -- your columns here
       total_spend
   from base
   ```

3. **Document in schema.yml:**
   Add to `dbt/models/marts/schema.yml`:
   ```yaml
   - name: mart_yourname
     description: >
       What this model does. Grain: 1 row per X.
     columns:
       - name: user_id
         description: "User identifier"
   ```

4. **Run and test:**
   ```bash
   cd dbt && uv run dbt run --select mart_yourname
   uv run dbt test --select mart_yourname
   ```

5. **Add SQL to queries.py:**
   ```python
   # app/lib/queries.py
   YOUR_QUERY = "SELECT * FROM mart_yourname ORDER BY user_id"
   ```

6. **Rebuild sample DB for Streamlit Cloud:**
   ```bash
   make sample-deploy
   git add warehouse/cohort_compass_sample.duckdb
   git commit -m "chore: rebuild sample DB with mart_yourname"
   git push
   ```

### Materialization guide

| Use | Materialization |
|---|---|
| Full dataset read (285M rows) | `view` — never write 285M rows |
| Pre-aggregated analytics | `table` |
| Purchase facts (grows over time) | `incremental` with `unique_key` |
| CTEs used by multiple models | `ephemeral` |

### DuckDB OOM rule

**If `cohort_compass.duckdb` > 60% of RAM: DO NOT query `stg_events` directly via DuckDB.**

The buffer pool fills immediately (12 GB on 16 GB machine). Instead:
- Query downstream mart models (they're aggregated, much smaller)
- For raw Parquet access: use pyarrow directly, bypass DuckDB entirely

See `scripts/sample_for_deploy.py` step 6 (`mart_journey` section) as reference.

---

## Adding a New Streamlit Page

### File location

```
app/pages/8_NewPage.py   ← number prefix controls sidebar order
```

### Minimal template

```python
"""Cohort Compass — New Page."""

from __future__ import annotations

import streamlit as st

from lib import db, queries
from lib.filters import render_sidebar
from lib.sql_toggle import show_sql

st.set_page_config(
    page_title="New Page · Cohort Compass",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

filters = render_sidebar()

st.title("📊 New Page")
st.caption("Short description of what this page shows")
st.divider()

# --- Load data ---
df = db.query(queries.YOUR_QUERY)

# --- Chart ---
st.subheader("Chart title")
# ... plotly/st charts here ...

# --- Show SQL toggle ---
show_sql("YOUR_QUERY", queries.YOUR_QUERY)
```

### Key conventions

- **Never write SQL inline** in page files — add to `app/lib/queries.py`
- Use `from lib import ...` NOT `from app.lib import ...` (Streamlit adds `app/` to sys.path)
- Wrap slow queries with `@st.cache_data(ttl=3600)`
- Use `db.query(sql)` → returns `pd.DataFrame`

### Add SQL constant to queries.py

```python
# app/lib/queries.py

MY_NEW_QUERY = """
SELECT
    user_id,
    total_spend
FROM dim_users
ORDER BY total_spend DESC
LIMIT 100
"""
```

---

## Database Management

### Inspect tables

```powershell
uv run python -c "
import duckdb
c = duckdb.connect('warehouse/cohort_compass_sample.duckdb', read_only=True)
print(c.execute('SHOW TABLES').df())
c.close()
"
```

### Rebuild everything from scratch

```bash
make clean        # removes warehouse/ and data/parquet/
make data         # re-downloads REES46 CSVs (~14 GB, one-time)
make ingest       # CSV → Parquet → DuckDB external view
make dbt-build    # staging → intermediate → marts
make ml           # trains churn model, writes scored_users
```

### Rebuild sample DB (after adding new models)

```bash
make sample-deploy
git add warehouse/cohort_compass_sample.duckdb
git commit -m "chore: rebuild sample DB"
git push
```

Streamlit Cloud auto-redeploys from main.

### Check DuckDB version compatibility

The sample DB file format is tied to the DuckDB version used to create it.
Current pin: `duckdb==1.5.3` (in `pyproject.toml`).
If you upgrade DuckDB: rebuild the sample DB, then commit the new file.

---

## Troubleshooting Common Errors

| Error | Cause | Fix |
|---|---|---|
| `_duckdb.IOException` on Streamlit Cloud | Full DB absent, path fallback fails | Check `app/lib/db.py` auto-detect: `_FULL_DB if _FULL_DB.exists() else _SAMPLE_DB` |
| `ModuleNotFoundError: lib` | Running `python app/Home.py` directly | Use `uv run streamlit run app/Home.py` |
| `MissingArgumentsPropertyInGenericTestDeprecation` | `accepted_values` without `arguments:` wrapper | Non-blocking in dbt 1.11 — add `arguments:` if it bothers you |
| dbt parse slow on CI | Partial-parse cache conflict | Add `--no-partial-parse` flag |
| Streamlit app blank on first load | `@st.cache_data` miss on heavy query | Expected — cached after first run. Reduce `ttl` if needed. |
| `mart_journey` OOM locally | LAG over 285M rows exceeds buffer pool | `mart_journey` is a VIEW by design — queries are slow (30-60s). App caches result. |

---

## CI / GitHub Actions

Two workflows:

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | Push / PR to `main` | pytest + dbt parse |
| `dbt-docs.yml` | Push to `dbt/**` | dbt compile → dbt docs generate → GitHub Pages deploy |

`dbt parse` validates SQL syntax without a real database (uses `:memory:` DuckDB).
`dbt compile` must run before `dbt docs generate --no-compile` (generates `manifest.json`).

### CI profiles.yml strategy

`dbt/profiles.yml` is gitignored. CI writes it on-the-fly:
```yaml
- name: Write CI profiles.yml
  run: |
    printf "cohort_compass:\n  target: ci\n  outputs:\n    ci:\n      type: duckdb\n      path: ':memory:'\n      threads: 1\n" > dbt/profiles.yml
```

---

## Project Architecture (quick mental model)

```
Raw Parquet (14 GB, gitignored)
    ↓ DuckDB external view
stg_events (VIEW — never materialized, 285M rows)
    ↓
int_sessions / int_purchases / int_users (EPHEMERAL — compiled inline)
    ↓
fct_purchases (INCREMENTAL TABLE — purchase events only)
dim_users     (TABLE — one row per user)
mart_*        (TABLE or VIEW — analytics aggregates)
    ↓
Streamlit app (read-only DuckDB connection)
+ sklearn LogReg (writes scored_users back to DuckDB)
```

Key insight: **never materialize views that touch 285M rows** — DuckDB buffer pool
fills to 12 GB instantly on a 16 GB machine. Only mart-level aggregates are safe to TABLE.
