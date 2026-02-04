"""
VM Health Page - Detailed health score analysis and metrics visualization.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Add utils to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from api_client import FortifyAPIClient

# Page configuration
st.set_page_config(
    page_title="VM Health - Project Fortify",
    page_icon="🏥",
    layout="wide"
)

# Initialize API client
api_client = FortifyAPIClient()

# Custom CSS
st.markdown("""
    <style>
    .health-score-excellent { color: #28a745; font-weight: bold; }
    .health-score-good { color: #5cb85c; font-weight: bold; }
    .health-score-warning { color: #ffc107; font-weight: bold; }
    .health-score-critical { color: #dc3545; font-weight: bold; }
    .component-label { font-size: 0.9rem; color: #666; }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("🏥 VM Health Analysis")
st.markdown("Detailed health scoring and performance metrics")

# Sidebar - VM Selection
with st.sidebar:
    st.header("VM Selection")
    
    # Get all VMs
    vms = api_client.get_all_vms()
    
    if vms:
        vm_options = {f"{vm['vm_id']} - {vm['name']}": vm['vm_id'] for vm in vms}
        selected_display = st.selectbox(
            "Select Virtual Machine:",
            list(vm_options.keys()),
            index=0
        )
        selected_vm_id = vm_options[selected_display]
        
        st.divider()
        
        # Refresh button
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh (5 min)")
        
        if auto_refresh:
            st.info("⏱️ Auto-refresh enabled")
    else:
        st.error("❌ Unable to load VMs")
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
        st.subheader(f"📊 {selected_vm_id} - {vm_name}")
        
        # Health Score Section
        col1, col2, col3 = st.columns([2, 3, 2])
        
        with col1:
            # Health score gauge
            st.markdown("### Health Score")
            
            # Determine color and status
            if health_score >= 80:
                color = "#28a745"
                status = "Excellent"
                status_class = "health-score-excellent"
            elif health_score >= 65:
                color = "#5cb85c"
                status = "Good"
                status_class = "health-score-good"
            elif health_score >= 50:
                color = "#ffc107"
                status = "Warning"
                status_class = "health-score-warning"
            else:
                color = "#dc3545"
                status = "Critical"
                status_class = "health-score-critical"
            
            # Create gauge chart
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=health_score,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': status, 'font': {'size': 20}},
                gauge={
                    'axis': {'range': [None, 100], 'tickwidth': 1},
                    'bar': {'color': color},
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'steps': [
                        {'range': [0, 50], 'color': '#ffebee'},
                        {'range': [50, 65], 'color': '#fff9c4'},
                        {'range': [65, 80], 'color': '#e8f5e9'},
                        {'range': [80, 100], 'color': '#c8e6c9'}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 50
                    }
                }
            ))
            
            fig_gauge.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            
            st.plotly_chart(fig_gauge, use_container_width=True)
            
            st.markdown(f"<p class='{status_class}' style='text-align: center; font-size: 1.2rem;'>{status}</p>", unsafe_allow_html=True)
        
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
        st.markdown("### 📉 CPU Metrics (Last 24 Hours)")
        
        metrics_data = api_client.get_cpu_metrics(selected_vm_id, limit=1440)
        
        if metrics_data and metrics_data.get("metrics"):
            metrics_list = metrics_data["metrics"]
            
            # Create DataFrame
            df = pd.DataFrame(metrics_list)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Create time series chart
            fig_timeseries = go.Figure()
            
            # Add CPU line
            fig_timeseries.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['cpu_percent'],
                mode='lines',
                name='CPU Usage',
                line=dict(color='#1f77b4', width=2),
                hovertemplate='<b>Time</b>: %{x}<br><b>CPU</b>: %{y:.2f}%<extra></extra>'
            ))
            
            # Add mean line
            fig_timeseries.add_hline(
                y=mean_cpu,
                line_dash="dash",
                line_color="green",
                annotation_text=f"Mean: {mean_cpu:.1f}%",
                annotation_position="right"
            )
            
            # Highlight anomalies if present
            anomalous_indices = anomaly_details.get("anomalous_indices", [])
            if anomalous_indices and len(anomalous_indices) < len(df):
                anomaly_df = df.iloc[anomalous_indices]
                fig_timeseries.add_trace(go.Scatter(
                    x=anomaly_df['timestamp'],
                    y=anomaly_df['cpu_percent'],
                    mode='markers',
                    name='Anomalies',
                    marker=dict(color='red', size=8, symbol='x'),
                    hovertemplate='<b>Anomaly</b><br><b>Time</b>: %{x}<br><b>CPU</b>: %{y:.2f}%<extra></extra>'
                ))
            
            fig_timeseries.update_layout(
                title="CPU Utilization Over Time",
                xaxis_title="Time",
                yaxis_title="CPU Usage (%)",
                hovermode='x unified',
                height=400,
                showlegend=True
            )
            
            st.plotly_chart(fig_timeseries, use_container_width=True)
            
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
            st.warning("⚠️ No CPU metrics available for this VM")
        
    else:
        st.error("❌ Unable to load health data for this VM")
else:
    st.info("👈 Please select a VM from the sidebar")

# Footer
st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")