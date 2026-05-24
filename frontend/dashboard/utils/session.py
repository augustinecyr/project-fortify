"""
Cookie-backed session management for persistent JWT storage.

CookieController is intentionally NOT instantiated here — it must live at the
top of app.py so it survives the st.rerun() that login triggers. session.py
only writes flags to session_state; app.py acts on them each render.
"""
import streamlit as st

COOKIE_NAME = "fortify_token"
COOKIE_TTL_DAYS = 1


def save_token(token: str, username: str = ""):
    st.session_state.pop("_logged_out", None)
    st.session_state["_pending_cookie"] = token
    st.session_state["token"] = token
    if username:
        st.session_state["username"] = username


def load_token() -> str | None:
    # Explicit logout guard — prevents re-reading a cookie that is mid-deletion.
    if st.session_state.get("_logged_out"):
        return None
    if st.session_state.get("token"):
        return st.session_state["token"]
    # st.context.cookies reads the HTTP request headers synchronously — no component needed.
    token = st.context.cookies.get(COOKIE_NAME)
    if token:
        st.session_state["token"] = token
    return token


def clear_token():
    st.session_state["_logged_out"] = True
    st.session_state["_pending_clear"] = True
    st.session_state.pop("token", None)
    st.session_state.pop("username", None)
