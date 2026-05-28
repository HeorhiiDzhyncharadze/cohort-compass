"""Cohort Compass — Overview / KPI Pulse."""

import streamlit as st
import plotly.express as px

from app.lib import db, queries
from app.lib.filters import render_sidebar
from app.lib.sql_toggle import show_sql

st.set_page_config(
    page_title="Cohort Compass",
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
st.title("🧭 Cohort Compass")
st.caption("End-to-end retention & LTV analytics · 411M REES46 events · dbt + DuckDB")
st.divider()

# ---------------------------------------------------------------------------
# KPI Cards
# ---------------------------------------------------------------------------
st.subheader("KPI Pulse")

kpi = db.query(queries.KPI_SUMMARY)

if not kpi.empty and kpi["gmv"].notna().any():
    row = kpi.iloc[0]
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("GMV",         f"${row['gmv']:,.0f}")
    c2.metric("Orders",      f"{row['orders']:,.0f}")
    c3.metric("Buyers",      f"{row['buyers']:,.0f}")
    c4.metric("CVR",         f"{row['cvr']:.1f}%")
    c5.metric("AOV",         f"${row['aov']:.2f}")
    c6.metric("Repeat Rate", f"{row['repeat_rate']:.1f}%")
else:
    st.info("Write `KPI_SUMMARY` query in `app/lib/queries.py` to populate KPI cards.")

if filters["show_sql"]:
    show_sql("KPI Summary", queries.KPI_SUMMARY)

st.divider()

# ---------------------------------------------------------------------------
# GMV Trend
# ---------------------------------------------------------------------------
st.subheader("GMV Daily Trend")

gmv_df = db.query(queries.GMV_TREND)

if not gmv_df.empty and gmv_df["gmv"].notna().any():
    fig = px.line(
        gmv_df, x="event_day", y=["gmv", "gmv_7d_ma"],
        labels={"value": "GMV ($)", "event_day": "Date", "variable": ""},
        color_discrete_map={"gmv": "#FF6B35", "gmv_7d_ma": "#333333"},
    )
    fig.update_layout(hovermode="x unified", legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Write `GMV_TREND` query in `app/lib/queries.py` to populate this chart.")

if filters["show_sql"]:
    show_sql("GMV Trend", queries.GMV_TREND)

st.divider()

# ---------------------------------------------------------------------------
# Category Mix
# ---------------------------------------------------------------------------
st.subheader("GMV by Category (Top 10)")

cat_df = db.query(queries.CATEGORY_MIX)

if not cat_df.empty and cat_df["gmv"].notna().any():
    fig2 = px.bar(
        cat_df, x="gmv", y="category_code", orientation="h",
        text="pct", labels={"gmv": "GMV ($)", "category_code": ""},
        color_discrete_sequence=["#FF6B35"],
    )
    fig2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig2.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Write `CATEGORY_MIX` query in `app/lib/queries.py` to populate this chart.")

if filters["show_sql"]:
    show_sql("Category Mix", queries.CATEGORY_MIX)
