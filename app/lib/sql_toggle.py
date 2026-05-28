"""'Show SQL' toggle component — renders beside every chart."""

from __future__ import annotations

import streamlit as st


def show_sql(label: str, sql: str) -> None:
    """Render an expander with syntax-highlighted SQL.

    Usage:
        st.plotly_chart(fig)
        show_sql("Funnel SQL", queries.FUNNEL)
    """
    with st.expander(f"🔍 Show SQL — {label}"):
        st.code(sql.strip(), language="sql")
        st.button(
            "📋 Copy",
            key=f"copy_{label}",
            on_click=_copy_to_clipboard,
            args=(sql,),
            help="Copy SQL to clipboard",
        )


def _copy_to_clipboard(text: str) -> None:
    # Streamlit Community Cloud doesn't support pyperclip;
    # inject JS workaround instead.
    st.components.v1.html(
        f"""
        <script>
        navigator.clipboard.writeText({repr(text)});
        </script>
        """,
        height=0,
    )
