"""Cohort Compass — Customer Journey (Sankey)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import db, queries
from lib.filters import render_sidebar
from lib.sql_toggle import show_sql

st.set_page_config(
    page_title="Customer Journey · Cohort Compass",
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
st.title("🌊 Customer Journey")
st.caption(
    "Session-level event-type transitions · source: mart_journey  "
    "· first load ~30–60 s (LAG over 285 M rows), cached for 1 h after."
)
st.divider()

# ---------------------------------------------------------------------------
# Data — cached because mart_journey is a VIEW over 285M rows
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def load_journey() -> pd.DataFrame:
    return db.query(queries.JOURNEY_TRANSITIONS)


with st.spinner("Loading journey data — first load may take ~60 s …"):
    df = load_journey()

if df.empty:
    st.warning("No data. Run `make dbt-build` first.")
    st.stop()

# ---------------------------------------------------------------------------
# 1. Sankey diagram
# ---------------------------------------------------------------------------
st.subheader("Event-Type Transition Flow")
st.caption(
    "Each node = one event type. Arrow width = number of session transitions. "
    "Read left-to-right: what users did *before* → what they did *next*."
)

EVENT_COLORS: dict[str, str] = {
    "view":             "#636EFA",
    "cart":             "#FFA15A",
    "remove_from_cart": "#EF553B",
    "purchase":         "#00CC96",
}
DEFAULT_COLOR = "#AAAAAA"

# Build ordered node list (preserve encounter order, dedup)
all_events: list[str] = list(
    dict.fromkeys(list(df["from_event"]) + list(df["to_event"]))
)
node_idx: dict[str, int] = {e: i for i, e in enumerate(all_events)}
node_colors = [EVENT_COLORS.get(e, DEFAULT_COLOR) for e in all_events]

fig_sankey = go.Figure(
    go.Sankey(
        arrangement="snap",
        node=dict(
            label=all_events,
            color=node_colors,
            pad=20,
            thickness=20,
            line=dict(color="white", width=0.5),
        ),
        link=dict(
            source=[node_idx[e] for e in df["from_event"]],
            target=[node_idx[e] for e in df["to_event"]],
            value=df["transition_count"].tolist(),
            color="rgba(150,150,150,0.25)",
        ),
    )
)
fig_sankey.update_layout(
    height=500,
    margin=dict(l=20, r=20, t=20, b=20),
)
st.plotly_chart(fig_sankey, use_container_width=True)

show_sql("Journey Transitions", queries.JOURNEY_TRANSITIONS)

st.divider()

# ---------------------------------------------------------------------------
# 2. Top transitions table
# ---------------------------------------------------------------------------
st.subheader("Top Transitions")

total_transitions = int(df["transition_count"].sum())
st.caption(
    f"{len(df):,} unique transition pairs · "
    f"{total_transitions:,} total transitions across all sessions"
)

# Enrich with pct column for context
table_df = df.copy()
table_df["pct"] = (table_df["transition_count"] / total_transitions * 100).round(2)

st.dataframe(
    table_df.head(20).rename(columns={
        "from_event":       "From",
        "to_event":         "To",
        "transition_count": "Count",
        "pct":              "Share (%)",
    }),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ---------------------------------------------------------------------------
# 3. Key insight callouts
# ---------------------------------------------------------------------------
st.subheader("Reading the Flow")

purchase_rows = df[df["to_event"] == "purchase"]["transition_count"].sum()
remove_rows   = df[df["to_event"] == "remove_from_cart"]["transition_count"].sum()
view_to_cart  = df[(df["from_event"] == "view") & (df["to_event"] == "cart")]["transition_count"].sum()

i1, i2, i3 = st.columns(3)
i1.metric(
    "Transitions → purchase",
    f"{purchase_rows:,}",
    help="All session steps that ended in a purchase event.",
)
i2.metric(
    "Transitions → remove_from_cart",
    f"{remove_rows:,}",
    help="Steps that ended in cart abandonment.",
)
i3.metric(
    "view → cart",
    f"{view_to_cart:,}",
    help="Direct add-to-cart after a view — a high-intent signal.",
)
