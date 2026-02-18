"""
VM Health Monitor - Enhanced with comprehensive VM information
Displays health scoring, resource utilization, security metrics, and performance analytics.
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
except ImportError as e:
    st.error(f"Import failed: {e}. Make sure all component files exist.")
    st.stop()

# ---- CUSTOM CSS ----
st.markdown("""
    <style>
    .metric-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    .info-label {
        font-size: 0.875rem;
        color: #64748b;
        font-weight: 500;
        margin-bottom: 0.25rem;
    }
    .info-value {
        font-size: 1.125rem;
        color: #212529;
        font-weight: 600;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .status-online { background-color: #dcfce7; color: #166534; }
    .status-offline { background-color: #fee2e2; color: #991b1b; }
    </style>
""", unsafe_allow_html=True)

# ---- INIT ----
st.set_page_config(page_title="VM Health Monitor", layout="wide", page_icon="🖥️")
api_client = FortifyAPIClient()

st.title("VM Health Monitor")
st.caption("Comprehensive health scoring, performance analytics, and security monitoring")

# ---- LOAD VM LIST ----
vms_summary = api_client.get_vms_summary()
if not vms_summary:
    st.error("No VMs found. Is the API running?")
    st.stop()

vms = vms_summary.get("vms", [])

# Sort VMs by VM ID for consistent ordering
sorted_vms = sorted(vms, key=lambda x: x['vm_id'])

# Create a list of display strings and a mapping back to VM ID
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

# ---- TOP ROW: VM SELECTOR + REFRESH BUTTONS ----
col_sel, col_refresh = st.columns([3, 0.5])
with col_sel:
    selected_display = st.selectbox(
        "Select Virtual Machine",
        vm_display_list,          # Use the sorted list directly
        index=default_index,
        label_visibility="collapsed",
        placeholder="Choose a VM...",
        key="vm_selector"
    )
    selected_vm_id = vm_id_by_display[selected_display]
with col_refresh:
    if st.button("🔄", help="Refresh data"):
        st.cache_data.clear()
        st.rerun()

# ---- FETCH DETAILED VM INFO ----
# CRITICAL FIX: Need to fetch individual VM details from API
# The summary endpoint might not return all fields
with st.spinner("Loading VM details..."):
    # Try to get detailed VM info - you may need to add this endpoint to your API
    # For now, we'll use the summary data and show what's available
    vm_details = None
    for vm in vms:
        if vm['vm_id'] == selected_vm_id:
            vm_details = vm
            break
    
    if not vm_details:
        st.error(f"VM {selected_vm_id} not found")
        st.stop()
    
    # Get health score data
    health_data = api_client.get_health_score(selected_vm_id)

if not health_data:
    st.error("No health data received.")
    st.stop()

# ---- DEBUG: Show what data we actually have ----
with st.expander("🔍 Preview Data", expanded=False):
    st.write("**VM Details from Summary:**")
    st.json(vm_details)
    st.write("**Available Keys:**")
    st.write(list(vm_details.keys()))

# ---- EXTRACT VM DATA (with proper fallbacks) ----
vm_name = vm_details.get("name", "Unknown")
vm_status = vm_details.get("status", "unknown")

# These might not be in the summary - check what's actually available
host = vm_details.get("host", "Not available in API")
os_version = vm_details.get("os_version", "Not available in API")
uptime_hours = vm_details.get("uptime_hours")
health_score_vm = vm_details.get("health_score")
security_score = vm_details.get("security_score", 0)
alert_count = vm_details.get("alert_count", 0)

# Current resource metrics
current_cpu = vm_details.get("current_cpu")
current_memory = vm_details.get("current_memory")
current_disk = vm_details.get("current_disk")
memory_used_mb = vm_details.get("memory_used_mb")
memory_total_mb = vm_details.get("memory_total_mb")
disk_used_gb = vm_details.get("disk_used_gb")
disk_total_gb = vm_details.get("disk_total_gb")
network_in = vm_details.get("network_in_mbps")
network_out = vm_details.get("network_out_mbps")

# Security metrics
open_vulns = vm_details.get("open_vulnerabilities", 0)
critical_vulns = vm_details.get("critical_vulnerabilities", 0)
last_patch = vm_details.get("last_patch_date")
compliance = vm_details.get("compliance_score", "N/A")
firewall = vm_details.get("firewall_enabled")
ssh_key = vm_details.get("ssh_key_auth")
encryption = vm_details.get("disk_encryption")

# ---- VM HEADER WITH STATUS ----
status_class = "status-online" if vm_status == "online" else "status-offline"
st.markdown(f"""
    <h3>{selected_vm_id} – {vm_name} 
    <span class="status-badge {status_class}">{vm_status.upper()}</span></h3>
""", unsafe_allow_html=True)

# Only show host/OS if available
if host and host != "Not available in API":
    st.markdown(f"<p style='color: #6c757d; margin-top: -0.5rem;'>🖥️ Host: {host} | 💿 OS: {os_version}</p>", 
                unsafe_allow_html=True)
else:
    st.info("ℹ️ **Note:** Host and OS information not available from API. The summary endpoint may not include all VM fields. Consider fetching individual VM details.")

# ---- VM OVERVIEW CARDS ----
st.markdown("### 📊 VM Overview")

info_col1, info_col2, info_col3, info_col4 = st.columns(4)

with info_col1:
    if uptime_hours is not None and uptime_hours > 0:
        uptime_days = uptime_hours / 24
        st.markdown(f"""
            <div class="metric-card">
                <div class="info-label">UPTIME</div>
                <div class="info-value">{uptime_days:.1f} days</div>
            </div>
        """, unsafe_allow_html=True)
    elif vm_status == "online":
        st.markdown("""
            <div class="metric-card">
                <div class="info-label">UPTIME</div>
                <div class="info-value">Unknown</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div class="metric-card">
                <div class="info-label">UPTIME</div>
                <div class="info-value">Offline</div>
            </div>
        """, unsafe_allow_html=True)

with info_col2:
    if health_score_vm is not None:
        st.markdown(f"""
            <div class="metric-card">
                <div class="info-label">HEALTH SCORE</div>
                <div class="info-value">{health_score_vm}/100</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div class="metric-card">
                <div class="info-label">HEALTH SCORE</div>
                <div class="info-value">Not Available</div>
            </div>
        """, unsafe_allow_html=True)

with info_col3:
    st.markdown(f"""
        <div class="metric-card">
            <div class="info-label">SECURITY SCORE</div>
            <div class="info-value">{security_score}/100</div>
        </div>
    """, unsafe_allow_html=True)

with info_col4:
    alert_icon = "🔴" if alert_count > 0 else "🟢"
    st.markdown(f"""
        <div class="metric-card">
            <div class="info-label">ALERTS</div>
            <div class="info-value">{alert_icon} {alert_count}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---- RESOURCE UTILIZATION ----
if vm_status == "online" and current_cpu is not None:
    st.markdown("### 💻 Current Resource Utilization")
    
    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    
    with res_col1:
        avg_cpu_24h = vm_details.get("avg_cpu_24h", 0)
        delta = current_cpu - avg_cpu_24h if avg_cpu_24h else None
        st.metric("CPU Usage", f"{current_cpu:.1f}%", 
                 delta=f"{delta:+.1f}% vs 24h avg" if delta else None,
                 delta_color="inverse")
    
    with res_col2:
        if current_memory is not None and memory_total_mb:
            st.metric("Memory Usage", f"{current_memory:.1f}%",
                     delta=f"{memory_used_mb:,} / {memory_total_mb:,} MB" if memory_used_mb else None)
        else:
            st.metric("Memory Usage", "N/A")
    
    with res_col3:
        if current_disk is not None and disk_total_gb:
            st.metric("Disk Usage", f"{current_disk:.1f}%",
                     delta=f"{disk_used_gb:,} / {disk_total_gb:,} GB" if disk_used_gb else None)
        else:
            st.metric("Disk Usage", "N/A")
    
    with res_col4:
        if network_in is not None and network_out is not None:
            st.metric("Network I/O", f"↓ {network_in:.1f} MB/s",
                     delta=f"↑ {network_out:.1f} MB/s")
        else:
            st.metric("Network I/O", "N/A")
    
    st.divider()
else:
    if vm_status != "online":
        st.info("ℹ️ VM is offline - resource metrics not available")
    else:
        st.info("ℹ️ Resource utilization data not available from API")
    st.divider()

# ---- SECURITY & COMPLIANCE ----
if security_score > 0 or open_vulns > 0:
    st.markdown("### 🔒 Security & Compliance")
    
    sec_col1, sec_col2, sec_col3, sec_col4 = st.columns(4)
    
    with sec_col1:
        vuln_icon = "🔴" if critical_vulns > 0 else "🟡" if open_vulns > 0 else "🟢"
        st.metric("Vulnerabilities", f"{vuln_icon} {open_vulns}",
                 delta=f"{critical_vulns} critical" if critical_vulns > 0 else "No critical issues")
    
    with sec_col2:
        if last_patch:
            try:
                patch_date = pd.to_datetime(last_patch)
                days_since = (datetime.now() - patch_date).days
                patch_status = "🟢" if days_since < 7 else "🟡" if days_since < 30 else "🔴"
                st.metric("Last Patched", f"{patch_status} {days_since}d ago",
                         delta=patch_date.strftime("%Y-%m-%d"))
            except:
                st.metric("Last Patched", "Unknown")
        else:
            st.metric("Last Patched", "Not recorded")
    
    with sec_col3:
        st.metric("Compliance", compliance)
    
    with sec_col4:
        sec_features = []
        if firewall: sec_features.append("🛡️")
        if ssh_key: sec_features.append("🔑")
        if encryption: sec_features.append("🔒")
        
        enabled_count = len(sec_features)
        st.metric("Security Features", f"{enabled_count}/3",
                 delta=" ".join(sec_features) if sec_features else "None enabled")
    
    st.divider()

# ---- HEALTH SCORE DETAILS ----
st.markdown("### 💚 Health Score Analysis")

health_score = health_data.get("health_score", 0)
components = health_data.get("components", {})
anomaly_details = health_data.get("anomaly_details", {})
metrics_analyzed = health_data.get("metrics_analyzed", 0)

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
    st.markdown("#### Anomaly Detection")
    st.metric("Anomalies Detected", anomaly_details.get("anomaly_count", 0))
    st.metric("Data Points Analyzed", f"{anomaly_details.get('total_points', 0):,}")
    st.metric("Average CPU", f"{anomaly_details.get('mean', 0):.1f}%")
    st.metric("Standard Deviation", f"{anomaly_details.get('std_dev', 0):.1f}")
    st.caption(f"📊 {metrics_analyzed} total metrics analyzed")

st.divider()

# ---- CPU METRICS ----
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

with st.spinner("Loading CPU metrics..."):
    metrics_data = api_client.get_cpu_metrics(selected_vm_id, limit=limit)

if not metrics_data or not metrics_data.get("metrics"):
    st.warning("No CPU metrics available for this VM.")
else:
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
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    stat_col1.metric("Minimum", f"{df['cpu_percent'].min():.1f}%")
    stat_col2.metric("Maximum", f"{df['cpu_percent'].max():.1f}%")
    stat_col3.metric("Average", f"{df['cpu_percent'].mean():.1f}%")
    stat_col4.metric("Current", f"{df['cpu_percent'].iloc[-1]:.1f}%")

# ---- FOOTER ----
st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Project Fortify v0.2.0")