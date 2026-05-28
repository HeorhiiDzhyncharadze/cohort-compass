"""Cohort Compass — Churn Lab."""

import streamlit as st
import plotly.express as px

from lib import db, queries
from lib.filters import render_sidebar
from lib.sql_toggle import show_sql

st.set_page_config(
    page_title="Churn Lab · Cohort Compass",
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
st.title("⚠️ Churn Lab")
st.caption("Churn features · source: mart_churn_features · ML scores added after `make ml`")
st.divider()

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
df = db.query(queries.CHURN_FEATURES)

if df.empty:
    st.warning("No data. Run `make dbt-build` first.")
    st.stop()

# ---------------------------------------------------------------------------
# 1. Churn Rate KPI card
# ---------------------------------------------------------------------------
st.subheader("Churn Overview")

total_users   = len(df)
churned_users = df["is_churned"].sum()
churn_rate    = churned_users / total_users * 100

c1, c2, c3 = st.columns(3)
c1.metric("Total Users",   f"{total_users:,}")
c2.metric("Churned Users", f"{churned_users:,}")
c3.metric("Churn Rate",    f"{churn_rate:.1f}%")

show_sql("Churn Features", queries.CHURN_FEATURES)

st.divider()

# ---------------------------------------------------------------------------
# 2. Churned vs Retained by RFM segment
# ---------------------------------------------------------------------------
st.subheader("Churned vs Retained by Segment")

SEGMENT_ORDER = ["Champions", "Loyal", "At Risk", "Hibernating", "Lost"]

seg_df = (
    df.groupby(["rfm_segment", "is_churned"])
    .size()
    .reset_index(name="users")
)
seg_df["status"] = seg_df["is_churned"].map({True: "Churned", False: "Retained"})
seg_df["rfm_segment"] = seg_df["rfm_segment"].astype("category").cat.set_categories(
    SEGMENT_ORDER, ordered=True
)
seg_df = seg_df.sort_values("rfm_segment")

fig_bar = px.bar(
    seg_df,
    x="rfm_segment",
    y="users",
    color="status",
    barmode="group",
    color_discrete_map={"Churned": "#EF553B", "Retained": "#00CC96"},
    category_orders={"rfm_segment": SEGMENT_ORDER, "status": ["Retained", "Churned"]},
    labels={"rfm_segment": "Segment", "users": "Users", "status": ""},
)
fig_bar.update_layout(hovermode="x unified", legend_title_text="")
st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# 3. At-Risk users: not yet churned, but recency score ≤ 2
# ---------------------------------------------------------------------------
st.subheader("Top 50 At-Risk Users")
st.caption("Retained (is_churned = False) · r_score ≤ 2 · sorted by days since last purchase desc")

at_risk = (
    df[(df["is_churned"] == False) & (df["r_score"] <= 2)]
    .nlargest(50, "days_since_last_purchase")
)

if at_risk.empty:
    st.info("No at-risk users found with current thresholds.")
else:
    st.dataframe(
        at_risk[[
            "user_id", "rfm_segment", "r_score", "f_score", "m_score",
            "total_purchases", "total_spend",
            "days_since_last_purchase", "avg_days_between_purchases",
        ]]
        .rename(columns={
            "user_id":                    "User ID",
            "rfm_segment":                "Segment",
            "r_score":                    "R",
            "f_score":                    "F",
            "m_score":                    "M",
            "total_purchases":            "Orders",
            "total_spend":                "Total Spend ($)",
            "days_since_last_purchase":   "Days Inactive",
            "avg_days_between_purchases": "Avg Gap (days)",
        })
        .reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# ML placeholder — populated after `make ml`
# ---------------------------------------------------------------------------
st.subheader("ML Churn Scores")
st.info(
    "Run `make ml` to train the churn model and populate `scored_users`. "
    "Churn probabilities will appear here automatically.",
    icon="🤖",
)
