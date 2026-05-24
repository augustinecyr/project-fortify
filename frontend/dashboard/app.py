"""
Project Fortify - Main Entry Point
Navigation hub for the dashboard.
"""
import streamlit as st
import sys
import time
from pathlib import Path
from streamlit_cookies_manager import CookieManager

st.set_page_config(
    page_title="Project Fortify Dashboard",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Project Fortify - Infrastructure Health Monitoring Platform v0.8.0"
    }
)

st.markdown("""
<style>
    .stApp header [data-testid="stStatusWidget"] { display: none !important; }
    .stApp header button[kind="header"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

sys.path.insert(0, str(Path(__file__).parent / "utils"))
from session import load_token, clear_token, save_token, COOKIE_KEY

# ---------------------------------------------------------------------------
# Cookie manager — blocks until the browser component has initialised and sent
# back the current cookies. st.stop() on the first render causes a brief blank
# screen (~100 ms) before the real page appears; this is unavoidable with any
# component-based cookie approach and is the price of reliable persistence.
# ---------------------------------------------------------------------------
_cookies = CookieManager(prefix="fortify_")

if not _cookies.ready():
    st.stop()   # wait for component → rerun with cookies available

# Hydrate session_state from cookie on fresh connection (browser refresh / new tab)
if not st.session_state.get("_logged_out") and not st.session_state.get("token"):
    _stored = _cookies.get(COOKIE_KEY)
    if _stored:
        st.session_state["token"] = _stored

# Write pending cookie set (queued by save_token() during login)
_set_token = st.session_state.pop("_set_token", None)
if _set_token:
    _cookies[COOKIE_KEY] = _set_token
    _cookies.save()

# Clear pending cookie (queued by clear_token() during logout)
if st.session_state.pop("_clear_token", False):
    if COOKIE_KEY in _cookies:
        del _cookies[COOKIE_KEY]
        _cookies.save()

# ---------------------------------------------------------------------------
# Navigation / auth gate
# ---------------------------------------------------------------------------
login_page = st.Page("pages/login.py", title="Login", icon=":material/login:")

if not load_token():
    pg = st.navigation([login_page])
    pg.run()

elif st.session_state.pop("just_logged_in", False):
    st.markdown("""
    <style>
    html, body, .stApp { overflow: hidden !important; }
    @keyframes progressAnim { from { width: 0%; } to { width: 100%; } }
    .loading-overlay {
        position: fixed; inset: 0; z-index: 9999; background: white;
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; gap: 0.6rem;
    }
    .loading-icon  { font-size: 2.5rem; line-height: 1; margin-bottom: 0.25rem; }
    .loading-title { font-size: 1.25rem; font-weight: 700; color: #0f172a; margin: 0; }
    .loading-sub   { font-size: 0.875rem; color: #64748b; margin: 0 0 0.5rem 0; }
    .progress-track { width: 220px; height: 4px; background: #e2e8f0; border-radius: 2px; overflow: hidden; }
    .progress-fill  { height: 100%; background: #3b82f6; border-radius: 2px;
                      animation: progressAnim 2.8s ease-in-out forwards; }
    </style>
    <div class="loading-overlay">
        <div class="loading-icon">🛡️</div>
        <div class="loading-title">Project Fortify</div>
        <div class="loading-sub">Signing you in…</div>
        <div class="progress-track"><div class="progress-fill"></div></div>
    </div>
    """, unsafe_allow_html=True)
    st.session_state["_cover"] = True
    time.sleep(3)
    st.rerun()

else:
    if st.session_state.pop("_cover", False):
        st.markdown("""
        <style>
        @keyframes _cov { 0% { opacity:1; } 100% { opacity:0; } }
        ._cover {
            position: fixed; inset: 0; z-index: 99999; background: #ffffff;
            animation: _cov 0.6s ease-out 0.8s both; pointer-events: none;
        }
        </style>
        <div class="_cover"></div>
        """, unsafe_allow_html=True)

    # Intercept ?vm= query param produced when the browser follows an HTML link
    # to /vm_health_monitor?vm=xxx — Streamlit redirects that to /?vm=xxx, so we
    # catch it here and forward to the correct page via session_state.
    if st.query_params.get("vm"):
        st.session_state["_nav_vm_id"] = st.query_params["vm"]
        st.session_state.pop("vm_selector", None)
        st.switch_page("pages/vm_health_monitor.py")

    pages = {
        "Monitoring": [
            st.Page("pages/home.py", title="Home", icon=":material/home:", url_path="home"),
            st.Page("pages/vm_health_monitor.py", title="VM Health", icon=":material/health_and_safety:"),
        ],
        "Reports": [
            st.Page("pages/export_report.py", title="Export Report", icon=":material/download:"),
        ],
        "Optimization": [
            st.Page("pages/optimization.py", title="Cost Optimization", icon=":material/trending_down:"),
        ],
        "Security": [
            st.Page("pages/security_posture.py", title="Security Posture", icon=":material/security:"),
        ],
        "AI": [
            st.Page("pages/ai_insights.py", title="AI Insights", icon=":material/psychology:"),
        ]
    }
    pg = st.navigation(pages)

    with st.sidebar:
        username = st.session_state.get("username", "admin")
        st.caption(f"Signed in as **{username}**")
        if st.button("Sign out", icon=":material/logout:", use_container_width=True):
            clear_token()
            st.rerun()

    pg.run()
