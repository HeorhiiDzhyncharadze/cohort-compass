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
SELECT
    SUM(p.price)                                                          AS gmv,
    COUNT(*)                                                              AS orders,
    COUNT(DISTINCT p.user_id)                                             AS buyers,
    ROUND(
        COUNT(DISTINCT p.user_id) * 1.0
        / NULLIF((SELECT SUM(viewers) FROM mart_funnel), 0),
        4
    )                                                                     AS cvr,
    ROUND(SUM(p.price) / NULLIF(COUNT(*), 0), 2)                         AS aov,
    ROUND(
        COUNT(DISTINCT CASE WHEN u.total_purchases > 1 THEN u.user_id END) * 1.0
        / NULLIF(COUNT(DISTINCT u.user_id), 0),
        4
    )                                                                     AS repeat_rate
FROM fct_purchases p
JOIN dim_users u ON p.user_id = u.user_id
"""

# TODO: write SQL that returns daily GMV trend
# Columns: event_day, gmv, gmv_7d_ma
# Source: fct_purchases
GMV_TREND = """
SELECT
    event_time::DATE                                                                   AS event_day,
    SUM(price)                                                                         AS gmv,
    AVG(SUM(price)) OVER (
        ORDER BY event_time::DATE
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    )                                                                                  AS gmv_7d_ma
FROM fct_purchases
GROUP BY event_time::DATE
ORDER BY event_day
"""

# TODO: write SQL that returns category mix (top 10 by GMV)
# Columns: category_code, gmv, pct
# Source: fct_purchases
CATEGORY_MIX = """
SELECT
    category_code,
    SUM(price)                                                AS gmv,
    ROUND(SUM(price) * 100.0 / SUM(SUM(price)) OVER(), 1)   AS pct
FROM fct_purchases
WHERE category_code IS NOT NULL
GROUP BY category_code
ORDER BY gmv DESC
LIMIT 10
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

CHURN_FEATURES = "SELECT * FROM mart_churn_features"

CHURN_SCORES = """
-- Available after `make ml` populates scored_users table
SELECT * FROM scored_users ORDER BY churn_probability DESC
"""
