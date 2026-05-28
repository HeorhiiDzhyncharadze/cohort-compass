"""Sidebar global filters — applied across all pages."""

from __future__ import annotations

import streamlit as st

from lib import db

# Cache category / brand lists so sidebar doesn't re-query on every interaction
@st.cache_data(ttl=3600)
def _load_categories() -> list[str]:
    df = db.query("SELECT DISTINCT category_code FROM fct_events WHERE category_code IS NOT NULL ORDER BY 1")
    return df["category_code"].tolist()


@st.cache_data(ttl=3600)
def _load_brands() -> list[str]:
    df = db.query("SELECT DISTINCT brand FROM fct_events WHERE brand IS NOT NULL ORDER BY 1")
    return df["brand"].tolist()


def render_sidebar() -> dict:
    """Render sidebar widgets and return filter dict.

    Returns:
        {
            "date_from":   str  "YYYY-MM-DD",
            "date_to":     str  "YYYY-MM-DD",
            "categories":  list[str] | [],
            "brands":      list[str] | [],
            "price_tiers": list[str] | [],
            "show_sql":    bool,
        }
    """
    st.sidebar.title("Cohort Compass")
    st.sidebar.markdown("---")

    # Date range
    st.sidebar.subheader("Date range")
    date_from = st.sidebar.date_input("From", value=None, key="date_from")
    date_to   = st.sidebar.date_input("To",   value=None, key="date_to")

    st.sidebar.markdown("---")

    # Category filter
    st.sidebar.subheader("Category")
    all_categories = _load_categories()
    categories = st.sidebar.multiselect(
        "Select categories", all_categories, default=[], key="categories"
    )

    # Brand filter
    st.sidebar.subheader("Brand")
    all_brands = _load_brands()
    brands = st.sidebar.multiselect(
        "Select brands", all_brands, default=[], key="brands"
    )

    # Price tier
    st.sidebar.subheader("Price tier")
    price_tiers = st.sidebar.multiselect(
        "Select tiers",
        ["Low (<$50)", "Mid ($50–$200)", "High (>$200)"],
        default=[],
        key="price_tiers",
    )

    st.sidebar.markdown("---")

    # Show SQL toggle
    show_sql = st.sidebar.toggle("🔍 Show SQL", value=False, key="show_sql_global")

    return {
        "date_from":   str(date_from) if date_from else "2019-10-01",
        "date_to":     str(date_to)   if date_to   else "2020-04-30",
        "categories":  categories,
        "brands":      brands,
        "price_tiers": price_tiers,
        "show_sql":    show_sql,
    }


def price_tier_clause(tiers: list[str]) -> str:
    """Convert price tier selections to SQL WHERE fragment."""
    clauses = []
    if "Low (<$50)"      in tiers: clauses.append("price < 50")
    if "Mid ($50–$200)"  in tiers: clauses.append("(price >= 50 AND price <= 200)")
    if "High (>$200)"    in tiers: clauses.append("price > 200")
    return f"({' OR '.join(clauses)})" if clauses else "TRUE"
