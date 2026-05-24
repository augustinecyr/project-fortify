"""
Project Fortify - Main Entry Point
Navigation hub for the dashboard.
"""
import streamlit as st
import sys
import time
from pathlib import Path

st.set_page_config(
    page_title="Project Fortify Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Project Fortify - Infrastructure Health Monitoring Platform v0.8.0"
    }
)

st.markdown("""
<style>
    .stApp header [data-testid="stStatusWidget"] {
        display: none !important;
    }
    .stApp header button[kind="header"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

sys.path.insert(0, str(Path(__file__).parent / "utils"))
from session import load_token, clear_token

login_page = st.Page("pages/login.py", title="Login", icon=":material/login:")

if not load_token():
    pg = st.navigation([login_page])
    pg.run()

elif st.session_state.pop("just_logged_in", False):
    # Fixed overlay sits above all Streamlit chrome (header, sidebar, footer).
    # The CSS progress bar animates in the browser while Python sleeps,
    # giving the browser time to fully commit this as the stable render state
    # before home.py runs. No VM data calls happen here — home.py fetches its
    # own data and the browser holds this screen during that call.
    st.markdown("""
    <style>
    html, body, .stApp { overflow: hidden !important; }
    @keyframes progressAnim {
        from { width: 0%; }
        to   { width: 100%; }
    }
    .loading-overlay {
        position: fixed;
        inset: 0;
        z-index: 9999;
        background: white;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.6rem;
    }
    .loading-icon  { font-size: 2.5rem; line-height: 1; margin-bottom: 0.25rem; }
    .loading-title { font-size: 1.25rem; font-weight: 700; color: #0f172a; margin: 0; }
    .loading-sub   { font-size: 0.875rem; color: #64748b; margin: 0 0 0.5rem 0; }
    .progress-track {
        width: 220px;
        height: 4px;
        background: #e2e8f0;
        border-radius: 2px;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        background: #3b82f6;
        border-radius: 2px;
        animation: progressAnim 2.8s ease-in-out forwards;
    }
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
            animation: _cov 0.6s ease-out 0.8s both;
            pointer-events: none;
        }
        </style>
        <div class="_cover"></div>
        """, unsafe_allow_html=True)

    pages = {
        "Monitoring": [
            st.Page("pages/home.py", title="Home", icon=":material/home:"),
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
