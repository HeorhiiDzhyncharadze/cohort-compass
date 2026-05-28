"""Cohort Compass — Cohort Retention."""

import streamlit as st
import plotly.graph_objects as go

from lib import db, queries
from lib.filters import render_sidebar
from lib.sql_toggle import show_sql

st.set_page_config(
    page_title="Cohorts · Cohort Compass",
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
st.title("📅 Cohort Retention")
st.caption("Monthly cohorts · retention_rate = retained_users / cohort_size · source: mart_cohorts")
st.divider()

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
df = db.query(queries.COHORT_RETENTION)

if df.empty:
    st.warning("No data. Run `make dbt-build` first.")
    st.stop()

# ---------------------------------------------------------------------------
# Pivot: cohort_month (rows) × period_number (cols) → retention_rate
# ---------------------------------------------------------------------------
pivot = (
    df.pivot(index="cohort_month", columns="period_number", values="retention_rate")
    .sort_index()
)

# Format row labels as YYYY-MM strings for readability
pivot.index = pivot.index.astype(str).str[:7]
pivot.columns = [f"M+{c}" for c in pivot.columns]

# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------
st.subheader("Retention Matrix")

fig = go.Figure(
    go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale="Blues",
        zmin=0,
        zmax=100,
        text=[[f"{v:.1f}%" if v == v else "" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        hovertemplate="Cohort: %{y}<br>Period: %{x}<br>Retention: %{z:.1f}%<extra></extra>",
        colorbar=dict(title="Retention %"),
    )
)

fig.update_layout(
    xaxis_title="Period (months since first purchase)",
    yaxis_title="Cohort (month of first purchase)",
    yaxis_autorange="reversed",
    height=450,
    margin=dict(l=80, r=40, t=40, b=60),
)

st.plotly_chart(fig, use_container_width=True)

show_sql("Cohort Retention", queries.COHORT_RETENTION)

st.divider()

# ---------------------------------------------------------------------------
# Supporting table: cohort sizes
# ---------------------------------------------------------------------------
st.subheader("Cohort Sizes")

cohort_sizes = (
    df[df["period_number"] == 0][["cohort_month", "cohort_size"]]
    .copy()
    .sort_values("cohort_month")
)
cohort_sizes["cohort_month"] = cohort_sizes["cohort_month"].astype(str).str[:7]
cohort_sizes = cohort_sizes.rename(columns={"cohort_month": "Cohort", "cohort_size": "Users"})
cohort_sizes["Users"] = cohort_sizes["Users"].map("{:,}".format)

st.dataframe(cohort_sizes, use_container_width=True, hide_index=True)
