"""
Project Fortify - Main Entry Point
Navigation hub for the dashboard.
"""
import streamlit as st
import sys
from pathlib import Path
from streamlit_cookies_manager import CookieManager

st.set_page_config(
    page_title="Project Fortify Dashboard",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _loading_screen(message: str):
    """Branded loading cover that fades out on its own.

    Rendered in the SAME run as the destination page, so that page renders
    behind it: the overlay holds opaque long enough to mask the fetch + paint,
    then fades to reveal the finished page. It only covers the sidebar/content
    while opaque (pointer-events disabled) — it does not persistently hide them.
    """
    st.markdown(f"""
    <style>
    @keyframes _lsProg {{ from {{ width: 0%; }} to {{ width: 100%; }} }}
    @keyframes _lsFade {{ 0% {{ opacity: 1; }} 100% {{ opacity: 0; }} }}
    .loading-overlay {{
        position: fixed; inset: 0; z-index: 99999; background: white;
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; gap: 0.6rem; pointer-events: none;
        animation: _lsFade 0.4s ease-out 1.3s both;
    }}
    .loading-icon  {{ font-size: 2.5rem; line-height: 1; margin-bottom: 0.75rem; }}
    .loading-sub   {{ font-size: 0.875rem; color: #64748b; margin: 0 0 0.75rem 0; }}
    .progress-track {{ width: 220px; height: 4px; background: #e2e8f0; border-radius: 2px; overflow: hidden; }}
    .progress-fill  {{ height: 100%; background: #3b82f6; border-radius: 2px;
                      animation: _lsProg 1.2s ease-in-out forwards; }}
    </style>
    <div class="loading-overlay">
        <div class="loading-icon">🛡️</div>
        <div class="loading-sub">{message}</div>
        <div class="progress-track"><div class="progress-fill"></div></div>
    </div>
    """, unsafe_allow_html=True)


st.markdown("""
<style>
    .stApp header [data-testid="stStatusWidget"] { display: none !important; }
    .stApp header button[kind="header"] { display: none !important; }
    /* Hide all Streamlit running/loading indicators globally */
    [data-testid="stSpinner"],
    .stSpinner,
    [data-testid="stDecoration"] { display: none !important; }
    /* Hide skeleton placeholder blocks that appear during reruns */
    [data-testid="stSkeleton"] { visibility: hidden !important; }
</style>
""", unsafe_allow_html=True)

sys.path.insert(0, str(Path(__file__).parent / "utils"))
from session import load_token, clear_token, COOKIE_KEY

# ---------------------------------------------------------------------------
# Cookie manager — blocks until the browser component has initialised and sent
# back the current cookies. st.stop() on the first render causes a brief blank
# screen (~100 ms) before the real page appears; this is unavoidable with any
# component-based cookie approach and is the price of reliable persistence.
# ---------------------------------------------------------------------------
_cookies = CookieManager(prefix="fortify_")

if not _cookies.ready():
    # Blank the viewport while the component handshake completes so neither
    # the login form nor any skeleton placeholder is visible during the wait.
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"],
    [data-testid="stSidebar"] { visibility: hidden !important; }
    </style>
    """, unsafe_allow_html=True)
    st.stop()

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
login_page = st.Page("views/login.py", title="Login", icon=":material/login:")

if not load_token():
    # Option 2 — instant sign-out: a brief white fade as the login form appears,
    # no branded screen and no artificial delay (single rerun from click).
    if st.session_state.pop("_just_logged_out", False):
        st.markdown("""
        <style>
        @keyframes _logoutCov { 0% { opacity:1; } 100% { opacity:0; } }
        ._logoutCov {
            position: fixed; inset: 0; z-index: 99999; background: #ffffff;
            animation: _logoutCov 0.5s ease-out 0.25s both; pointer-events: none;
        }
        </style>
        <div class="_logoutCov"></div>
        """, unsafe_allow_html=True)
    pg = st.navigation([login_page])
    pg.run()

else:
    # Just logged in: render the branded cover AND the home page in the same run.
    # Home renders behind the cover, which fades once it has painted — no extra
    # rerun and no blocking sleep.
    if st.session_state.pop("just_logged_in", False):
        _loading_screen("Signing you in…")

    pages = {
        "Monitoring": [
            st.Page("views/home.py", title="Home", icon=":material/home:", url_path="home"),
            st.Page("views/vm_health_monitor.py", title="VM Health", icon=":material/health_and_safety:"),
        ],
        "Reports": [
            st.Page("views/export_report.py", title="Export Report", icon=":material/download:"),
        ],
        "Optimization": [
            st.Page("views/optimization.py", title="Cost Optimization", icon=":material/trending_down:"),
        ],
        "Security": [
            st.Page("views/security_posture.py", title="Security Posture", icon=":material/security:"),
        ],
        "AI": [
            st.Page("views/ai_insights.py", title="AI Insights", icon=":material/psychology:", url_path="ai_insights"),
        ]
    }
    pg = st.navigation(pages)

    with st.sidebar:
        username = st.session_state.get("username", "admin")
        st.caption(f"Signed in as **{username}**")
        if st.button("Sign out", icon=":material/logout:", use_container_width=True):
            clear_token()
            st.session_state["_just_logged_out"] = True
            st.rerun()

    pg.run()
