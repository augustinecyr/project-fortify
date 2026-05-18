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
    st.markdown('<div class="error-card"><strong>Unable to load data</strong>Verify the backend is running and refresh the page.</div>', unsafe_allow_html=True)
    st.stop()

# ---- PAGE CONFIG ----
st.set_page_config(page_title="VM Health Monitor", layout="wide", page_icon="🖥️")

# ---- CUSTOM CSS ----
st.markdown("""
<style>
.block-container { padding-top: 1.5rem !important; }
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
    font-size: 2rem;
    font-weight: 700;
    color: #1e293b;
}
.info-delta {
    font-size: 0.8rem;
    margin-top: 0.25rem;
    color: #64748b;
}
.status-badge {
    display: inline-block;
    padding: 0.2rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    margin-left: 0.75rem;
}
.status-online { background-color: #dcfce7; color: #166534; }
.status-offline { background-color: #fee2e2; color: #991b1b; }
.vm-header {
    font-size: 1rem;
    margin-bottom: 1rem;
    color: #0f172a;
}
.vm-header strong {
    font-weight: 700;
}
.vm-meta {
    color: #94a3b8;
    font-size: 0.825rem;
}
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

token = st.session_state.get("token")
if not token:
    st.switch_page("pages/login.py")

title_col, btn_col = st.columns([9, 0.4])
with title_col:
    st.markdown("""
        <div class="page-header-title">VM Health Monitor</div>
        <div class="page-header-sub">Virtual machine health scoring and performance analytics</div>
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

health_data = api_client.get_health_score(selected_vm_id, token=token)

if not vm_details or not health_data:
    st.markdown('<div class="error-card"><strong>Unable to load data</strong>Verify the backend is running and refresh the page.</div>', unsafe_allow_html=True)
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
st.markdown("### VM Overview")
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

r1, r2, r3, r4 = st.columns(4)

with r1:
    render_card("CPU Usage", f"{vm_details.get('current_cpu') or 0:.1f}%")
with r2:
    render_card("Memory Usage", f"{vm_details.get('current_memory') or 0:.1f}%")
with r3:
    render_card("Disk Usage", f"{vm_details.get('current_disk') or 0:.1f}%")
with r4:
    render_card("Network I/O", f"↓ {vm_details.get('network_in_mbps') or 0:.1f} MB/s")

st.divider()

# ---- HEALTH ANALYSIS ----
st.markdown("### Health Score Analysis")
col_left, col_right = st.columns([1.2, 1])

with col_left:
    render_health_score(health_score, health_status, comp_scores)

with col_right:
    render_card("Anomalies Detected", anomaly_details.get("anomaly_count", 0))
    render_card("Average CPU", f"{anomaly_details.get('mean', 0):.1f}%")
    render_card("Variation", f"{anomaly_details.get('std_dev', 0):.1f}")
    st.markdown("""
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem; margin-top: 0.5rem;">
            <p style="font-weight: 600; margin-bottom: 0.5rem; color: #0f172a;">What these metrics mean:</p>
            <ul style="margin: 0; padding-left: 1.2rem; color: #334155; line-height: 1.5;">
                <li><strong>Anomalies Detected</strong> – Points where CPU usage deviates significantly from normal, potentially indicating issues.</li>
                <li><strong>Average CPU</strong> – The mean CPU usage over the period, showing typical load.</li>
                <li><strong>Variation</strong> – How much CPU usage fluctuates; low = stable, high = erratic.</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# ---- PERFORMANCE SECTION ----
st.markdown("### Performance Metrics")

# 1️⃣ Put selector FIRST
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

# 2️⃣ THEN create tabs
tab1, tab2 = st.tabs(["💻 CPU Performance", "🧠 Memory Status"])


# ===============================
# ---- TAB 1: CPU PERFORMANCE ---
# ===============================
with tab1:

    metrics_data = api_client.get_cpu_metrics(selected_vm_id, limit=limit, token=token)

    if metrics_data and metrics_data.get("metrics"):
        df = pd.DataFrame(metrics_data["metrics"])
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        anomalous_indices = []
        if time_range == "Last 24 Hours":
            anomalous_indices = anomaly_details.get("anomalous_indices", [])
            anomalous_indices = [
                i for i in anomalous_indices if 0 <= i < len(df)
            ]

        fig = create_cpu_timeseries(
            metrics_data["metrics"],
            df["cpu_percent"].mean(),
            anomalous_indices,
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

    else:
        st.warning("No CPU metrics available for this VM.")


# =============================
# ---- TAB 2: MEMORY STATUS ---
# =============================
with tab2:

    st.info("💡 **Current Memory Snapshot** - Historical memory tracking coming soon")

    current_memory = vm_details.get("current_memory")
    memory_used_mb = vm_details.get("memory_used_mb")
    memory_total_mb = vm_details.get("memory_total_mb")

    if (
        current_memory is not None
        and memory_used_mb is not None
        and memory_total_mb is not None
    ):

        available_mb = memory_total_mb - memory_used_mb

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            render_card("Memory Usage", f"{current_memory:.1f}%")
        with m2:
            render_card("Used", f"{memory_used_mb:,} MB")
        with m3:
            render_card("Total", f"{memory_total_mb:,} MB")
        with m4:
            render_card("Available", f"{available_mb:,} MB")

        if current_memory >= 80:
            status_text = "Critical"
            status_color = "#dc2626"
        elif current_memory >= 60:
            status_text = "Warning"
            status_color = "#f59e0b"
        else:
            status_text = "Healthy"
            status_color = "#059669"

        st.markdown(
            f"""
            <div style="
                margin-top: 1rem;
                padding: 0.75rem;
                background-color: #f8fafc;
                border-left: 4px solid {status_color};
                border-radius: 6px;">
                <strong>Status:</strong> {status_text}
                <span style="color: #64748b; font-size: 0.9rem; margin-left: 0.5rem;">
                    (Healthy &lt;60%, Warning 60-80%, Critical &gt;80%)
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:
        st.warning("Incomplete memory data available")
                                            
st.divider()

# ---- AI ANALYSIS ----
RISK_STYLES = {
    "critical": ("#fee2e2", "#991b1b", "#dc2626"),
    "high":     ("#fee2e2", "#991b1b", "#dc2626"),
    "medium":   ("#fef3c7", "#92400e", "#d97706"),
    "low":      ("#f0fdf4", "#166534", "#059669"),
}

# Load from session state or fetch once
ai_cache_key = f"vm_ai_{selected_vm_id}"
if ai_cache_key not in st.session_state:
    with st.spinner("Loading AI analysis..."):
        ai_result = api_client.get_vm_analysis(selected_vm_id, token=token)
    st.session_state[ai_cache_key] = (
        ai_result if (ai_result and not ai_result.get("is_fallback")) else None
    )

ai_data = st.session_state.get(ai_cache_key)

# Header row — title + refresh button
ai_title_col, ai_btn_col = st.columns([9, 0.4])
with ai_title_col:
    st.markdown('<div class="section-header">AI Analysis</div>', unsafe_allow_html=True)
with ai_btn_col:
    if st.button("↻", key=f"refresh_ai_{selected_vm_id}",
                 help="Clears cache and requests a fresh Groq analysis",
                 width="stretch"):
        api_client.clear_ai_cache(token=token)
        if ai_cache_key in st.session_state:
            del st.session_state[ai_cache_key]
        st.rerun()

if ai_data:
    risk = ai_data.get("risk_level", "medium").lower()
    rbg, rfg, rborder = RISK_STYLES.get(risk, RISK_STYLES["medium"])
    ts = ai_data.get("analysis_timestamp", "")
    model = ai_data.get("model_used", "—")
    actions = ai_data.get("recommended_actions", [])

    try:
        ts_fmt = datetime.fromisoformat(ts).strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        ts_fmt = ts

    # Subheader with meta
    st.markdown(
        f'<div class="section-subheader">Model: {model} &nbsp;·&nbsp; Analysed: {ts_fmt}</div>',
        unsafe_allow_html=True
    )

    # ---- TOP ROW — Risk + action count + prediction horizon ----
    r1, r2, r3 = st.columns(3)

    with r1:
        st.markdown(f"""
            <div class="metric-card" style="border-left:4px solid {rborder};">
                <div class="info-label">Risk Level</div>
                <div class="info-value" style="font-size:1.5rem;color:{rfg};">{risk.capitalize()}</div>
                <div class="info-delta">Assessed by Groq LLM</div>
            </div>
        """, unsafe_allow_html=True)

    with r2:
        action_count = len(actions)
        ac = "#dc2626" if action_count > 0 else "#059669"
        st.markdown(f"""
            <div class="metric-card">
                <div class="info-label">Recommended Actions</div>
                <div class="info-value" style="font-size:1.5rem;color:{ac};">{action_count}</div>
                <div class="info-delta">{"Review actions below" if action_count > 0 else "No actions required"}</div>
            </div>
        """, unsafe_allow_html=True)

    with r3:
        prediction_text = ai_data.get("prediction", "")
        # Extract timeframe hint from prediction text
        horizon = "24–48 hours"
        for phrase in ["24 hours", "48 hours", "7 days", "week", "month"]:
            if phrase in prediction_text.lower():
                horizon = phrase
                break
        st.markdown(f"""
            <div class="metric-card">
                <div class="info-label">Prediction Horizon</div>
                <div class="info-value" style="font-size:1.5rem;color:#6366f1;">{horizon}</div>
                <div class="info-delta">Forecast window</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- NARRATIVE ROW — Health + Anomaly side by side ----
    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown("""
            <div style="font-size:0.75rem;font-weight:600;color:#64748b;
                        text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.4rem;">
                Health Explanation
            </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
            <div style="background:#f8fafc;border-left:4px solid #6366f1;
                        border-radius:0.5rem;padding:0.875rem 1rem;
                        font-size:0.875rem;color:#1e3a5f;line-height:1.7;">
                {ai_data.get('health_explanation', '—')}
            </div>
        """, unsafe_allow_html=True)

    with right_col:
        st.markdown("""
            <div style="font-size:0.75rem;font-weight:600;color:#64748b;
                        text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.4rem;">
                Anomaly Explanation
            </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
            <div style="background:#f8fafc;border-left:4px solid #e2e8f0;
                        border-radius:0.5rem;padding:0.875rem 1rem;
                        font-size:0.875rem;color:#334155;line-height:1.7;">
                {ai_data.get('anomaly_explanation', '—')}
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- ACTIONS + PREDICTION ROW ----
    act_col, pred_col = st.columns(2)

    with act_col:
        st.markdown("""
            <div style="font-size:0.75rem;font-weight:600;color:#64748b;
                        text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.4rem;">
                Recommended Actions
            </div>
        """, unsafe_allow_html=True)
        if actions:
            for action in actions:
                pri = action.get("priority", "low").lower()
                abg, afg, aborder = RISK_STYLES.get(pri, RISK_STYLES["low"])
                st.markdown(f"""
                    <div style="background:{abg};border-left:3px solid {aborder};
                                border-radius:6px;padding:0.65rem 0.875rem;
                                margin-bottom:0.5rem;">
                        <span style="font-size:0.7rem;font-weight:700;
                                     text-transform:uppercase;letter-spacing:0.05em;
                                     color:{afg};">{pri}</span>
                        <span style="font-size:0.825rem;color:{afg};margin-left:8px;">
                            {action.get('action', '—')}
                        </span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div style="background:#f0fdf4;border-left:3px solid #059669;
                            border-radius:6px;padding:0.65rem 0.875rem;
                            font-size:0.825rem;color:#166534;">
                    No actions required — VM is operating normally.
                </div>
            """, unsafe_allow_html=True)

    with pred_col:
        st.markdown("""
            <div style="font-size:0.75rem;font-weight:600;color:#64748b;
                        text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.4rem;">
                Prediction
            </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
            <div style="background:#fafaf9;border-left:4px solid #8b5cf6;
                        border-radius:0.5rem;padding:0.875rem 1rem;
                        font-size:0.875rem;color:#44403c;line-height:1.7;">
                {ai_data.get('prediction', '—')}
            </div>
        """, unsafe_allow_html=True)

else:
    st.markdown('<div class="section-subheader">Groq LLM deep-dive — click ↻ to run analysis</div>',
                unsafe_allow_html=True)
    st.markdown("""
        <div style="background:#f8fafc;border:1px dashed #cbd5e1;border-radius:10px;
                    padding:2rem 1.5rem;text-align:center;">
            <div style="font-size:0.9rem;font-weight:600;color:#0f172a;margin-bottom:0.3rem;">
                No analysis available
            </div>
            <div style="font-size:0.825rem;color:#64748b;">
                Click the <strong>↻</strong> button above to generate an AI analysis for this VM.
            </div>
        </div>
    """, unsafe_allow_html=True)

st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Project Fortify v0.8.0")