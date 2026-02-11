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
        if st.button("Refresh Data", width='stretch'):
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
    # Fetch health data with spinner
    with st.spinner("Loading health data..."):
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
        
        # Export button at the top - simple and clear
        col1, col2 = st.columns([6, 1])
        with col2:
            export_button = st.button("Export Report", width='stretch')
        
        # Health Score Section
        col1, col2, col3 = st.columns([2, 3, 2])
        
        with col1:
            # Health score gauge
            st.markdown("### Health Score")
            
            # Get status info
            css_class, status, color = get_health_status_class(health_score)
            
            # Create and display gauge
            fig_gauge = create_health_gauge(health_score)
            st.plotly_chart(fig_gauge, width='stretch')
            
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
            st.caption(f"Analyzed {metrics_analyzed:,} data points")
        
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
        
        # Time range selector
        time_range = st.selectbox(
            "Time Range:",
            ["Last 1 Hour", "Last 6 Hours", "Last 12 Hours", "Last 24 Hours"],
            index=3
        )
        
        # Map time range to limit
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
            
            # Create time series chart using component
            anomalous_indices = anomaly_details.get("anomalous_indices", [])
            fig_timeseries = create_cpu_timeseries(
                metrics_list,
                mean_cpu,
                anomalous_indices if anomalous_indices and len(anomalous_indices) < len(metrics_list) else None,
                height=400
            )
            st.plotly_chart(fig_timeseries, width='stretch')
            
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
            
            # Handle export when button is clicked
            if export_button:
                # Combine all data into one structured format
                export_data = {
                    "export_info": {
                        "export_timestamp": datetime.now().isoformat(),
                        "vm_id": selected_vm_id,
                        "vm_name": vm_name,
                        "time_range": time_range
                    },
                    "health_summary": {
                        "health_score": health_score,
                        "health_status": status,
                        "anomaly_score": anomaly_score,
                        "stability_score": stability_score,
                        "historical_score": historical_score,
                        "metrics_analyzed": metrics_analyzed
                    },
                    "anomaly_details": {
                        "anomaly_count": anomaly_count,
                        "total_points": total_points,
                        "mean_cpu": mean_cpu,
                        "std_dev": std_dev
                    },
                    "cpu_statistics": {
                        "min_cpu": float(df['cpu_percent'].min()),
                        "max_cpu": float(df['cpu_percent'].max()),
                        "avg_cpu": float(df['cpu_percent'].mean()),
                        "current_cpu": float(df['cpu_percent'].iloc[-1])
                    },
                    "detailed_metrics": metrics_list
                }
                
                # Create CSV content
                import io
                import json
                
                # Create a CSV with summary first, then detailed metrics
                csv_buffer = io.StringIO()
                
                # Write header
                csv_buffer.write("VM Health Report\n")
                csv_buffer.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                csv_buffer.write(f"VM ID: {selected_vm_id}\n")
                csv_buffer.write(f"VM Name: {vm_name}\n")
                csv_buffer.write(f"Time Range: {time_range}\n")
                csv_buffer.write("\n")
                
                # Write health summary section
                csv_buffer.write("HEALTH SUMMARY\n")
                summary_df = pd.DataFrame([
                    ["Health Score", f"{health_score:.1f}"],
                    ["Health Status", status],
                    ["Anomaly Score", f"{anomaly_score:.1f}"],
                    ["Stability Score", f"{stability_score:.1f}"],
                    ["Historical Score", f"{historical_score:.1f}"],
                    ["Metrics Analyzed", f"{metrics_analyzed:,}"]
                ])
                summary_df.to_csv(csv_buffer, header=False, index=False)
                csv_buffer.write("\n")
                
                # Write anomaly details section
                csv_buffer.write("ANOMALY DETAILS\n")
                anomaly_df = pd.DataFrame([
                    ["Anomalies Detected", anomaly_count],
                    ["Total Data Points", total_points],
                    ["Average CPU", f"{mean_cpu:.1f}%"],
                    ["Std Deviation", f"{std_dev:.1f}"]
                ])
                anomaly_df.to_csv(csv_buffer, header=False, index=False)
                csv_buffer.write("\n")
                
                # Write CPU statistics section
                csv_buffer.write("CPU STATISTICS\n")
                stats_df = pd.DataFrame([
                    ["Minimum CPU", f"{df['cpu_percent'].min():.2f}%"],
                    ["Maximum CPU", f"{df['cpu_percent'].max():.2f}%"],
                    ["Average CPU", f"{df['cpu_percent'].mean():.2f}%"],
                    ["Current CPU", f"{df['cpu_percent'].iloc[-1]:.2f}%"]
                ])
                stats_df.to_csv(csv_buffer, header=False, index=False)
                csv_buffer.write("\n")
                
                # Write detailed metrics section
                csv_buffer.write("DETAILED METRICS\n")
                metrics_df = pd.DataFrame(metrics_list)
                metrics_df.to_csv(csv_buffer, index=False)
                
                # Create JSON content as well
                json_buffer = io.StringIO()
                json.dump(export_data, json_buffer, indent=2, default=str)
                
                # Create tabs for different export formats
                st.divider()
                st.markdown("### Export Options")
                
                tab1, tab2 = st.tabs(["CSV Format", "JSON Format"])
                
                with tab1:
                    st.download_button(
                        label="Download CSV Report",
                        data=csv_buffer.getvalue(),
                        file_name=f"{selected_vm_id}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="csv_export"
                    )
                    st.caption("CSV format includes all data in a structured format with sections")
                
                with tab2:
                    st.download_button(
                        label="Download JSON Report",
                        data=json_buffer.getvalue(),
                        file_name=f"{selected_vm_id}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        key="json_export"
                    )
                    st.caption("JSON format includes structured data with nested objects")
        
        else:
            st.warning("No CPU metrics available for the selected time range. Try selecting a longer time period.")
        
    else:
        st.error("Unable to load health data for this VM. Please check if the VM exists and try refreshing.")
else:
    st.info("Please select a VM from the sidebar to view health analysis.")

# Footer
st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")