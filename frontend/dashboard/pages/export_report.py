"""Export VM Report - Standalone page for generating comprehensive VM reports."""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
import functools

# ---- PATH FIXES ----
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "components"))

# ---- IMPORTS ----
try:
    from api_client import FortifyAPIClient
    from utils.export import generate_csv_report, generate_json_report
except ImportError as e:
    st.markdown('<div class="error-card"><strong>Unable to load data</strong>Verify the backend is running and refresh the page.</div>', unsafe_allow_html=True)
    st.stop()

st.markdown("""
<style>
.block-container { padding-top: 1.5rem !important; }
.page-header-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.5px;
    margin: 0 0 0.15rem 0;
    line-height: 1.2;
}
.page-header-sub {
    font-size: 0.825rem;
    color: #64748b;
    margin: 0;
    font-weight: 400;
}
.header-divider {
    border: none;
    border-bottom: 1px solid #e2e8f0;
    margin: 0.75rem 0 1.5rem 0;
}
.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #0f172a;
    margin: 1.75rem 0 0.25rem 0;
}
.error-card {
    background: #fee2e2;
    border-left: 4px solid #ef4444;
    border-radius: 0.5rem;
    padding: 1rem 1.25rem;
    color: #7f1d1d;
    font-size: 0.875rem;
    margin-bottom: 1rem;
}
.error-card strong {
    display: block;
    color: #991b1b;
    font-size: 0.9rem;
    margin-bottom: 0.25rem;
}
div[data-testid="stButton"] button {
    padding: 0.1rem 0.35rem !important;
    font-size: 1rem;
    line-height: 1;
    min-height: 0 !important;
    height: auto !important;
    border-color: #e2e8f0;
    color: #94a3b8;
    background: white;
}
div[data-testid="stButton"] button:hover {
    border-color: #94a3b8;
    color: #0f172a;
    background: #f8fafc;
}
</style>
""", unsafe_allow_html=True)

# ---- INIT API ----
api_client = FortifyAPIClient()

token = st.session_state.get("token")
if not token:
    st.switch_page("pages/login.py")

title_col, btn_col = st.columns([9, 0.4])
with title_col:
    st.markdown("""
        <div class="page-header-title">Export Report</div>
        <div class="page-header-sub">Generate and download comprehensive VM health and metrics reports</div>
    """, unsafe_allow_html=True)
with btn_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↻", help="Refresh", width="stretch"):
        st.cache_data.clear()
        st.rerun()
st.markdown('<hr class="header-divider">', unsafe_allow_html=True)

# ---- LOAD VM LIST ----
vms_summary = api_client.get_vms_summary(token=token)
if not vms_summary:
    st.markdown('<div class="error-card"><strong>Unable to load data</strong>Verify the backend is running and refresh the page.</div>', unsafe_allow_html=True)
    st.stop()

vms = vms_summary.get("vms", [])

# Sort VMs by VM ID for consistent ordering
sorted_vms = sorted(vms, key=lambda x: x['vm_id'])
vm_display_list = [f"{vm['vm_id']} - {vm['name']}" for vm in sorted_vms]
vm_id_by_display = {display: vm['vm_id'] for display, vm in zip(vm_display_list, sorted_vms)}

# ---- VM SELECTOR ----
selected_display = st.selectbox(
    "Select Virtual Machine",
    vm_display_list,
    index=0,
    key="vm_selector"
)
selected_vm_id = vm_id_by_display[selected_display]

# ---- TIME RANGE SELECTOR ----
time_range = st.selectbox(
    "Time Range for CPU Metrics",
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

# ---- FETCH DATA ----
# Get VM details from summary
vm_details = next((vm for vm in vms if vm['vm_id'] == selected_vm_id), None)
if not vm_details:
    st.markdown('<div class="error-card"><strong>Unable to load data</strong>Verify the backend is running and refresh the page.</div>', unsafe_allow_html=True)
    st.stop()

# Health score data
health_data = api_client.get_health_score(selected_vm_id, token=token)
if not health_data:
    st.markdown('<div class="error-card"><strong>Unable to load data</strong>Verify the backend is running and refresh the page.</div>', unsafe_allow_html=True)
    st.stop()

# CPU metrics
metrics_data = api_client.get_cpu_metrics(selected_vm_id, limit=limit, token=token)
metrics_list = metrics_data.get("metrics", []) if metrics_data else []

# ---- BUILD EXPORT DATA DICTIONARY (same as in vm_health_monitor) ----
vm_name = vm_details.get("name", "Unknown")
vm_status = vm_details.get("status", "unknown")
host = vm_details.get("host", "Not available")
os_version = vm_details.get("os_version", "Not available")
uptime_hours = vm_details.get("uptime_hours")
health_score_vm = vm_details.get("health_score")
security_score = vm_details.get("security_score", 0)
alert_count = vm_details.get("alert_count", 0)

current_cpu = vm_details.get("current_cpu")
current_memory = vm_details.get("current_memory")
current_disk = vm_details.get("current_disk")
memory_used_mb = vm_details.get("memory_used_mb")
memory_total_mb = vm_details.get("memory_total_mb")
disk_used_gb = vm_details.get("disk_used_gb")
disk_total_gb = vm_details.get("disk_total_gb")
network_in = vm_details.get("network_in_mbps")
network_out = vm_details.get("network_out_mbps")

open_vulns = vm_details.get("open_vulnerabilities", 0)
critical_vulns = vm_details.get("critical_vulnerabilities", 0)
last_patch = vm_details.get("last_patch_date")
compliance = vm_details.get("compliance_score", "N/A")
firewall = vm_details.get("firewall_enabled")
ssh_key = vm_details.get("ssh_key_auth")
encryption = vm_details.get("disk_encryption")

# Component scores from health_data
components = health_data.get("components", {})
anomaly_details = health_data.get("anomaly_details", {})
metrics_analyzed = health_data.get("metrics_analyzed", 0)

comp_scores = {
    "anomaly_score": components.get("anomaly_score", 0) * 100,
    "stability_score": components.get("stability_score", 0) * 100,
    "historical_score": components.get("historical_score", 0) * 100,
}

export_data = {
    "vm_id": selected_vm_id,
    "vm_name": vm_name,
    "status": vm_status,
    "host": host if host != "Not available" else None,
    "os_version": os_version if os_version != "Not available" else None,
    "uptime_hours": uptime_hours,
    "health_score": health_data.get("health_score", 0),
    "health_status": "Healthy" if health_data.get("health_score", 0) >= 80 else "Warning" if health_data.get("health_score", 0) >= 60 else "Critical",
    "security_score": security_score,
    "anomaly_score": comp_scores["anomaly_score"],
    "stability_score": comp_scores["stability_score"],
    "historical_score": comp_scores["historical_score"],
    "metrics_analyzed": metrics_analyzed,
    "current_cpu": current_cpu,
    "current_memory": current_memory,
    "current_disk": current_disk,
    "memory_total_mb": memory_total_mb,
    "memory_used_mb": memory_used_mb,
    "disk_total_gb": disk_total_gb,
    "disk_used_gb": disk_used_gb,
    "network_in_mbps": network_in,
    "network_out_mbps": network_out,
    "open_vulnerabilities": open_vulns,
    "critical_vulnerabilities": critical_vulns,
    "last_patch_date": str(last_patch) if last_patch else None,
    "compliance_score": compliance,
    "firewall_enabled": firewall,
    "ssh_key_auth": ssh_key,
    "disk_encryption": encryption,
    "alert_count": alert_count,
    "anomaly_detected": vm_details.get("anomaly_detected", False),
    "anomaly_count": anomaly_details.get("anomaly_count", 0),
    "total_points": anomaly_details.get("total_points", 0),
    "mean_cpu": anomaly_details.get("mean", 0),
    "std_dev": anomaly_details.get("std_dev", 0),
}

# Create DataFrame for metrics if available
if metrics_list:
    df = pd.DataFrame(metrics_list)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
else:
    df = pd.DataFrame(columns=['timestamp', 'cpu_percent', 'source'])

# ---- EXPORT BUTTONS ----
st.markdown('<div class="section-header">Generate Report</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
ts = datetime.now().strftime('%Y%m%d_%H%M%S')

with col1:
    csv_data = generate_csv_report(
        vm_id=selected_vm_id,
        vm_name=vm_name,
        health_data=export_data,
        metrics_df=df,
        time_range=time_range
    )
    st.download_button(
        label="📥 Download CSV Report",
        data=csv_data,
        file_name=f"{selected_vm_id}_report_{ts}.csv",
        mime="text/csv",
        width="stretch"
    )

with col2:
    json_data = generate_json_report(
        vm_id=selected_vm_id,
        vm_name=vm_name,
        health_data=export_data,
        metrics_list=metrics_list,
        time_range=time_range
    )
    st.download_button(
        label="📥 Download JSON Report",
        data=json_data,
        file_name=f"{selected_vm_id}_report_{ts}.json",
        mime="application/json",
        width="stretch"
    )

# Optional: Show a preview of the data
with st.expander("Preview Exported Data"):
    st.json(export_data)

st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Project Fortify v0.8.0")