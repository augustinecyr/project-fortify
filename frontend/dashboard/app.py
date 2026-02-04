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
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .status-healthy {
        color: #28a745;
    }
    .status-warning {
        color: #ffc107;
    }
    .status-critical {
        color: #dc3545;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize API client
api_client = FortifyAPIClient()

# Header
st.markdown('<p class="main-header">🛡️ Project Fortify Dashboard</p>', unsafe_allow_html=True)
st.markdown("AI-assisted infrastructure monitoring and health scoring")

# Sidebar
with st.sidebar:
    st.header("Navigation")
    st.markdown("Use the pages above to navigate:")
    st.markdown("- **Home** - System overview")
    st.markdown("- **VM Health** - Detailed health analysis")
    
    st.divider()
    
    # System status
    st.subheader("System Status")
    status = api_client.get_system_status()
    
    if status:
        if status.get("database") == "connected":
            st.success("✅ Database: Connected")
        else:
            st.error("❌ Database: Disconnected")
        
        st.info(f"📦 API Version: {status.get('version', 'Unknown')}")
    else:
        st.error("❌ API: Unavailable")

# Main content
st.header("📊 System Overview")

# Get all VMs
vms = api_client.get_all_vms()

if vms:
    # Summary metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total VMs",
            value=len(vms),
            delta=None
        )
    
    with col2:
        # Calculate average health (sample from first 5 VMs for performance)
        sample_scores = []
        for vm in vms[:5]:
            health_data = api_client.get_health_score(vm["vm_id"])
            if health_data:
                sample_scores.append(health_data.get("health_score", 0))
        
        avg_health = sum(sample_scores) / len(sample_scores) if sample_scores else 0
        
        st.metric(
            label="Avg Health Score",
            value=f"{avg_health:.0f}/100",
            delta=None
        )
    
    with col3:
        # Count critical VMs (score < 50)
        critical_count = sum(1 for score in sample_scores if score < 50)
        
        st.metric(
            label="Critical Alerts",
            value=critical_count,
            delta=None,
            delta_color="inverse"
        )
    
    with col4:
        st.metric(
            label="Monitored Metrics",
            value="201K+",
            delta=None
        )
    
    st.divider()
    
    # VM Quick Selector
    st.subheader("🔍 Quick VM Lookup")
    
    vm_names = [f"{vm['vm_id']} - {vm['name']}" for vm in vms]
    selected_vm_display = st.selectbox(
        "Select a VM to view details:",
        vm_names,
        index=0
    )
    
    # Extract vm_id from selection
    selected_vm_id = selected_vm_display.split(" - ")[0]
    
    if st.button("View Health Details", type="primary"):
        st.info(f"Navigate to **VM Health** page in the sidebar and select {selected_vm_id}")
    
    st.divider()
    
    # Recent Activity / VM List
    st.subheader("📋 Virtual Machines")
    
    # Display VMs in a grid
    cols_per_row = 4
    for i in range(0, len(vms), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            if i + j < len(vms):
                vm = vms[i + j]
                with col:
                    st.markdown(f"**{vm['vm_id']}**")
                    st.caption(vm['name'])
    
else:
    st.warning("⚠️ Unable to load VM data. Please check API connection.")

# Footer
st.divider()
st.caption("Project Fortify - AI-Assisted Infrastructure Monitoring | Version 0.1.0")