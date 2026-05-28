"""Cohort Compass — Funnel Analysis."""

import streamlit as st
import plotly.express as px

from lib import db, queries
from lib.filters import render_sidebar
from lib.sql_toggle import show_sql

st.set_page_config(
    page_title="Funnel · Cohort Compass",
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
st.title("🔻 Funnel Analysis")
st.caption("Monthly view → cart → purchase conversion · source: mart_funnel")
st.divider()

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
df = db.query(queries.FUNNEL_MONTHLY)

if df.empty:
    st.warning("No data. Run `make dbt-build` first.")
    st.stop()

# ---------------------------------------------------------------------------
# 1. Grouped bar: viewers → carted → buyers per month
# ---------------------------------------------------------------------------
st.subheader("Monthly Funnel Volume")

df_long = df.melt(
    id_vars="event_date",
    value_vars=["viewers", "carted", "buyers"],
    var_name="stage",
    value_name="users",
)

# Friendly ordering and labels
stage_order  = ["viewers", "carted", "buyers"]
stage_labels = {"viewers": "Viewers", "carted": "Carted", "buyers": "Buyers"}
df_long["stage"] = df_long["stage"].map(stage_labels)

fig_bar = px.bar(
    df_long,
    x="event_date",
    y="users",
    color="stage",
    barmode="group",
    color_discrete_sequence=["#636EFA", "#FFA15A", "#00CC96"],
    labels={"event_date": "Month", "users": "Unique Users", "stage": "Stage"},
    category_orders={"stage": [stage_labels[s] for s in stage_order]},
)
fig_bar.update_layout(hovermode="x unified", legend_title_text="")
st.plotly_chart(fig_bar, use_container_width=True)

show_sql("Funnel Monthly", queries.FUNNEL_MONTHLY)

st.divider()

# ---------------------------------------------------------------------------
# 2. CVR line chart: view-to-purchase rate over time
# ---------------------------------------------------------------------------
st.subheader("View → Purchase CVR (%)")

fig_cvr = px.line(
    df,
    x="event_date",
    y="view_to_purchase_rate",
    markers=True,
    labels={"event_date": "Month", "view_to_purchase_rate": "CVR (%)"},
    color_discrete_sequence=["#FF6B35"],
)
fig_cvr.update_traces(line_width=2, marker_size=7)
fig_cvr.update_layout(hovermode="x unified")
st.plotly_chart(fig_cvr, use_container_width=True)

show_sql("CVR Trend", queries.FUNNEL_MONTHLY)
