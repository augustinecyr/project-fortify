"""
VM Health Page - Final working version.
Uses components/health_widget.py, components/charts.py, utils/export.py.
All fixes applied: dynamic mean, anomalies only for 24h, one-click export.
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# ---- FIX PATHS ----
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "components"))

# ---- IMPORTS (with immediate error if missing) ----
try:
    from api_client import FortifyAPIClient
    from helpers import get_health_status_class
    from components.charts import create_cpu_timeseries
    from components.health_widget import render_health_score
    from utils.export import generate_csv_report, generate_json_report
except ImportError as e:
    st.error(f"Import failed: {e}. Make sure all component files exist.")
    st.stop()

# ---- INIT ----
st.set_page_config(page_title="VM Health Monitor", layout="wide", page_icon="🖥️")
api_client = FortifyAPIClient()

st.title("VM Health Monitor")
st.caption("Real-time health scoring and performance analytics")

# ---- SIDEBAR ----
with st.sidebar:
    st.markdown("### VM Selection")
    vms_summary = api_client.get_vms_summary()
    if not vms_summary:
        st.error("No VMs found. Is the API running?")
        st.stop()

    vms = vms_summary.get("vms", [])
    vm_options = {f"{vm['vm_id']} - {vm['name']}": vm['vm_id'] for vm in vms}
    selected_display = st.selectbox("Select VM", list(vm_options.keys()), label_visibility="collapsed")
    selected_vm_id = vm_options[selected_display]

    if st.button("Refresh Data", width='stretch'):
        st.cache_data.clear()
        st.rerun()

# ---- MAIN CONTENT (protected) ----
if selected_vm_id:
    try:
        # ---- HEALTH DATA ----
        with st.spinner("Loading health data..."):
            health_data = api_client.get_health_score(selected_vm_id)
        if not health_data:
            st.error("No health data received.")
            st.stop()

        vm_name = health_data.get("vm_name", "Unknown")
        health_score = health_data.get("health_score", 0)
        components = health_data.get("components", {})
        anomaly_details = health_data.get("anomaly_details", {})
        metrics_analyzed = health_data.get("metrics_analyzed", 0)

        st.markdown(f"### {selected_vm_id} – {vm_name}")

        # ---- HEALTH WIDGET + ANOMALY DETAILS ----
        comp_scores = {
            "anomaly_score": components.get("anomaly_score", 0) * 100,
            "stability_score": components.get("stability_score", 0) * 100,
            "historical_score": components.get("historical_score", 0) * 100,
        }
        _, status, _ = get_health_status_class(health_score)

        col_left, col_right = st.columns([1.2, 1])
        with col_left:
            render_health_score(health_score, status, comp_scores)
        with col_right:
            st.markdown("### Anomaly Details")
            st.metric("Anomalies", anomaly_details.get("anomaly_count", 0))
            st.metric("Data Points", f"{anomaly_details.get('total_points', 0):,}")
            st.metric("Avg CPU", f"{anomaly_details.get('mean', 0):.1f}%")
            st.metric("Std Dev", f"{anomaly_details.get('std_dev', 0):.1f}")
            st.caption(f"📊 {metrics_analyzed} data points analyzed")

        st.divider()

        # ---- CPU METRICS ----
        st.markdown("## CPU Metrics Analysis")
        time_range = st.selectbox(
            "Time Range",
            ["Last 1 Hour", "Last 6 Hours", "Last 12 Hours", "Last 24 Hours"],
            index=3
        )
        limit = {
            "Last 1 Hour": 60,
            "Last 6 Hours": 360,
            "Last 12 Hours": 720,
            "Last 24 Hours": 1440
        }[time_range]

        with st.spinner("Loading CPU metrics..."):
            metrics_data = api_client.get_cpu_metrics(selected_vm_id, limit=limit)

        if not metrics_data or not metrics_data.get("metrics"):
            st.warning("No CPU metrics available.")
            st.stop()

        metrics_list = metrics_data["metrics"]
        df = pd.DataFrame(metrics_list)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # ---- PLOTLY CHART (dynamic mean, anomalies only for 24h) ----
        current_mean = df['cpu_percent'].mean()
        anomalous_indices = []
        if time_range == "Last 24 Hours":
            anomalous_indices = anomaly_details.get("anomalous_indices", [])
            # Keep only valid indices (within current metrics length)
            anomalous_indices = [i for i in anomalous_indices if i < len(metrics_list)]

        fig = create_cpu_timeseries(
            metrics_list,
            current_mean,
            anomalous_indices,
            height=400
        )
        st.plotly_chart(fig, width='stretch')

        # ---- STATISTICS ----
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Min CPU", f"{df['cpu_percent'].min():.1f}%")
        col2.metric("Max CPU", f"{df['cpu_percent'].max():.1f}%")
        col3.metric("Avg CPU", f"{df['cpu_percent'].mean():.1f}%")
        col4.metric("Current CPU", f"{df['cpu_percent'].iloc[-1]:.1f}%")

        st.divider()

        # ---- ONE-CLICK EXPORT ----
        st.markdown("### Export Report")
        fmt = st.radio("Format", ["CSV", "JSON"], horizontal=True, label_visibility="collapsed")

        export_data = {
            "health_score": health_score,
            "status": status,
            "anomaly_score": comp_scores["anomaly_score"],
            "stability_score": comp_scores["stability_score"],
            "historical_score": comp_scores["historical_score"],
            "metrics_analyzed": metrics_analyzed,
            "anomaly_count": anomaly_details.get("anomaly_count", 0),
            "total_points": anomaly_details.get("total_points", 0),
            "mean_cpu": anomaly_details.get("mean", 0),
            "std_dev": anomaly_details.get("std_dev", 0),
        }
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')

        if fmt == "CSV":
            st.download_button(
                label="Export",
                data=lambda: generate_csv_report(selected_vm_id, vm_name, export_data, df, time_range),
                file_name=f"{selected_vm_id}_report_{ts}.csv",
                mime="text/csv",
                type="primary"
            )
        else:
            st.download_button(
                label="Export",
                data=lambda: generate_json_report(selected_vm_id, vm_name, export_data, metrics_list, time_range),
                file_name=f"{selected_vm_id}_report_{ts}.json",
                mime="application/json",
                type="primary"
            )

    except Exception as e:
        st.error("An error occurred. See details below:")
        st.exception(e)  # Full traceback in browser
else:
    st.info("Select a VM from the sidebar.")

st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")