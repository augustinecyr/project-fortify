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
from charts import create_health_gauge, create_cpu_timeseries, create_component_bars
from helpers import get_health_status_class, export_to_csv

# Page configuration
st.set_page_config(
    page_title="VM Health Monitor - Project Fortify",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Project Fortify - Infrastructure Health Monitoring Platform v0.1.0"
    }
)

# Initialize API client
api_client = FortifyAPIClient()

# Custom CSS
st.markdown("""
    <style>
    /* Hide footer only */
    footer {visibility: hidden;}
    
    .health-score-excellent { color: #059669; font-weight: 600; }
    .health-score-good { color: #10b981; font-weight: 600; }
    .health-score-warning { color: #f59e0b; font-weight: 600; }
    .health-score-critical { color: #dc2626; font-weight: 600; }
    .component-label { font-size: 0.875rem; color: #64748b; margin-bottom: 0.25rem; }
    
    h1 {
        color: #1e293b;
        font-weight: 600;
        font-size: 2rem;
    }
    
    h2 {
        color: #1e293b;
        font-weight: 600;
        font-size: 1.5rem;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.5rem;
        margin-top: 1.5rem;
    }
    
    h3 {
        color: #334155;
        font-weight: 600;
        font-size: 1.25rem;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("VM Health Monitor")
st.caption("Real-time health scoring and performance analytics")

# Sidebar - VM Selection
with st.sidebar:
    st.markdown("### VM Selection")
    
    # Get VMs from summary (faster, cached)
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
        
        # Refresh button
        if st.button("Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh (5 min)", value=False)
        
        if auto_refresh:
            st.caption("Auto-refresh enabled")
    else:
        st.error("Unable to load VMs")
        selected_vm_id = None

# Main content
if selected_vm_id:
    # Fetch health data
    health_data = api_client.get_health_score(selected_vm_id)
    
    if health_data:
        # Extract data
        vm_name = health_data.get("vm_name", "Unknown")
        health_score = health_data.get("health_score", 0)
        components = health_data.get("components", {})
        anomaly_details = health_data.get("anomaly_details", {})
        metrics_analyzed = health_data.get("metrics_analyzed", 0)
        
        # Display VM info
        st.markdown(f"### {selected_vm_id} - {vm_name}")
        
        # Health Score Section
        col1, col2, col3 = st.columns([2, 3, 2])
        
        with col1:
            # Health score gauge
            st.markdown("### Health Score")
            
            # Get status info
            css_class, status, color = get_health_status_class(health_score)
            
            # Create and display gauge
            fig_gauge = create_health_gauge(health_score)
            st.plotly_chart(fig_gauge, use_container_width=True)
            
            st.markdown(f"<p class='{css_class}' style='text-align: center; font-size: 1.2rem;'>{status}</p>", unsafe_allow_html=True)
        
        with col2:
            # Score components breakdown
            st.markdown("### Score Components")
            
            anomaly_score = components.get("anomaly_score", 0) * 100
            stability_score = components.get("stability_score", 0) * 100
            historical_score = components.get("historical_score", 0) * 100
            
            # Anomaly component
            st.markdown('<p class="component-label">Anomaly Score (40% weight)</p>', unsafe_allow_html=True)
            st.progress(anomaly_score / 100)
            st.caption(f"{anomaly_score:.1f}/100")
            
            # Stability component
            st.markdown('<p class="component-label">Stability Score (30% weight)</p>', unsafe_allow_html=True)
            st.progress(stability_score / 100)
            st.caption(f"{stability_score:.1f}/100")
            
            # Historical component
            st.markdown('<p class="component-label">Historical Score (30% weight)</p>', unsafe_allow_html=True)
            st.progress(historical_score / 100)
            st.caption(f"{historical_score:.1f}/100")
            
            st.divider()
            st.caption(f"📈 Analyzed {metrics_analyzed:,} data points")
        
        with col3:
            # Anomaly details
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
        
        # CPU Metrics Time Series
        st.markdown("## CPU Metrics Analysis")
        
        # Time range selector and export button
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            time_range = st.selectbox(
                "Time Range:",
                ["Last 1 Hour", "Last 6 Hours", "Last 12 Hours", "Last 24 Hours"],
                index=3
            )
        with col2:
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Export CSV", use_container_width=True):
                st.info("Export functionality coming soon")
        with col3:
            pass  # Empty column for spacing
        
        # Map time range to limit
        time_range_map = {
            "Last 1 Hour": 60,
            "Last 6 Hours": 360,
            "Last 12 Hours": 720,
            "Last 24 Hours": 1440
        }
        limit = time_range_map.get(time_range, 1440)
        
        metrics_data = api_client.get_cpu_metrics(selected_vm_id, limit=limit)
        
        if metrics_data and metrics_data.get("metrics"):
            metrics_list = metrics_data["metrics"]
            
            # Create time series chart using component
            anomalous_indices = anomaly_details.get("anomalous_indices", [])
            fig_timeseries = create_cpu_timeseries(
                metrics_list,
                mean_cpu,
                anomalous_indices if anomalous_indices and len(anomalous_indices) < len(metrics_list) else None,
                height=400
            )
            st.plotly_chart(fig_timeseries, use_container_width=True)
            
            # Export data preparation
            if st.session_state.get('export_csv', False):
                csv_data = export_to_csv(metrics_list, f"{selected_vm_id}_metrics.csv")
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name=f"{selected_vm_id}_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            # Create DataFrame for statistics
            df = pd.DataFrame(metrics_list)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Min CPU", f"{df['cpu_percent'].min():.2f}%")
            with col2:
                st.metric("Max CPU", f"{df['cpu_percent'].max():.2f}%")
            with col3:
                st.metric("Avg CPU", f"{df['cpu_percent'].mean():.2f}%")
            with col4:
                st.metric("Current CPU", f"{df['cpu_percent'].iloc[-1]:.2f}%")
        else:
            st.warning("No CPU metrics available for this VM")
        
    else:
        st.error("Unable to load health data for this VM")
else:
    st.info("Please select a VM from the sidebar")

# Footer
st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")