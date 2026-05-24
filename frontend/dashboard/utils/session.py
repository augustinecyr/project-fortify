"""
Cookie-backed session management for persistent JWT storage.
"""
import extra_streamlit_components as stx
import streamlit as st

COOKIE_NAME = "fortify_token"
COOKIE_TTL_DAYS = 1


def get_cookie_manager():
    return stx.CookieManager(key="fortify_cookie_mgr")


def save_token(token: str, username: str = ""):
    cm = get_cookie_manager()
    cm.set(COOKIE_NAME, token, max_age=COOKIE_TTL_DAYS * 86400)
    st.session_state["token"] = token
    if username:
        st.session_state["username"] = username


def load_token() -> str | None:
    if st.session_state.get("token"):
        return st.session_state["token"]
    cm = get_cookie_manager()
    token = cm.get(COOKIE_NAME)
    if token:
        st.session_state["token"] = token
    return token


def clear_token():
    cm = get_cookie_manager()
    cm.delete(COOKIE_NAME)
    st.session_state.pop("token", None)
    st.session_state.pop("username", None)
