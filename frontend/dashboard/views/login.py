"""
Project Fortify — Login page.
"""
import base64
import os
import sys
import requests
import streamlit as st
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from session import save_token, load_token

_WALLPAPER = Path(__file__).resolve().parents[1] / "assets" / "login-wallpaper.jpg"
_wallpaper_css = (
    f"url('data:image/jpeg;base64,{base64.b64encode(_WALLPAPER.read_bytes()).decode()}')"
    if _WALLPAPER.exists()
    else "linear-gradient(160deg, #0f172a 0%, #1e3a5f 55%, #1e40af 100%)"
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

if load_token():
    st.switch_page("app.py")
    st.stop()

st.markdown(f"""
<style>
/* ── Viewport lock ── */
html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"], section.main {{
    height: 100vh !important;
    max-height: 100vh !important;
    overflow: hidden !important;
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
}}
header, [data-testid="stSidebar"],
[data-testid="stDecoration"] {{ display: none !important; }}

/* ── Push block-container into the right half, vertically centred ── */
.block-container {{
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    /* small top nudge offsets the empty error slot at the top of the column
       so the visible form sits at the optical centre, not slightly high */
    padding: 5vh 5vw 0 calc(50vw + 5vw) !important;
    margin: 0 !important;
    max-width: 100vw !important;
    height: 100vh !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
}}

/* ── Kill any horizontal-block gaps (inner layout columns) ── */
[data-testid="stHorizontalBlock"] {{
    height: auto !important;
    gap: 0 !important;
}}
[data-testid="column"] {{ padding: 0 !important; }}

[data-testid="InputInstructions"] {{ display: none !important; }}

/* ── Spinner positioning ── */
[data-testid="stSpinner"] {{
    padding: 0.5rem 0 !important;
    font-size: 0.8rem !important;
    color: #64748b !important;
}}
</style>

<!-- Fixed left panel — outside Streamlit's layout engine -->
<div style="
    position: fixed; top: 0; left: 0;
    width: 50%; height: 100vh;
    background: {_wallpaper_css} center/cover no-repeat;
    display: flex; align-items: center; justify-content: center;
    z-index: 0;
">
</div>
""", unsafe_allow_html=True)

# ── Processing cover ──────────────────────────────────────────────────────────
# While the auth POST below blocks, the filled login form would otherwise stay
# visible. Cover it with the same branded screen app.py shows post-login, so the
# click → home transition reads as one continuous loading state.
if st.session_state.get("_logging_in"):
    st.markdown("""
    <style>
    @keyframes _liProg { from { width: 0%; } to { width: 100%; } }
    ._liCover {
        position: fixed; inset: 0; z-index: 99999; background: white;
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; gap: 0.6rem;
    }
    </style>
    <div class="_liCover">
        <div style="font-size:2.5rem; margin-bottom:0.75rem;">🛡️</div>
        <div style="font-size:0.875rem; color:#64748b; margin:0 0 0.75rem 0;">Signing you in…</div>
        <div style="width:220px; height:4px; background:#e2e8f0; border-radius:2px; overflow:hidden;">
            <div style="height:100%; background:#3b82f6; border-radius:2px;
                        animation:_liProg 1.2s ease-in-out forwards;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Error slot — fixed-height wrapper so the form never shifts ────────────────
_error = st.session_state.pop("_login_error", "")
_error_inner = (
    f'<div style="background:#fee2e2;border-left:4px solid #dc2626;'
    f'border-radius:.5rem;padding:.6rem 1rem;color:#991b1b;font-size:.8rem;">'
    f'{_error}</div>'
) if _error else ""
st.markdown(
    f'<div style="min-height:3rem;margin-bottom:0.5rem;box-sizing:border-box;">{_error_inner}</div>',
    unsafe_allow_html=True,
)

# ── Brand ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:1.75rem;">
    <div style="font-size:1.35rem; font-weight:700; color:#0f172a; margin-bottom:0.3rem;">
        🛡️ Project Fortify
    </div>
    <div style="font-size:0.825rem; color:#64748b;">
        Sign in to access the dashboard.
    </div>
</div>
""", unsafe_allow_html=True)

# ── Inputs ────────────────────────────────────────────────────────────────────
_logging_in = st.session_state.get("_logging_in", False)

username = st.text_input("Username", key="login_username", disabled=_logging_in)
password = st.text_input("Password", type="password", key="login_password", disabled=_logging_in)
st.markdown("<div style='height:0.15rem;'></div>", unsafe_allow_html=True)
sign_in = st.button(
    "Signing in…" if _logging_in else "Sign in",
    use_container_width=True,
    type="primary",
    disabled=_logging_in,
)

# ── Auth logic ────────────────────────────────────────────────────────────────
if sign_in and not _logging_in:
    if not username or not password:
        st.session_state["_login_error"] = "Please enter both username and password."
        st.rerun()
    else:
        st.session_state["_logging_in"] = True
        st.rerun()

if _logging_in:
    _u = st.session_state.get("login_username", "")
    _p = st.session_state.get("login_password", "")
    with st.spinner("Signing in…"):
        try:
            r = requests.post(
                f"{API_BASE_URL}/auth/token",
                data={"username": _u, "password": _p},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=5,
            )
            if r.status_code == 200:
                save_token(r.json()["access_token"], _u)
                st.session_state["just_logged_in"] = True
                st.session_state.pop("_logging_in", None)
                st.rerun()
            else:
                st.session_state["_login_error"] = "Invalid username or password."
                st.session_state.pop("_logging_in", None)
                st.rerun()
        except requests.exceptions.ConnectionError:
            st.session_state["_login_error"] = "Cannot reach the API. Ensure the backend is running."
            st.session_state.pop("_logging_in", None)
            st.rerun()
        except Exception as e:
            st.session_state["_login_error"] = f"Unexpected error: {e}"
            st.session_state.pop("_logging_in", None)
            st.rerun()
