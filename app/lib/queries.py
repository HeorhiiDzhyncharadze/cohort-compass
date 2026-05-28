"""All SQL strings live here — single source of truth for 'Show SQL' toggle.

Convention:
  - Module-level constants for static queries (no filters).
  - Functions for parameterised queries (accept filter dict, return SQL string).
  - NEVER write SQL inline in page files.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Overview / KPI Pulse
# ---------------------------------------------------------------------------

# TODO: write SQL that returns one row with columns:
#   gmv, orders, buyers, cvr, aov, repeat_rate
# Source: fct_purchases + dim_users
KPI_SUMMARY = """
-- TODO: write KPI summary query
SELECT
    NULL::DOUBLE AS gmv,
    NULL::BIGINT AS orders,
    NULL::BIGINT AS buyers,
    NULL::DOUBLE AS cvr,
    NULL::DOUBLE AS aov,
    NULL::DOUBLE AS repeat_rate
"""

# TODO: write SQL that returns daily GMV trend
# Columns: event_day, gmv, gmv_7d_ma
# Source: fct_purchases
GMV_TREND = """
-- TODO: write daily GMV trend with 7-day moving average
SELECT
    NULL::DATE   AS event_day,
    NULL::DOUBLE AS gmv,
    NULL::DOUBLE AS gmv_7d_ma
LIMIT 0
"""

# TODO: write SQL that returns category mix (top 10 by GMV)
# Columns: category_code, gmv, pct
# Source: fct_purchases
CATEGORY_MIX = """
-- TODO: write category GMV mix
SELECT
    NULL::VARCHAR AS category_code,
    NULL::DOUBLE  AS gmv,
    NULL::DOUBLE  AS pct
LIMIT 0
"""

# ---------------------------------------------------------------------------
# Funnel
# ---------------------------------------------------------------------------

# Static monthly funnel — already in mart_funnel
FUNNEL_MONTHLY = "SELECT * FROM mart_funnel ORDER BY event_date"

# ---------------------------------------------------------------------------
# Cohort Retention
# ---------------------------------------------------------------------------

COHORT_RETENTION = "SELECT * FROM mart_cohorts ORDER BY cohort_month, period_number"

# ---------------------------------------------------------------------------
# RFM
# ---------------------------------------------------------------------------

RFM_USERS    = "SELECT * FROM mart_rfm"
RFM_SEGMENTS = """
SELECT rfm_segment,
       COUNT(*)                                   AS users,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
FROM mart_rfm
GROUP BY rfm_segment
ORDER BY users DESC
"""

# ---------------------------------------------------------------------------
# LTV
# ---------------------------------------------------------------------------

LTV_DISTRIBUTION = "SELECT * FROM mart_ltv ORDER BY total_spend DESC"

# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------

ANOMALIES = "SELECT * FROM mart_anomalies ORDER BY event_day"

# ---------------------------------------------------------------------------
# Customer Journey (Sankey)
# ---------------------------------------------------------------------------

JOURNEY_TRANSITIONS = "SELECT * FROM mart_journey ORDER BY transition_count DESC"

# ---------------------------------------------------------------------------
# Churn (filled after ML step)
# ---------------------------------------------------------------------------

CHURN_SCORES = """
-- Available after `make ml` populates scored_users table
SELECT * FROM scored_users ORDER BY churn_probability DESC
"""
