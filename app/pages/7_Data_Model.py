"""Cohort Compass — Data Model & dbt Lineage."""

from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from lib.filters import render_sidebar

st.set_page_config(
    page_title="Data Model · Cohort Compass",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
filters = render_sidebar()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🗂️ Data Model")
st.caption("dbt lineage graph · model documentation · SQL-first architecture")
st.divider()

# ---------------------------------------------------------------------------
# 1. Architecture overview — Mermaid (always visible, no server needed)
# ---------------------------------------------------------------------------
st.subheader("Pipeline Architecture")

st.markdown("""
```mermaid
flowchart LR
    CSV["REES46 CSVs\\n14 GB · 7 months"] -->|chunked ingest| PQ["Parquet\\npartitioned by date"]
    PQ -->|DuckDB external view| RAW["raw_events"]

    subgraph dbt ["dbt-duckdb"]
        RAW --> STG["staging/\\nstg_events"]
        STG --> INT["intermediate/\\nint_sessions\\nint_purchases · int_users"]
        INT --> FACT["fct_events\\nfct_purchases"]
        INT --> DIM["dim_users\\ndim_products"]
        FACT --> MART["mart_funnel\\nmart_cohorts\\nmart_rfm\\nmart_ltv\\nmart_journey\\nmart_anomalies\\nmart_churn_features"]
        DIM  --> MART
    end

    MART --> APP["Streamlit\\n8 pages"]
    MART --> ML["sklearn LogReg\\nchurn model"]
    ML   -->|scored_users| APP
```
""")

st.divider()

# ---------------------------------------------------------------------------
# 2. dbt docs iframe — works locally after `make dbt-docs`
# ---------------------------------------------------------------------------
st.subheader("Interactive dbt Lineage Graph")

DBT_DOCS_URL = "http://localhost:8081"

tab_gh, tab_local = st.tabs(["🌐 GitHub Pages", "🖥️ Local (make dbt-docs)"])

with tab_gh:
    GH_PAGES_URL = "https://heorhiidzhyncharadze.github.io/cohort-compass"
    st.caption("Static dbt docs published via GitHub Actions → GitHub Pages.")
    st.link_button("Open on GitHub Pages →", GH_PAGES_URL, type="primary")
    components.iframe(GH_PAGES_URL, height=650, scrolling=True)

with tab_local:
    st.caption(
        "Run `make dbt-docs` in a separate terminal to start the dbt docs server, "
        "then click the button below to open the full interactive lineage graph."
    )
    st.link_button("Open dbt docs →", DBT_DOCS_URL, type="primary")
    st.info("The iframe is disabled in the public demo — run locally to use the interactive lineage graph.")

st.divider()

# ---------------------------------------------------------------------------
# 3. Model catalogue
# ---------------------------------------------------------------------------
st.subheader("Model Catalogue")

MODELS = [
    # layer, name, materialization, grain, description
    ("staging",       "stg_events",          "view",        "1 row = 1 event",         "Cast, clean, dedup raw events. Strips nulls on price for purchases."),
    ("intermediate",  "int_sessions",         "ephemeral",   "1 row = 1 session",       "30-min inactivity sessionization via LAG + cumulative SUM window."),
    ("intermediate",  "int_purchases",        "ephemeral",   "1 row = 1 purchase",      "Purchase subset with LAG-derived days_since_prev_purchase."),
    ("intermediate",  "int_users",            "ephemeral",   "1 row = 1 user",          "First/last purchase date, total orders & spend per user."),
    ("marts · facts", "fct_events",           "view",        "1 row = 1 event",         "Thin passthrough view. VIEW not TABLE — avoids 285M-row OOM."),
    ("marts · facts", "fct_purchases",        "incremental", "1 row = 1 purchase",      "Materialized purchase subset. Incremental on event_time."),
    ("marts · dims",  "dim_users",            "table",       "1 row = 1 user",          "User spine: cohort_month, first/last purchase, segment (NEW/REPEAT)."),
    ("marts",         "mart_funnel",          "table",       "1 row = 1 month",         "Monthly view→cart→purchase funnel with CVR columns."),
    ("marts",         "mart_cohorts",         "table",       "1 row = cohort × period", "Retention matrix: cohort_month × period_number → retention_rate."),
    ("marts",         "mart_rfm",             "table",       "1 row = 1 user",          "NTILE(5) R/F/M scores + Champions/Loyal/At Risk/Hibernating/Lost segments."),
    ("marts",         "mart_ltv",             "table",       "1 row = 1 user",          "AOV, avg purchase gap, predicted LTV (heuristic; ML to replace)."),
    ("marts",         "mart_journey",         "view",        "1 row = 1 transition",    "LAG-based event-pair transitions. VIEW — LAG on 285M rows exceeds RAM."),
    ("marts",         "mart_anomalies",       "table",       "1 row = 1 day",           "Daily CVR with rolling 30-day Z-score. approx_count_distinct for memory."),
    ("marts",         "mart_churn_features",  "table",       "1 row = 1 user",          "ML feature store: RFM scores + purchase stats + is_churned label."),
]

catalogue_df = pd.DataFrame(
    MODELS,
    columns=["Layer", "Model", "Materialization", "Grain", "Description"],
)

# Color-code materialization
MAT_COLORS = {
    "view":        "#636EFA",
    "table":       "#00CC96",
    "incremental": "#FFA15A",
    "ephemeral":   "#AB63FA",
}

st.dataframe(
    catalogue_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Materialization": st.column_config.TextColumn(
            "Materialization",
            help="view · table · incremental · ephemeral",
        ),
    },
)

st.divider()

# ---------------------------------------------------------------------------
# 4. SQL techniques reference
# ---------------------------------------------------------------------------
st.subheader("SQL Techniques Used")

techniques = {
    "Sessionization (30-min gap)": (
        "int_sessions",
        """-- Two-CTE pattern (DuckDB forbids nested window functions)
with lagged as (
    select *, lag(event_time) over (partition by user_id order by event_time) as prev
    from stg_events
),
session_flags as (
    select *,
        sum(case when prev is null then 0
                 when event_time - prev > interval 30 minute then 1
                 else 0 end)
        over (partition by user_id order by event_time
              rows between unbounded preceding and current row) as session_id_raw
    from lagged
)""",
    ),
    "Cohort retention matrix": (
        "mart_cohorts",
        """datediff('month', cohort_month, event_date) as period_number
-- grain: cohort_month × period_number → retained_users / cohort_size""",
    ),
    "NTILE RFM scoring": (
        "mart_rfm",
        """ntile(5) over (order by last_purchase_date desc) as r_score,
ntile(5) over (order by total_purchases)         as f_score,
ntile(5) over (order by total_spend)             as m_score""",
    ),
    "Rolling Z-score anomaly detection": (
        "mart_anomalies",
        """avg(cvr)    over (order by event_day rows between 29 preceding and current row) as rolling_avg,
stddev(cvr) over (order by event_day rows between 29 preceding and current row) as rolling_std,
(cvr - rolling_avg) / nullif(rolling_std, 0) as z_score,
abs(z_score) > 2 as is_anomaly""",
    ),
    "Event-type transitions (LAG)": (
        "mart_journey",
        """lag(event_type) over (partition by user_session order by event_time) as from_event,
event_type as to_event
-- then GROUP BY from_event, to_event → transition_count""",
    ),
    "Window function in aggregate (GMV 7d MA)": (
        "queries.py",
        """avg(sum(price)) over (
    order by event_time::date
    rows between 6 preceding and current row
) as gmv_7d_ma""",
    ),
}

for technique, (source, snippet) in techniques.items():
    with st.expander(f"**{technique}** · `{source}`"):
        st.code(snippet.strip(), language="sql")
