"""
Helper functions for the dashboard.
"""
import math
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional


def paginated_table(rows: List[str], thead_html: str, key: str,
                    page_size: int = 10, caption: Optional[str] = None) -> None:
    """
    Render a styled HTML table with Prev/Next pagination controls.

    Pages that build their own row markup pass a list of <tr>…</tr> strings and
    the full <thead>…</thead> block; this slices the rows to the active page and
    renders the surrounding table chrome + controls. Page state is kept per-table
    in st.session_state under a key derived from `key`.

    Args:
        rows: list of <tr>…</tr> HTML strings, one per data row.
        thead_html: the full <thead>…</thead> block.
        key: unique identifier for this table's pagination state.
        page_size: number of rows shown per page.
        caption: optional caption rendered beneath the table.
    """
    total = len(rows)
    total_pages = max(1, math.ceil(total / page_size))
    state_key = f"_page_{key}"
    page = min(max(st.session_state.get(state_key, 1), 1), total_pages)
    st.session_state[state_key] = page

    start = (page - 1) * page_size
    visible = rows[start:start + page_size]

    # Build the table as a single string that begins at column 0. Streamlit's
    # markdown ends an HTML block at the first blank/whitespace-only line and
    # renders anything indented afterwards as a code block — so we must avoid
    # leading indentation on substitution lines.
    table_html = (
        '<div style="border:1px solid #e2e8f0;border-radius:8px;'
        'overflow:hidden;overflow-x:auto;margin-top:0.5rem;">'
        '<table style="width:100%;border-collapse:collapse;font-size:0.875rem;">'
        f'{thead_html}'
        f'<tbody>{"".join(visible)}</tbody>'
        '</table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

    if total_pages > 1:
        prev_col, info_col, next_col = st.columns([1, 3, 1])
        with prev_col:
            if st.button("← Prev", key=f"{key}_prev", disabled=page <= 1,
                         use_container_width=True):
                st.session_state[state_key] = page - 1
                st.rerun()
        with info_col:
            st.markdown(
                f"<div style='text-align:center;color:#64748b;font-size:0.8rem;"
                f"padding-top:0.45rem;'>Page {page} of {total_pages} "
                f"&nbsp;·&nbsp; {start + 1}–{min(start + page_size, total)} of {total}</div>",
                unsafe_allow_html=True,
            )
        with next_col:
            if st.button("Next →", key=f"{key}_next", disabled=page >= total_pages,
                         use_container_width=True):
                st.session_state[state_key] = page + 1
                st.rerun()

    if caption:
        st.caption(caption)


def get_health_status_class(score: int) -> tuple:
    """
    Get CSS class and label for health score.
    
    Args:
        score: Health score (0-100)
    
    Returns:
        Tuple of (css_class, status_label, color)
    """
    if score >= 80:
        return "health-score-excellent", "Excellent", "#28a745"
    elif score >= 65:
        return "health-score-good", "Good", "#5cb85c"
    elif score >= 50:
        return "health-score-warning", "Warning", "#ffc107"
    else:
        return "health-score-critical", "Critical", "#dc3545"


def export_to_csv(data: List[Dict], filename: str) -> str:
    """
    Convert data to CSV format.
    
    Args:
        data: List of dictionaries to export
        filename: Output filename
    
    Returns:
        CSV string
    """
    df = pd.DataFrame(data)
    return df.to_csv(index=False)


def format_timestamp(timestamp: str) -> str:
    """
    Format ISO timestamp to readable format.
    
    Args:
        timestamp: ISO 8601 timestamp string
    
    Returns:
        Formatted timestamp string
    """
    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def calculate_time_range(hours: int = 24) -> tuple:
    """
    Calculate start and end timestamps for time range.
    
    Args:
        hours: Number of hours to look back
    
    Returns:
        Tuple of (start_time, end_time) as ISO strings
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    return start_time.isoformat(), end_time.isoformat()


def format_large_number(num: int) -> str:
    """
    Format large numbers with K/M suffixes.
    
    Args:
        num: Number to format
    
    Returns:
        Formatted string
    """
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    else:
        return str(num)