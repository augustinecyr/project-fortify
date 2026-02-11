"""
Project Fortify - Home Dashboard
System overview and VM summary table.
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd

# Add utils to path (needed for API client)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))

from api_client import FortifyAPIClient

# Initialize API client
api_client = FortifyAPIClient()

# Custom CSS for home page
st.markdown("""
    <style>
    .main-header {
        font-size: 2rem;
        font-weight: 600;
        color: #1e3a8a;
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
    }
    .main-subheader {
        font-size: 1rem;
        color: #64748b;
        margin-bottom: 2rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 600;
    }
    h2 {
        color: #1e293b;
        font-weight: 600;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.5rem;
        margin-top: 1.5rem;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">Project Fortify</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subheader">Infrastructure Health Monitoring & Analytics Platform</p>', unsafe_allow_html=True)

# Main content
st.markdown("## System Overview")

# Get VMs summary
with st.spinner("Loading system data..."):
    vms_summary = api_client.get_vms_summary()

if vms_summary:
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total VMs", vms_summary.get("total", 0))
    with col2:
        st.metric("Online VMs", vms_summary.get("online", 0))
    with col3:
        st.metric("Offline VMs", vms_summary.get("offline", 0), delta_color="inverse")
    with col4:
        vms_list = vms_summary.get("vms", [])
        online_vms = [vm for vm in vms_list if vm.get("avg_cpu_24h") is not None]
        avg_cpu = sum(vm["avg_cpu_24h"] for vm in online_vms) / len(online_vms) if online_vms else 0
        st.metric("Avg CPU (24h)", f"{avg_cpu:.1f}%")
    
    st.divider()
    
    # VM Table
    st.markdown("## Virtual Machines")
    df_vms = pd.DataFrame(vms_list)
    display_columns = {
        "vm_id": "VM ID",
        "name": "Name",
        "status": "Status",
        "current_cpu": "Current CPU (%)",
        "avg_cpu_24h": "Avg CPU 24h (%)",
        "metric_count_24h": "Metrics (24h)"
    }
    df_display = df_vms[list(display_columns.keys())].copy()
    df_display.columns = list(display_columns.values())
    df_display["Current CPU (%)"] = df_display["Current CPU (%)"].apply(
        lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
    )
    df_display["Avg CPU 24h (%)"] = df_display["Avg CPU 24h (%)"].apply(
        lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
    )
    st.dataframe(df_display, width='stretch', hide_index=True)
    st.caption(f"Displaying {len(vms_list)} virtual machines | Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.warning("⚠️ Unable to load VM data. Please check API connection.")

st.divider()
st.caption("Project Fortify - AI-Assisted Infrastructure Monitoring | Version 0.1.0")