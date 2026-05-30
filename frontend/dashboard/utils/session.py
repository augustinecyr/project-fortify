"""
Session management — token lives in st.session_state.
app.py owns the EncryptedCookieManager and hydrates session_state from it on
every page load. session.py only touches session_state and signals app.py via
flags when a cookie write or delete is needed.
"""
import streamlit as st

COOKIE_KEY = "token"          # key inside EncryptedCookieManager (prefix added by app.py)
COOKIE_TTL_DAYS = 1


def save_token(token: str, username: str = ""):
    st.session_state.pop("_logged_out", None)
    st.session_state["_set_token"] = token   # picked up by app.py cookie block
    st.session_state["token"] = token        # immediate use in current session
    if username:
        st.session_state["username"] = username


def load_token() -> str | None:
    if st.session_state.get("_logged_out"):
        return None
    return st.session_state.get("token")     # hydrated from cookie by app.py


def clear_token():
    st.session_state["_logged_out"] = True
    st.session_state["_clear_token"] = True  # picked up by app.py cookie block
    st.session_state.pop("token", None)
    st.session_state.pop("username", None)
