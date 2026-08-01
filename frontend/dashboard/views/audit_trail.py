"""
Audit Trail — operator-facing view of the persisted security audit log.

Consumes the operator-gated GET /api/v1/audit endpoint with server-side
pagination and filtering. Access is restricted to operator/admin both in the
navigation (app.py) and here as defence in depth.
"""
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st

# ---- PATH FIXES ----
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))

try:
    from api_client import FortifyAPIClient
    from session import load_token
except ImportError:
    st.error("Unable to load the audit view. Verify the backend is running and refresh.")
    st.stop()

st.set_page_config(page_title="Audit Trail", page_icon="📜", layout="wide")

# ---- ACCESS GUARD (defence in depth; nav already hides this from viewers) ----
_role = st.session_state.get("role", "")
if _role not in ("operator", "admin"):
    st.error("You do not have permission to view the audit trail.")
    st.stop()

# ---- CSS (shared design system) ----
st.markdown("""
<style>
.block-container { padding-top: 1.5rem !important; }
.page-header-title { font-size: 1.6rem; font-weight: 700; color: #0f172a;
    letter-spacing: -0.5px; margin: 0 0 0.15rem 0; line-height: 1.2; }
.page-header-sub { font-size: 0.825rem; color: #64748b; margin: 0; font-weight: 400; }
.header-divider { border: none; border-bottom: 1px solid #e2e8f0; margin: 0.75rem 0 1.5rem 0; }
.section-header { font-size: 1.25rem; font-weight: 600; color: #0f172a; margin: 1.5rem 0 0.5rem 0; }
.error-card { background: #fee2e2; border-left: 4px solid #ef4444; border-radius: 0.5rem;
    padding: 1rem 1.25rem; color: #7f1d1d; font-size: 0.875rem; margin-bottom: 1rem; }
.error-card strong { display: block; color: #991b1b; font-size: 0.9rem; margin-bottom: 0.25rem; }
</style>
""", unsafe_allow_html=True)

# ---- BADGE / FORMAT HELPERS ----
_DANGER_EVENTS = {
    "auth_failure", "auth_failure_inactive", "authz_denied",
    "token_rejected", "password_change_failed", "audit_persist_failed",
}
_SUCCESS_EVENTS = {"auth_success"}


def _pill(text, bg, fg):
    return (f'<span style="background:{bg};color:{fg};padding:2px 10px;border-radius:9999px;'
            f'font-size:0.72rem;font-weight:600;white-space:nowrap;">{text}</span>')


def event_pill(event):
    if event in _DANGER_EVENTS:
        return _pill(event, "#fee2e2", "#991b1b")
    if event in _SUCCESS_EVENTS:
        return _pill(event, "#dcfce7", "#166534")
    return _pill(event, "#e0e7ff", "#3730a3")  # state-change events


def outcome_pill(success):
    if success is True:
        return _pill("✓ success", "#dcfce7", "#166534")
    if success is False:
        return _pill("✗ failed", "#fee2e2", "#991b1b")
    return '<span style="color:#94a3b8;">—</span>'


def fmt_ts(value):
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value)


def esc(value):
    if value is None:
        return "—"
    return (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ---- INIT ----
token = load_token()
api_client = FortifyAPIClient()

# ---- HEADER ----
title_col, btn_col = st.columns([9, 0.4])
with title_col:
    st.markdown("""
        <div class="page-header-title">Audit Trail</div>
        <div class="page-header-sub">Persisted security events — authentication, authorization, and state changes</div>
    """, unsafe_allow_html=True)
with btn_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↻", help="Refresh", width="stretch"):
        st.rerun()
st.markdown('<hr class="header-divider">', unsafe_allow_html=True)

# ---- FILTERS ----
_EVENT_OPTIONS = [
    "All events", "auth_success", "auth_failure", "auth_failure_inactive",
    "authz_denied", "token_rejected", "user_created", "user_updated",
    "user_password_reset", "user_password_changed", "vm_updated", "ai_cache_cleared",
]
f1, f2, f3 = st.columns([2, 2, 1])
with f1:
    event_choice = st.selectbox("Event type", _EVENT_OPTIONS, index=0)
with f2:
    actor_filter = st.text_input("Actor (username)", placeholder="e.g. admin").strip()
with f3:
    page_size = st.selectbox("Page size", [25, 50, 100], index=0)

event_filter = None if event_choice == "All events" else event_choice

# Reset to the first page whenever a filter or page size changes.
_filter_sig = (event_filter, actor_filter, page_size)
if st.session_state.get("_audit_filter_sig") != _filter_sig:
    st.session_state["_audit_filter_sig"] = _filter_sig
    st.session_state["_audit_offset"] = 0

offset = st.session_state.get("_audit_offset", 0)

# ---- FETCH ----
data = api_client.get_audit_events(
    token=token, limit=page_size, offset=offset,
    event=event_filter, actor=(actor_filter or None),
)

if data is None:
    st.markdown('<div class="error-card"><strong>Unable to load the audit trail</strong>'
                'Verify the backend is running and refresh the page.</div>', unsafe_allow_html=True)
    st.stop()

total = data.get("total", 0)
entries = data.get("entries", [])

# ---- TABLE ----
st.markdown(f'<div class="section-header">Events <span style="color:#94a3b8;font-size:0.85rem;">'
            f'({total} total)</span></div>', unsafe_allow_html=True)

if not entries:
    st.info("No audit events match the current filters.")
    st.stop()

rows = []
for e in entries:
    rows.append(f"""
    <tr style="border-bottom:1px solid #f1f5f9;">
        <td style="padding:0.6rem 1rem;color:#334155;white-space:nowrap;font-family:monospace;font-size:0.8rem;">{fmt_ts(e.get('timestamp'))}</td>
        <td style="padding:0.6rem 1rem;">{event_pill(esc(e.get('event')))}</td>
        <td style="padding:0.6rem 1rem;color:#0f172a;font-weight:600;">{esc(e.get('actor'))}</td>
        <td style="padding:0.6rem 1rem;color:#475569;">{esc(e.get('role'))}</td>
        <td style="padding:0.6rem 1rem;color:#475569;font-family:monospace;font-size:0.8rem;">{esc(e.get('target'))}</td>
        <td style="padding:0.6rem 1rem;color:#475569;">{esc(e.get('detail'))}</td>
        <td style="padding:0.6rem 1rem;color:#475569;font-family:monospace;font-size:0.8rem;">{esc(e.get('ip'))}</td>
        <td style="padding:0.6rem 1rem;">{outcome_pill(e.get('success'))}</td>
    </tr>""")

th = ("padding:0.6rem 1rem;color:#64748b;font-weight:600;font-size:0.72rem;text-transform:uppercase;"
      "letter-spacing:0.05em;text-align:left;background:#f8fafc;border-bottom:2px solid #e2e8f0;")
thead_html = f"""<thead><tr>
<th style="{th}">Time (UTC)</th><th style="{th}">Event</th><th style="{th}">Actor</th>
<th style="{th}">Role</th><th style="{th}">Target</th><th style="{th}">Detail</th>
<th style="{th}">IP</th><th style="{th}">Outcome</th>
</tr></thead>"""

table_html = (
    '<div style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;overflow-x:auto;margin-top:0.5rem;">'
    '<table style="width:100%;border-collapse:collapse;font-size:0.875rem;">'
    f'{thead_html}<tbody>{"".join(rows)}</tbody></table></div>'
)
st.markdown(table_html, unsafe_allow_html=True)

# ---- SERVER-SIDE PAGINATION ----
import math
total_pages = max(1, math.ceil(total / page_size))
current_page = offset // page_size + 1
prev_col, info_col, next_col = st.columns([1, 3, 1])
with prev_col:
    if st.button("← Prev", disabled=offset <= 0, use_container_width=True):
        st.session_state["_audit_offset"] = max(0, offset - page_size)
        st.rerun()
with info_col:
    shown_to = min(offset + page_size, total)
    st.markdown(
        f"<div style='text-align:center;color:#64748b;font-size:0.8rem;padding-top:0.45rem;'>"
        f"Page {current_page} of {total_pages} &nbsp;·&nbsp; {offset + 1}–{shown_to} of {total}</div>",
        unsafe_allow_html=True,
    )
with next_col:
    if st.button("Next →", disabled=offset + page_size >= total, use_container_width=True):
        st.session_state["_audit_offset"] = offset + page_size
        st.rerun()

st.divider()
st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Project Fortify v1.1.2")
