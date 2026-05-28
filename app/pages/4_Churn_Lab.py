"""Cohort Compass — Churn Lab."""

import pandas as pd
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
# 4. ML Churn Scores — populated after `make ml`
# ---------------------------------------------------------------------------
st.subheader("ML Churn Scores")

try:
    scored = db.query(queries.CHURN_SCORES)
except Exception:
    scored = pd.DataFrame()

if scored.empty:
    st.info(
        "Run `make ml` to train the churn model and populate `scored_users`. "
        "Churn probabilities will appear here automatically.",
        icon="🤖",
    )
    st.stop()

# --- KPI row ---
high_risk = (scored["churn_probability"] >= 0.5).sum()
avg_prob  = scored["churn_probability"].mean()

m1, m2, m3 = st.columns(3)
m1.metric("Users Scored",    f"{len(scored):,}")
m2.metric("Predicted Churn", f"{high_risk:,}  ({high_risk/len(scored)*100:.1f}%)")
m3.metric("Avg Churn Prob",  f"{avg_prob:.1%}")

show_sql("ML Scores", queries.CHURN_SCORES)

st.divider()

# --- Threshold slider (defined before column blocks so value is in scope) ---
st.subheader("What-If: Intervention Simulator")
st.caption("Set probability threshold to target the right cohort for a re-engagement campaign.")

threshold = st.slider(
    "Churn probability threshold",
    min_value=0.10, max_value=0.90, value=0.50, step=0.05,
    format="%.2f",
)

col_hist, col_sim = st.columns([3, 2])

with col_hist:
    fig_hist = px.histogram(
        scored,
        x="churn_probability",
        nbins=50,
        color_discrete_sequence=["#636EFA"],
        labels={"churn_probability": "Churn Probability"},
        title="Churn Probability Distribution",
    )
    fig_hist.add_vline(
        x=threshold,
        line_dash="dash",
        line_color="#EF553B",
        annotation_text=f"Threshold {threshold:.2f}",
        annotation_position="top right",
    )
    fig_hist.update_layout(bargap=0.05, yaxis_title="Users")
    st.plotly_chart(fig_hist, use_container_width=True)

with col_sim:
    targeted     = int((scored["churn_probability"] >= threshold).sum())
    pct_targeted = targeted / len(scored) * 100
    save_rate    = st.slider("Estimated save rate (%)", 5, 40, 15, 5)
    saved        = int(targeted * save_rate / 100)
    avg_spend    = float(df["total_spend"].mean())
    revenue_saved = saved * avg_spend

    st.metric("Users Targeted",     f"{targeted:,}  ({pct_targeted:.1f}%)")
    st.metric("Est. Users Saved",   f"{saved:,}")
    st.metric("Est. Revenue Saved", f"${revenue_saved:,.0f}")
    st.caption(
        f"Avg spend per user: ${avg_spend:.2f}. "
        "Revenue estimate assumes saved users retain their historical average spend."
    )

st.divider()

# --- Top high-risk users table ---
st.subheader(f"Top 50 Users — Churn Probability ≥ {threshold:.2f}")

top_risk = scored[scored["churn_probability"] >= threshold].head(50)

if top_risk.empty:
    st.info("No users above this threshold. Lower the slider.")
else:
    st.dataframe(
        top_risk[["user_id", "churn_probability", "churn_label"]]
        .rename(columns={
            "user_id":           "User ID",
            "churn_probability": "Churn Probability",
            "churn_label":       "Predicted Churned",
        })
        .reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )
