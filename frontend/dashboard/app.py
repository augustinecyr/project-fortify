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

# In app.py, after st.set_page_config
st.markdown("""
<style>
    /* Hide the entire running status container */
    .stApp header [data-testid="stStatusWidget"] {
        display: none !important;
    }
    
    /* Alternative: Hide only the stop button */
    .stApp header button[kind="header"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

sys.path.insert(0, str(Path(__file__).parent / "utils"))

# Pages with Material Icons
pages = {
    "Monitoring": [
        st.Page("pages/home.py", title="Home", icon=":material/home:"),
        st.Page("pages/vm_health_monitor.py", title="VM Health", icon=":material/health_and_safety:"),
    ],
    "Reports": [
        st.Page("pages/export_report.py", title="Export Report", icon=":material/download:"),
        # Future: st.Page("pages/scheduled_reports.py", title="Scheduled Reports", icon=":material/schedule:"),
    ],
    "Optimization": [
        st.Page("pages/optimization.py", title="Cost Optimization", icon=":material/trending_down:"),
    ],
    "Security": [
        st.Page("pages/security_analytics.py", title="Security Analytics", icon=":material/security:"),  # if placed in root, else "pages/security.py"
    ]
}

pg = st.navigation(pages)
pg.run()