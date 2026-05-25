"""
Project Fortify — Login page.
"""
import os
import sys
import requests
import streamlit as st
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from session import save_token, load_token

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

if load_token():
    st.switch_page("app.py")
    st.stop()

st.markdown("""
<style>
/* ── Viewport lock ── */
html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"], section.main {
    height: 100vh !important;
    max-height: 100vh !important;
    overflow: hidden !important;
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
}
header, [data-testid="stSidebar"],
[data-testid="stDecoration"] { display: none !important; }

/* ── Push block-container into the right half, vertically centred ── */
.block-container {
    padding: calc(50vh - 155px) 5vw 0 calc(50vw + 5vw) !important;
    margin: 0 !important;
    max-width: 100vw !important;
    height: 100vh !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
}

/* ── Kill any horizontal-block gaps (inner layout columns) ── */
[data-testid="stHorizontalBlock"] {
    height: auto !important;
    gap: 0 !important;
}
[data-testid="column"] { padding: 0 !important; }

[data-testid="InputInstructions"] { display: none !important; }
</style>

<!-- Fixed left panel — outside Streamlit's layout engine -->
<div style="
    position: fixed; top: 0; left: 0;
    width: 50%; height: 100vh;
    background: #f1f5f9;
    display: flex; align-items: center; justify-content: center;
    z-index: 0;
">
    <div style="text-align:center; color:#cbd5e1; user-select:none;">
        <div style="font-size:2.5rem; margin-bottom:0.5rem;">🖼️</div>
        <div style="font-size:0.7rem; letter-spacing:0.12em; text-transform:uppercase;">
            Wallpaper placeholder
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Error slot — always rendered at fixed height so the form never shifts ────
_error = st.session_state.pop("_login_error", "")
if _error:
    st.markdown(
        f'<div style="background:#fee2e2;border-left:4px solid #dc2626;border-radius:.5rem;'
        f'padding:.75rem 1rem;color:#991b1b;font-size:.825rem;margin-bottom:.75rem;">'
        f'{_error}</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown("<div style='height:3.5rem;'></div>", unsafe_allow_html=True)

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
username = st.text_input("Username", key="login_username")
password = st.text_input("Password", type="password", key="login_password")
st.markdown("<div style='height:0.15rem;'></div>", unsafe_allow_html=True)
sign_in  = st.button("Sign in", use_container_width=True, type="primary")

# ── Auth logic ────────────────────────────────────────────────────────────────
if sign_in:
    if not username or not password:
        st.session_state["_login_error"] = "Please enter both username and password."
        st.rerun()
    else:
        try:
            r = requests.post(
                f"{API_BASE_URL}/auth/token",
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=5,
            )
            if r.status_code == 200:
                save_token(r.json()["access_token"], username)
                st.session_state["just_logged_in"] = True
                st.rerun()
            else:
                st.session_state["_login_error"] = "Invalid username or password."
                st.rerun()
        except requests.exceptions.ConnectionError:
            st.session_state["_login_error"] = "Cannot reach the API. Ensure the backend is running."
            st.rerun()
        except Exception as e:
            st.session_state["_login_error"] = f"Unexpected error: {e}"
            st.rerun()
