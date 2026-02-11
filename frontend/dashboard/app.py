"""
Project Fortify - Main Entry Point
Navigation hub for the dashboard.
"""
import streamlit as st
import sys
from pathlib import Path

st.set_page_config(
    page_title="Project Fortify Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Project Fortify - Infrastructure Health Monitoring Platform v0.1.0"
    }
)

sys.path.insert(0, str(Path(__file__).parent / "utils"))

# Pages with Material Icons
pages = {
    "Monitoring": [
        st.Page("pages/home.py", title="Home", icon=":material/home:"),
        st.Page("pages/vm_health_monitor.py", title="VM Health", icon=":material/health_and_safety:"),
    ],
    "Reports": [
        # Future pages (e.g., :material/description:, :material/bar_chart:)
    ]
}

pg = st.navigation(pages)
pg.run()