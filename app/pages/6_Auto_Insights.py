"""Cohort Compass — Auto-Insights (anomaly detection)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import db, queries
from lib.filters import render_sidebar
from lib.sql_toggle import show_sql

st.set_page_config(
    page_title="Auto-Insights · Cohort Compass",
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
st.title("🔍 Auto-Insights")
st.caption(
    "Automated anomaly detection via rolling 30-day Z-score on daily CVR  "
    "· source: mart_anomalies  · |Z| > 2 flagged as anomalous"
)
st.divider()

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
df = db.query(queries.ANOMALIES)

if df.empty:
    st.warning("No data. Run `make dbt-build` first.")
    st.stop()

df["event_day"] = pd.to_datetime(df["event_day"])
anomalies = df[df["is_anomaly"] == True].copy()

# ---------------------------------------------------------------------------
# 1. KPI cards
# ---------------------------------------------------------------------------
total_days    = len(df)
anomaly_days  = len(anomalies)
avg_cvr       = df["cvr"].mean() * 100
peak_anomaly  = anomalies["z_score"].abs().max() if not anomalies.empty else 0.0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Days Tracked",    f"{total_days}")
k2.metric("Anomaly Days",    f"{anomaly_days}  ({anomaly_days/total_days*100:.0f}%)")
k3.metric("Avg Daily CVR",   f"{avg_cvr:.2f}%")
k4.metric("Peak |Z-score|",  f"{peak_anomaly:.2f}")

show_sql("Anomalies", queries.ANOMALIES)

st.divider()

# ---------------------------------------------------------------------------
# 2. CVR timeline with anomalies highlighted
# ---------------------------------------------------------------------------
st.subheader("Daily CVR with Anomaly Detection")
st.caption("Blue line = daily CVR · dashed grey = 30-day rolling average · red dots = anomalies (|Z| > 2)")

fig = go.Figure()

# CVR line
fig.add_trace(go.Scatter(
    x=df["event_day"],
    y=(df["cvr"] * 100).round(3),
    mode="lines",
    name="Daily CVR (%)",
    line=dict(color="#636EFA", width=1.5),
    hovertemplate="%{x|%b %d}: CVR = %{y:.3f}%<extra></extra>",
))

# Rolling avg dashed
fig.add_trace(go.Scatter(
    x=df["event_day"],
    y=(df["rolling_avg_cvr"] * 100).round(3),
    mode="lines",
    name="30-day Rolling Avg (%)",
    line=dict(color="#AAAAAA", width=1, dash="dash"),
    hovertemplate="%{x|%b %d}: Avg = %{y:.3f}%<extra></extra>",
))

# Anomaly markers
if not anomalies.empty:
    fig.add_trace(go.Scatter(
        x=anomalies["event_day"],
        y=(anomalies["cvr"] * 100).round(3),
        mode="markers",
        name="Anomaly",
        marker=dict(color="#EF553B", size=10, symbol="circle", line=dict(color="white", width=1)),
        customdata=anomalies[["z_score"]].values,
        hovertemplate="%{x|%b %d}: CVR = %{y:.3f}%  Z = %{customdata[0]:.2f}<extra></extra>",
    ))

fig.update_layout(
    xaxis_title="Date",
    yaxis_title="CVR (%)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=420,
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# 3. Narrative insight cards
# ---------------------------------------------------------------------------
st.subheader(f"{'🚨 ' if not anomalies.empty else ''}Anomaly Narratives")

if anomalies.empty:
    st.success("No anomalies detected in this period.")
else:
    st.caption(f"{len(anomalies)} anomalous days detected — narratives generated automatically from Z-score data.")

    def make_narrative(row: pd.Series) -> str:
        direction = "spiked" if row["z_score"] > 0 else "dropped"
        cvr_pct   = row["cvr"] * 100
        avg_pct   = row["rolling_avg_cvr"] * 100
        diff_pp   = cvr_pct - avg_pct
        date_str  = row["event_day"].strftime("%b %d")
        z         = row["z_score"]
        sign      = "+" if diff_pp > 0 else ""
        viewers   = int(row["viewers"])
        buyers    = int(row["buyers"])
        return (
            f"**{date_str}** — CVR {direction} to **{cvr_pct:.2f}%** "
            f"({sign}{diff_pp:.2f} pp vs 30-day avg of {avg_pct:.2f}%) · "
            f"Z-score: **{z:+.2f}** · "
            f"{viewers:,} viewers → {buyers:,} buyers"
        )

    for _, row in anomalies.sort_values("event_day").iterrows():
        icon = "📈" if row["z_score"] > 0 else "📉"
        severity = "🔴" if abs(row["z_score"]) > 3 else "🟡"
        with st.container():
            st.markdown(f"{severity} {icon}  {make_narrative(row)}")

st.divider()

# ---------------------------------------------------------------------------
# 4. Full anomaly table
# ---------------------------------------------------------------------------
st.subheader("Anomaly Details Table")

if anomalies.empty:
    st.info("No anomalies to display.")
else:
    display = anomalies[[
        "event_day", "cvr", "rolling_avg_cvr", "rolling_stddev_cvr",
        "z_score", "viewers", "buyers",
    ]].copy()

    display["cvr_pct"]     = (display["cvr"] * 100).round(3)
    display["avg_cvr_pct"] = (display["rolling_avg_cvr"] * 100).round(3)
    display["diff_pp"]     = (display["cvr_pct"] - display["avg_cvr_pct"]).round(3)

    st.dataframe(
        display[[
            "event_day", "cvr_pct", "avg_cvr_pct", "diff_pp",
            "z_score", "viewers", "buyers",
        ]]
        .rename(columns={
            "event_day":   "Date",
            "cvr_pct":     "CVR (%)",
            "avg_cvr_pct": "30d Avg CVR (%)",
            "diff_pp":     "Diff (pp)",
            "z_score":     "Z-score",
            "viewers":     "Viewers",
            "buyers":      "Buyers",
        })
        .reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )
