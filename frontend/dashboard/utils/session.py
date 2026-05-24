"""
Cookie-backed session management for persistent JWT storage.

Reading uses st.context.cookies (synchronous, built-in Streamlit 1.37+).
Writing/deleting uses streamlit-cookies-controller (reliable browser writes).
"""
import streamlit as st
from streamlit_cookies_controller import CookieController

COOKIE_NAME = "fortify_token"
COOKIE_TTL_DAYS = 1


def _ctrl():
    return CookieController(key="fortify_ctrl")


def save_token(token: str, username: str = ""):
    _ctrl().set(COOKIE_NAME, token, max_age=COOKIE_TTL_DAYS * 86400)
    st.session_state["token"] = token
    if username:
        st.session_state["username"] = username


def load_token() -> str | None:
    if st.session_state.get("token"):
        return st.session_state["token"]
    # st.context.cookies reads HTTP request headers synchronously — no async component needed
    token = st.context.cookies.get(COOKIE_NAME)
    if token:
        st.session_state["token"] = token
    return token


def clear_token():
    _ctrl().remove(COOKIE_NAME)
    st.session_state.pop("token", None)
    st.session_state.pop("username", None)
