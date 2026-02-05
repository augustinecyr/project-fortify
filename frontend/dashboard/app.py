"""
Project Fortify - Main Dashboard
Interactive dashboard for VM health monitoring and analysis.
"""
import streamlit as st
import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / "utils"))

from api_client import FortifyAPIClient

# Page configuration
st.set_page_config(
    page_title="Project Fortify Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Project Fortify - Infrastructure Health Monitoring Platform v0.1.0"
    }
)

# Custom CSS
st.markdown("""
    <style>
    /* Hide footer only */
    footer {visibility: hidden;}
    
    /* Main header styling */
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
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 600;
    }
    
    /* Section headers */
    h2 {
        color: #1e293b;
        font-weight: 600;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.5rem;
        margin-top: 1.5rem;
    }
    
    /* Responsive table */
    [data-testid="stDataFrame"] {
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize API client
api_client = FortifyAPIClient()

# Header
st.markdown('<p class="main-header">Project Fortify</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subheader">Infrastructure Health Monitoring & Analytics Platform</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### Navigation")
    st.caption("Select a page from the sidebar menu above")
    
    st.divider()
    
    # System status
    st.markdown("### System Health")
    status = api_client.get_system_status()
    
    if status:
        if status.get("database") == "connected":
            st.success("Database Online")
        else:
            st.error("Database Offline")
        
        st.caption(f"API Version {status.get('version', 'Unknown')}")
    else:
        st.error("API Unavailable")

# Main content
st.markdown("## System Overview")

# Get VMs summary (single API call)
vms_summary = api_client.get_vms_summary()

if vms_summary:
    # Summary metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total VMs",
            value=vms_summary.get("total", 0),
            delta=None
        )
    
    with col2:
        st.metric(
            label="Online VMs",
            value=vms_summary.get("online", 0),
            delta=None
        )
    
    with col3:
        st.metric(
            label="Offline VMs",
            value=vms_summary.get("offline", 0),
            delta=None,
            delta_color="inverse"
        )
    
    with col4:
        # Calculate average CPU from summary
        vms_list = vms_summary.get("vms", [])
        online_vms = [vm for vm in vms_list if vm.get("avg_cpu_24h") is not None]
        avg_cpu = sum(vm["avg_cpu_24h"] for vm in online_vms) / len(online_vms) if online_vms else 0
        
        st.metric(
            label="Avg CPU (24h)",
            value=f"{avg_cpu:.1f}%",
            delta=None
        )
    
    st.divider()
    
    # VM Table View
    st.markdown("## Virtual Machines")
    
    # Create DataFrame for better display
    import pandas as pd
    
    df_vms = pd.DataFrame(vms_list)
    
    # Reorder and select columns for display
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
    
    # Format the dataframe
    df_display["Current CPU (%)"] = df_display["Current CPU (%)"].apply(
        lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
    )
    df_display["Avg CPU 24h (%)"] = df_display["Avg CPU 24h (%)"].apply(
        lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
    )
    
    # Display interactive table
    st.dataframe(
        df_display,
        width='stretch',
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn(
                "Status",
                help="VM online/offline status",
            ),
            "VM ID": st.column_config.TextColumn(
                "VM ID",
                help="Virtual Machine Identifier",
            )
        }
    )
    
    st.caption(f"Displaying {len(vms_list)} virtual machines | Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
else:
    st.warning("⚠️ Unable to load VM data. Please check API connection.")

# Footer
st.divider()
st.caption("Project Fortify - AI-Assisted Infrastructure Monitoring | Version 0.1.0")