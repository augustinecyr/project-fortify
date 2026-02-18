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
    st.error(f"Import failed: {e}. Make sure all component files exist.")
    st.stop()

st.set_page_config(page_title="Export VM Report", page_icon="📥", layout="wide")
st.title("📥 Export VM Report")
st.caption("Generate a comprehensive CSV or JSON report for any virtual machine.")

# ---- INIT API ----
api_client = FortifyAPIClient()

# ---- LOAD VM LIST ----
vms_summary = api_client.get_vms_summary()
if not vms_summary:
    st.error("No VMs found. Is the API running?")
    st.stop()

vms = vms_summary.get("vms", [])
vm_options = {f"{vm['vm_id']} - {vm['name']}": vm['vm_id'] for vm in vms}

# ---- VM SELECTOR ----
selected_display = st.selectbox(
    "Select Virtual Machine",
    list(vm_options.keys()),
    index=0,
    key="vm_selector"
)
selected_vm_id = vm_options[selected_display]

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
with st.spinner("Fetching VM data and metrics..."):
    # Get VM details from summary
    vm_details = next((vm for vm in vms if vm['vm_id'] == selected_vm_id), None)
    if not vm_details:
        st.error("VM not found.")
        st.stop()

    # Health score data
    health_data = api_client.get_health_score(selected_vm_id)
    if not health_data:
        st.error("No health data received.")
        st.stop()

    # CPU metrics
    metrics_data = api_client.get_cpu_metrics(selected_vm_id, limit=limit)
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
st.markdown("### Generate Report")
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
        use_container_width=True
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
        use_container_width=True
    )

# Optional: Show a preview of the data
with st.expander("Preview Exported Data"):
    st.json(export_data)