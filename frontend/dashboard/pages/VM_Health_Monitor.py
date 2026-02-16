"""
VM Health Page - Streamlined UI with top VM selector, refresh icon, and inline export buttons.
Supports ?vm=vm-XXX URL parameter for deep linking.
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
import functools

# ---- FIX PATHS ----
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "components"))

# ---- IMPORTS ----
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

# ---- LOAD VM LIST ----
vms_summary = api_client.get_vms_summary()
if not vms_summary:
    st.error("No VMs found. Is the API running?")
    st.stop()

vms = vms_summary.get("vms", [])
vm_options = {f"{vm['vm_id']} - {vm['name']}": vm['vm_id'] for vm in vms}

# ---- READ QUERY PARAMETER ----
query_params = st.query_params
preselected_vm = query_params.get("vm", None)
default_index = 0
if preselected_vm:
    for i, (display, vm_id) in enumerate(vm_options.items()):
        if vm_id == preselected_vm:
            default_index = i
            break

# ---- TOP ROW: VM SELECTOR + REFRESH + EXPORT BUTTONS ----
col_sel, col_refresh, col_csv, col_json = st.columns([3, 0.5, 1.5, 1.5])
with col_sel:
    selected_display = st.selectbox(
        "Select Virtual Machine",
        list(vm_options.keys()),
        index=default_index,
        label_visibility="collapsed",
        placeholder="Choose a VM...",
        key="vm_selector"
    )
    selected_vm_id = vm_options[selected_display]

with col_refresh:
    # Use a simple, non‑primary button with emoji only
    if st.button("🔄", help="Refresh data"):
        st.cache_data.clear()
        st.rerun()

# Export buttons (will be updated after data load; placeholders for now)
csv_btn = col_csv.empty()
json_btn = col_json.empty()

# ---- FETCH DATA FOR SELECTED VM ----
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
    index=3,
    key="time_range"
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

# ---- PLOTLY CHART ----
current_mean = df['cpu_percent'].mean()
anomalous_indices = []
if time_range == "Last 24 Hours":
    anomalous_indices = anomaly_details.get("anomalous_indices", [])
    anomalous_indices = [i for i in anomalous_indices if 0 <= i < len(metrics_list)]

fig = create_cpu_timeseries(
    metrics_list,
    current_mean,
    anomalous_indices,
    height=450
)
st.plotly_chart(fig, width='stretch')

# ---- STATISTICS ----
col1, col2, col3, col4 = st.columns(4)
col1.metric("Min CPU", f"{df['cpu_percent'].min():.1f}%")
col2.metric("Max CPU", f"{df['cpu_percent'].max():.1f}%")
col3.metric("Avg CPU", f"{df['cpu_percent'].mean():.1f}%")
col4.metric("Current CPU", f"{df['cpu_percent'].iloc[-1]:.1f}%")

# ---- EXPORT BUTTONS (update placeholders with actual data) ----
ts = datetime.now().strftime('%Y%m%d_%H%M%S')

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

csv_report = functools.partial(
    generate_csv_report,
    vm_id=selected_vm_id,
    vm_name=vm_name,
    health_data=export_data,
    metrics_df=df,
    time_range=time_range
)

json_report = functools.partial(
    generate_json_report,
    vm_id=selected_vm_id,
    vm_name=vm_name,
    health_data=export_data,
    metrics_list=metrics_list,
    time_range=time_range
)

with csv_btn:
    st.download_button(
        label="Export CSV",
        data=csv_report,
        file_name=f"{selected_vm_id}_report_{ts}.csv",
        mime="text/csv",
        width='stretch'
    )
with json_btn:
    st.download_button(
        label="Export JSON",
        data=json_report,
        file_name=f"{selected_vm_id}_report_{ts}.json",
        mime="application/json",
        width='stretch'
    )

# ---- FOOTER ----
st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")