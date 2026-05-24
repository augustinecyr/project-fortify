"""
Project Fortify — Login page.
"""
import os
import sys
import requests
import streamlit as st
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from session import save_token, load_token  # load_token reads session_state (hydrated by app.py)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# If the cookie carries a valid token, skip straight to the dashboard.
if load_token():
    st.switch_page("app.py")

st.markdown("""
<style>
.block-container { padding-top: 4rem !important; max-width: 420px; }
.login-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 0.25rem;
}
.login-sub {
    font-size: 0.825rem;
    color: #64748b;
    margin-bottom: 1.5rem;
}
.error-card {
    background: #fee2e2;
    border-left: 4px solid #dc2626;
    border-radius: 0.5rem;
    padding: 0.75rem 1rem;
    color: #991b1b;
    font-size: 0.825rem;
    margin-top: 0.75rem;
}
[data-testid="InputInstructions"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="login-title">🛡️ Project Fortify</div>', unsafe_allow_html=True)
st.markdown('<div class="login-sub">Sign in to access the infrastructure dashboard.</div>', unsafe_allow_html=True)

with st.form("login_form"):
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Sign in", use_container_width=True)

if submitted:
    if not username or not password:
        st.markdown('<div class="error-card">Please enter both username and password.</div>', unsafe_allow_html=True)
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
                st.markdown('<div class="error-card">Invalid username or password. Please try again.</div>', unsafe_allow_html=True)
        except requests.exceptions.ConnectionError:
            st.markdown('<div class="error-card">Cannot reach the API. Ensure the backend is running.</div>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown(f'<div class="error-card">Unexpected error: {e}</div>', unsafe_allow_html=True)
