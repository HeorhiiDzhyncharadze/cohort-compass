"""Cohort Compass — RFM Segmentation."""

import streamlit as st
import plotly.express as px

from lib import db, queries
from lib.filters import render_sidebar
from lib.sql_toggle import show_sql

st.set_page_config(
    page_title="RFM · Cohort Compass",
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
st.title("🎯 RFM Segmentation")
st.caption("Recency · Frequency · Monetary — NTILE(5) scoring · source: mart_rfm")
st.divider()

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
df  = db.query(queries.RFM_USERS)
seg = db.query(queries.RFM_SEGMENTS)

if df.empty:
    st.warning("No data. Run `make dbt-build` first.")
    st.stop()

# ---------------------------------------------------------------------------
# 1. Scatter: R vs F, size = total_spend, color = rfm_segment
# ---------------------------------------------------------------------------
st.subheader("R vs F Score")
st.caption("Bubble size = total spend. Each dot = one user (sampled to 20k for performance).")

# Scatter over full dataset is heavy — sample for rendering
sample = df.sample(n=min(20_000, len(df)), random_state=42)

SEGMENT_ORDER = ["Champions", "Loyal", "At Risk", "Hibernating", "Lost"]
SEGMENT_COLORS = {
    "Champions":  "#00CC96",
    "Loyal":      "#636EFA",
    "At Risk":    "#FFA15A",
    "Hibernating":"#AB63FA",
    "Lost":       "#EF553B",
}

fig_scatter = px.scatter(
    sample,
    x="r_score",
    y="f_score",
    size="total_spend",
    color="rfm_segment",
    hover_data=["user_id", "total_spend", "rfm_score"],
    category_orders={"rfm_segment": SEGMENT_ORDER},
    color_discrete_map=SEGMENT_COLORS,
    size_max=30,
    labels={
        "r_score":     "Recency Score (5 = most recent)",
        "f_score":     "Frequency Score (5 = most frequent)",
        "rfm_segment": "Segment",
    },
    opacity=0.65,
)
fig_scatter.update_layout(
    xaxis=dict(tickmode="linear", tick0=1, dtick=1),
    yaxis=dict(tickmode="linear", tick0=1, dtick=1),
    hovermode="closest",
    height=500,
)
st.plotly_chart(fig_scatter, use_container_width=True)

show_sql("RFM Users", queries.RFM_USERS)

st.divider()

# ---------------------------------------------------------------------------
# 2. Segments bar: user count + % per segment
# ---------------------------------------------------------------------------
st.subheader("Segment Breakdown")

# Ensure consistent segment order
seg["rfm_segment"] = seg["rfm_segment"].astype("category").cat.set_categories(
    SEGMENT_ORDER, ordered=True
)
seg = seg.sort_values("rfm_segment")

fig_bar = px.bar(
    seg,
    x="rfm_segment",
    y="users",
    text="pct",
    color="rfm_segment",
    color_discrete_map=SEGMENT_COLORS,
    category_orders={"rfm_segment": SEGMENT_ORDER},
    labels={"rfm_segment": "Segment", "users": "Users", "pct": "Share (%)"},
)
fig_bar.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
fig_bar.update_layout(showlegend=False, yaxis_title="Users")
st.plotly_chart(fig_bar, use_container_width=True)

show_sql("RFM Segments", queries.RFM_SEGMENTS)

st.divider()

# ---------------------------------------------------------------------------
# 3. Drill table: top-50 users for selected segment
# ---------------------------------------------------------------------------
st.subheader("Segment Drill-Down")

segment_options = ["All"] + SEGMENT_ORDER
selected_segment = st.selectbox("Select segment", segment_options, index=0)

if selected_segment == "All":
    drill = df.nlargest(50, "total_spend")
else:
    drill = df[df["rfm_segment"] == selected_segment].nlargest(50, "total_spend")

st.caption(f"Top 50 users by total spend · segment: **{selected_segment}**")

st.dataframe(
    drill[["user_id", "rfm_segment", "rfm_score", "r_score", "f_score", "m_score",
           "total_purchases", "total_spend", "last_purchase_date"]]
    .rename(columns={
        "user_id":           "User ID",
        "rfm_segment":       "Segment",
        "rfm_score":         "RFM Score",
        "r_score":           "R",
        "f_score":           "F",
        "m_score":           "M",
        "total_purchases":   "Orders",
        "total_spend":       "Total Spend ($)",
        "last_purchase_date":"Last Purchase",
    })
    .reset_index(drop=True),
    use_container_width=True,
    hide_index=True,
)
