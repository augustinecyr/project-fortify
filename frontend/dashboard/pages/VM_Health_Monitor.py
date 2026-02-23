"""
VM Health Monitor - Enhanced with comprehensive VM information
Displays health scoring, resource utilization, security metrics, and performance analytics.
Supports ?vm=vm-XXX URL parameter for deep linking.
Now uses last_seen for connectivity badge.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ---- FIX PATHS ----
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "components"))

# ---- IMPORTS ----
try:
    from api_client import FortifyAPIClient
    from helpers import get_health_status_class
    from components.charts import create_cpu_timeseries
    from components.health_widget import render_health_score
except ImportError as e:
    st.error(f"Import failed: {e}. Make sure all component files exist.")
    st.stop()

# ---- PAGE CONFIG ----
st.set_page_config(page_title="VM Health Monitor", layout="wide", page_icon="🖥️")

# ---- CUSTOM CSS ----
st.markdown("""
<style>
.metric-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    height: 100%;
}
.info-label {
    font-size: 0.75rem;
    color: #64748b;
    font-weight: 600;
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}
.info-value {
    font-size: 1.4rem;
    font-weight: 700;
    color: #1e293b;
}
.info-delta {
    font-size: 0.85rem;
    margin-top: 0.25rem;
    color: #64748b;
}
.status-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 1rem;
    font-weight: 600;
    margin-left: 0.75rem;
}
.status-online { background-color: #dcfce7; color: #166534; }
.status-offline { background-color: #fee2e2; color: #991b1b; }

.vm-header {
    font-size: 1.25rem;
    margin-bottom: 1rem;
}
.vm-header strong {
    font-weight: 700;
}
.vm-meta {
    color: #475569;
}
</style>
""", unsafe_allow_html=True)

# ---- CARD HELPER ----
def render_card(label, value, delta=None):
    st.markdown(f"""
        <div class="metric-card">
            <div class="info-label">{label}</div>
            <div class="info-value">{value}</div>
            {f'<div class="info-delta">{delta}</div>' if delta else ''}
        </div>
    """, unsafe_allow_html=True)

# ---- INIT ----
api_client = FortifyAPIClient()
st.title("VM Health Monitor")
st.caption("Comprehensive health scoring, performance analytics, and security monitoring")

# ---- LOAD VM LIST ----
vms_summary = api_client.get_vms_summary()
if not vms_summary:
    st.error("No VMs found. Is the API running?")
    st.stop()

vms = vms_summary.get("vms", [])
sorted_vms = sorted(vms, key=lambda x: x['vm_id'])

vm_display_list = [f"{vm['vm_id']} - {vm['name']}" for vm in sorted_vms]
vm_id_by_display = {display: vm['vm_id'] for display, vm in zip(vm_display_list, sorted_vms)}

# ---- READ QUERY PARAMETER ----
query_params = st.query_params
preselected_vm = query_params.get("vm", None)
default_index = 0

if preselected_vm:
    for i, display in enumerate(vm_display_list):
        if vm_id_by_display[display] == preselected_vm:
            default_index = i
            break

# ---- VM SELECTOR ----
selected_display = st.selectbox(
    "Select Virtual Machine",
    vm_display_list,
    index=default_index,
    label_visibility="collapsed",
    key="vm_selector"
)

selected_vm_id = vm_id_by_display[selected_display]

# ---- FETCH DATA ----
vm_details = next((vm for vm in sorted_vms if vm['vm_id'] == selected_vm_id), None)

with st.spinner("Loading VM details..."):
    health_data = api_client.get_health_score(selected_vm_id)

if not vm_details or not health_data:
    st.error("Unable to load VM details.")
    st.stop()

# ---- RESTORE DATA PREVIEW ----
with st.expander("🔍 Preview Data", expanded=False):
    st.write("**VM Details from Summary:**")
    st.json(vm_details)
    st.write("**Health Data from get_health_score():**")
    st.json(health_data)

# ---- EXTRACT DATA ----
vm_name = vm_details.get("name", "Unknown")
host = vm_details.get("host", "N/A")
os_version = vm_details.get("os_version", "N/A")

health_score = health_data.get("health_score", 0)
components = health_data.get("components", {})
anomaly_details = health_data.get("anomaly_details", {})

comp_scores = {
    "anomaly_score": components.get("anomaly_score", 0) * 100,
    "stability_score": components.get("stability_score", 0) * 100,
    "historical_score": components.get("historical_score", 0) * 100,
}

_, health_status, _ = get_health_status_class(health_score)

# ---- COMPUTE CONNECTIVITY FROM LAST_SEEN ----
offline_threshold = timedelta(minutes=5)
now = datetime.now(timezone.utc)
last_seen_str = vm_details.get("last_seen")
is_online = False
if last_seen_str:
    try:
        if last_seen_str.endswith('Z'):
            last_seen_str = last_seen_str.replace('Z', '+00:00')
        last_seen = datetime.fromisoformat(last_seen_str)
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        is_online = (now - last_seen) <= offline_threshold
    except Exception:
        is_online = False

connectivity_status = "online" if is_online else "offline"
connectivity_badge_class = "status-online" if is_online else "status-offline"
connectivity_badge_text = "ONLINE" if is_online else "OFFLINE"

# ---- HORIZONTAL HEADER ----
st.markdown(f"""
<div class="vm-header">
    <strong>{selected_vm_id} – {vm_name}</strong>
    <span class="status-badge {connectivity_badge_class}">
        {connectivity_badge_text}
    </span>
    &nbsp;&nbsp;
    <span class="vm-meta">
        Host: {host} | OS: {os_version}
    </span>
</div>
""", unsafe_allow_html=True)

# ---- VM OVERVIEW ----
st.markdown("### 📊 VM Overview")
col1, col2, col3, col4 = st.columns(4)

with col1:
    uptime_hours = vm_details.get("uptime_hours")
    render_card("Uptime", f"{uptime_hours/24:.1f} days" if uptime_hours else "N/A")

with col2:
    render_card("Health Score", f"{health_score:.0f}/100")

with col3:
    render_card("Security Score", f"{vm_details.get('security_score', 0)}/100")

with col4:
    render_card("Alerts", vm_details.get("alert_count", 0))

st.divider()

# ---- RESOURCE UTILIZATION ----
st.markdown("### 💻 Current Resource Utilization")
r1, r2, r3, r4 = st.columns(4)

with r1:
    render_card("CPU Usage", f"{vm_details.get('current_cpu', 0):.1f}%")
with r2:
    render_card("Memory Usage", f"{vm_details.get('current_memory', 0):.1f}%")
with r3:
    render_card("Disk Usage", f"{vm_details.get('current_disk', 0):.1f}%")
with r4:
    render_card("Network I/O", f"↓ {vm_details.get('network_in_mbps', 0):.1f} MB/s")

st.divider()

# ---- HEALTH ANALYSIS ----
st.markdown("### 💚 Health Score Analysis")
col_left, col_right = st.columns([1.2, 1])

with col_left:
    render_health_score(health_score, health_status, comp_scores)

with col_right:
    render_card("Anomalies Detected", anomaly_details.get("anomaly_count", 0))
    render_card("Average CPU", f"{anomaly_details.get('mean', 0):.1f}%")
    render_card("Std Deviation", f"{anomaly_details.get('std_dev', 0):.1f}")

st.divider()

# ---- CPU PERFORMANCE ----
st.markdown("### 📈 CPU Performance Analysis")

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

metrics_data = api_client.get_cpu_metrics(selected_vm_id, limit=limit)

if metrics_data and metrics_data.get("metrics"):
    df = pd.DataFrame(metrics_data["metrics"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    fig = create_cpu_timeseries(
        metrics_data["metrics"],
        df["cpu_percent"].mean(),
        anomaly_details.get("anomalous_indices", []),
        height=450
    )

    st.plotly_chart(fig, width='stretch')

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        render_card("Minimum", f"{df['cpu_percent'].min():.1f}%")
    with s2:
        render_card("Maximum", f"{df['cpu_percent'].max():.1f}%")
    with s3:
        render_card("Average", f"{df['cpu_percent'].mean():.1f}%")
    with s4:
        render_card("Current", f"{df['cpu_percent'].iloc[-1]:.1f}%")

st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Project Fortify v0.3.2")