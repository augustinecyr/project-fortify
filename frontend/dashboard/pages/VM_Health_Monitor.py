"""
VM Health Page - Detailed health score analysis and metrics visualization.
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "components"))

from api_client import FortifyAPIClient
from charts import create_cpu_timeseries, create_component_bars
from helpers import get_health_status_class, export_to_csv
from components.health_widget import render_health_score   # NEW

# Page configuration is already set in app.py – no need to repeat

# Initialize API client
api_client = FortifyAPIClient()

# Custom CSS (only page‑specific additions)
st.markdown("""
    <style>
    /* Hide footer only */
    footer {visibility: hidden;}
    
    /* Keep your existing component-label style if used elsewhere */
    .component-label { font-size: 0.875rem; color: #64748b; margin-bottom: 0.25rem; }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("VM Health Monitor")
st.caption("Real-time health scoring and performance analytics")

# Sidebar - VM Selection (unchanged)
with st.sidebar:
    st.markdown("### VM Selection")
    
    vms_summary = api_client.get_vms_summary()
    
    if vms_summary:
        vms = vms_summary.get("vms", [])
        vm_options = {f"{vm['vm_id']} - {vm['name']}": vm['vm_id'] for vm in vms}
        selected_display = st.selectbox(
            "Select Virtual Machine:",
            list(vm_options.keys()),
            index=0,
            label_visibility="collapsed"
        )
        selected_vm_id = vm_options[selected_display]
        
        st.divider()
        
        if st.button("Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        auto_refresh = st.checkbox("Auto-refresh (5 min)", value=False)
        if auto_refresh:
            st.caption("Auto-refresh enabled")
    else:
        st.error("Unable to load VMs")
        selected_vm_id = None

# Main content
if selected_vm_id:
    # Fetch health data
    with st.spinner("Loading health data..."):   # Will keep spinner; we didn't change this
        health_data = api_client.get_health_score(selected_vm_id)
    
    if health_data:
        vm_name = health_data.get("vm_name", "Unknown")
        health_score = health_data.get("health_score", 0)
        components = health_data.get("components", {})
        anomaly_details = health_data.get("anomaly_details", {})
        metrics_analyzed = health_data.get("metrics_analyzed", 0)
        
        st.markdown(f"### {selected_vm_id} - {vm_name}")
        
        # ---- MODERN HEALTH WIDGET ----
        # Convert component scores (0-1) to 0-100
        component_scores_100 = {
            "anomaly_score": components.get("anomaly_score", 0) * 100,
            "stability_score": components.get("stability_score", 0) * 100,
            "historical_score": components.get("historical_score", 0) * 100,
        }
        
        # Get status text & class (reuse your helper)
        css_class, status, color = get_health_status_class(health_score)
        
        # Two‑column layout: Health Score Card | Anomaly Details
        col_left, col_right = st.columns([1.2, 1])
        
        with col_left:
            render_health_score(health_score, status, component_scores_100)
        
        with col_right:
            st.markdown("### Anomaly Details")
            anomaly_count = anomaly_details.get("anomaly_count", 0)
            total_points = anomaly_details.get("total_points", 1)
            mean_cpu = anomaly_details.get("mean", 0)
            std_dev = anomaly_details.get("std_dev", 0)
            
            st.metric("Anomalies Detected", anomaly_count)
            st.metric("Total Data Points", f"{total_points:,}")
            st.metric("Average CPU", f"{mean_cpu:.1f}%")
            st.metric("Std Deviation", f"{std_dev:.1f}")
            
            st.divider()
            st.caption(f"📈 Analyzed {metrics_analyzed:,} data points")
        
        st.divider()
        
        # ---- CPU METRICS SECTION ----
        st.markdown("## CPU Metrics Analysis")
        
        # Time range selector
        time_range = st.selectbox(
            "Time Range:",
            ["Last 1 Hour", "Last 6 Hours", "Last 12 Hours", "Last 24 Hours"],
            index=3
        )
        
        time_range_map = {
            "Last 1 Hour": 60,
            "Last 6 Hours": 360,
            "Last 12 Hours": 720,
            "Last 24 Hours": 1440
        }
        limit = time_range_map.get(time_range, 1440)
        
        with st.spinner("Loading CPU metrics..."):
            metrics_data = api_client.get_cpu_metrics(selected_vm_id, limit=limit)
        
        if metrics_data and metrics_data.get("metrics"):
            metrics_list = metrics_data["metrics"]
            
            # Build time series chart
            anomalous_indices = anomaly_details.get("anomalous_indices", [])
            fig_timeseries = create_cpu_timeseries(
                metrics_list,
                mean_cpu,
                anomalous_indices if anomalous_indices and len(anomalous_indices) < len(metrics_list) else None,
                height=400
            )
            st.plotly_chart(fig_timeseries, use_container_width=True)
            
            # Statistics row
            df = pd.DataFrame(metrics_list)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Min CPU", f"{df['cpu_percent'].min():.2f}%")
            with col2:
                st.metric("Max CPU", f"{df['cpu_percent'].max():.2f}%")
            with col3:
                st.metric("Avg CPU", f"{df['cpu_percent'].mean():.2f}%")
            with col4:
                st.metric("Current CPU", f"{df['cpu_percent'].iloc[-1]:.2f}%")
            
            # ---- EXPORT SECTION (to be overhauled in Day 4) ----
            # For now, keep a simple download button – we'll replace this soon
            csv_data = export_to_csv(metrics_list, f"{selected_vm_id}_metrics.csv")
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name=f"{selected_vm_id}_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("⚠️ No CPU metrics available for the selected time range.")
    else:
        st.error("❌ Unable to load health data for this VM.")
else:
    st.info("👈 Please select a VM from the sidebar to view health analysis.")

# Footer
st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")