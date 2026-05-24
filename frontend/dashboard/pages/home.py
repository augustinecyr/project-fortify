"""
Project Fortify - Home Dashboard
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from api_client import FortifyAPIClient
from session import load_token

st.set_page_config(page_title="Project Fortify — Home", page_icon="🔒", layout="wide")

api_client = FortifyAPIClient()

token = load_token()
if not token:
    st.switch_page("pages/login.py")

st.markdown("""
<style>
/* Collapse default Streamlit top padding */
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
.page-header-timestamp {
    font-size: 0.75rem;
    color: #94a3b8;
    text-align: right;
}
.header-divider {
    border: none;
    border-bottom: 1px solid #e2e8f0;
    margin: 0.75rem 0 1.5rem 0;
}
.metric-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 1px 3px 0 rgba(0,0,0,0.07);
    transition: all 0.2s ease;
    margin-bottom: 1rem;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.metric-card:hover {
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    border-color: #cbd5e1;
}
.metric-card-header {
    font-size: 0.75rem;
    font-weight: 600;
    color: #64748b;
    margin-bottom: 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.metric-card-value {
    font-size: 2.5rem;
    font-weight: 700;
    color: #0f172a;
    line-height: 1;
    margin-bottom: 0.5rem;
}
.metric-card-delta { font-size: 0.8rem; font-weight: 500; }
.delta-positive { color: #059669; }
.delta-negative { color: #dc2626; }
.delta-neutral  { color: #64748b; }
.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #0f172a;
    margin: 1.75rem 0 0.25rem 0;
}
.section-subheader {
    font-size: 0.8rem;
    color: #94a3b8;
    margin-bottom: 1rem;
}
[data-testid="stDataFrame"] {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
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
</style>
""", unsafe_allow_html=True)

# ---- HEADER — title left, controls right, one unified row ----
now_str = datetime.now().strftime("%d %b %Y, %H:%M")

title_col, btn_col = st.columns([9, 0.4])

with title_col:
    st.markdown(f"""
        <div class="page-header-title">Project Fortify</div>
        <div class="page-header-sub">AI-Powered Infrastructure Health Monitoring &amp; Analytics Platform</div>
    """, unsafe_allow_html=True)

with btn_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↻", help="Refresh", width="stretch"):
        st.cache_data.clear()
        st.rerun()

st.markdown('<hr class="header-divider">', unsafe_allow_html=True)

# ---- DATA ----
vms_summary = api_client.get_vms_summary(token=token)

if vms_summary:
    vms_list = vms_summary.get("vms", [])
    total_vms = len(vms_list)

    online_vms   = sum(1 for vm in vms_list if vm.get("status") == "online")
    offline_vms  = total_vms - online_vms
    healthy_vms  = sum(1 for vm in vms_list if vm.get("health_score") and vm["health_score"] >= 80)
    warning_vms  = sum(1 for vm in vms_list if vm.get("health_score") and 60 <= vm["health_score"] < 80)
    critical_vms = sum(1 for vm in vms_list if vm.get("health_score") and vm["health_score"] < 60)

    online_vm_list = [vm for vm in vms_list if vm.get("health_score") is not None]
    fleet_health   = sum(vm["health_score"] for vm in online_vm_list) / len(online_vm_list) if online_vm_list else 0
    cpu_vals       = [vm["current_cpu"] for vm in vms_list if vm.get("current_cpu") is not None]
    fleet_avg_cpu  = round(sum(cpu_vals) / len(cpu_vals), 1) if cpu_vals else 0
    total_alerts   = sum(vm.get("alert_count", 0) or 0 for vm in vms_list)
    sec_scores     = [vm["security_score"] for vm in vms_list if vm.get("security_score") is not None]
    fleet_security = round(sum(sec_scores) / len(sec_scores)) if sec_scores else 0

    # ---- ROW 1 ----
    st.markdown('<div class="section-header">Fleet Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subheader">Real-time status across all virtual machines</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        oc = "#059669" if online_vms > 0 else "#94a3b8"
        fc = "#dc2626" if offline_vms > 0 else "#94a3b8"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-card-header">Total VMs</div>
            <div class="metric-card-value">{total_vms}</div>
            <div class="metric-card-delta delta-neutral">
                <span style="color:{oc};font-weight:600;">&#x25CF; {online_vms} Online</span>
                &nbsp;
                <span style="color:{fc};font-weight:600;">&#x25CF; {offline_vms} Offline</span>
            </div></div>""", unsafe_allow_html=True)
    with c2:
        hp = (healthy_vms / total_vms * 100) if total_vms > 0 else 0
        st.markdown(f"""<div class="metric-card">
            <div class="metric-card-header">Healthy</div>
            <div class="metric-card-value">{healthy_vms}</div>
            <div class="metric-card-delta delta-positive">&#x2713; {hp:.0f}% of fleet</div>
            </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-card-header">Warning</div>
            <div class="metric-card-value">{warning_vms}</div>
            <div class="metric-card-delta delta-neutral">Needs attention</div>
            </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-card-header">Critical</div>
            <div class="metric-card-value">{critical_vms}</div>
            <div class="metric-card-delta delta-negative">Immediate action required</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- ROW 2 ----
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        vc = "#059669" if fleet_health >= 80 else "#d97706" if fleet_health >= 60 else "#dc2626"
        vt = "Operating within optimal range" if fleet_health >= 80 else "Moderate risk detected" if fleet_health >= 60 else "Immediate attention required"
        vd = "delta-positive" if fleet_health >= 80 else "delta-neutral" if fleet_health >= 60 else "delta-negative"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-card-header">Fleet Health Score</div>
            <div class="metric-card-value" style="color:{vc};">{fleet_health:.0f}<span style="font-size:1rem;color:#94a3b8;">/100</span></div>
            <div class="metric-card-delta {vd}">{vt}</div>
            </div>""", unsafe_allow_html=True)
    with c2:
        sc = "#059669" if fleet_security >= 80 else "#d97706" if fleet_security >= 60 else "#dc2626"
        ss = "Good security standing" if fleet_security >= 80 else "Review security posture" if fleet_security >= 60 else "Security attention needed"
        sd = "delta-positive" if fleet_security >= 80 else "delta-neutral" if fleet_security >= 60 else "delta-negative"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-card-header">Fleet Security Score</div>
            <div class="metric-card-value" style="color:{sc};">{fleet_security}<span style="font-size:1rem;color:#94a3b8;">/100</span></div>
            <div class="metric-card-delta {sd}">{ss}</div>
            </div>""", unsafe_allow_html=True)
    with c3:
        cc = "#dc2626" if fleet_avg_cpu > 85 else "#d97706" if fleet_avg_cpu > 70 else "#059669"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-card-header">Avg CPU Utilization</div>
            <div class="metric-card-value" style="color:{cc};">{fleet_avg_cpu}%</div>
            <div class="metric-card-delta delta-neutral">Across all online VMs</div>
            </div>""", unsafe_allow_html=True)
    with c4:
        ac = "#dc2626" if total_alerts > 10 else "#d97706" if total_alerts > 0 else "#059669"
        at = "Investigate active alerts" if total_alerts > 0 else "No active alerts"
        ad = "delta-negative" if total_alerts > 0 else "delta-positive"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-card-header">Total Active Alerts</div>
            <div class="metric-card-value" style="color:{ac};">{total_alerts}</div>
            <div class="metric-card-delta {ad}">{at}</div>
            </div>""", unsafe_allow_html=True)

    st.divider()

    # ---- RECOMMENDATIONS ----
    st.markdown('<div class="section-header">Recommendations</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subheader">Intelligent insights based on current fleet state</div>', unsafe_allow_html=True)

    recommendations = []
    if critical_vms > 0:
        recommendations.append({"priority": "high", "title": "Critical Health Issues Detected",
            "description": f"{critical_vms} VM(s) with health score below 60. Recommend immediate investigation and resource scaling."})
    if warning_vms > 0:
        recommendations.append({"priority": "medium", "title": "Resource Optimization Opportunity",
            "description": f"{warning_vms} VM(s) showing moderate health (60–80). Consider proactive optimization before issues escalate."})
    if offline_vms > 0:
        recommendations.append({"priority": "medium", "title": "Offline VMs Detected",
            "description": f"{offline_vms} VM(s) currently offline. Verify if intentional or investigate connectivity."})
    if fleet_health >= 80:
        recommendations.append({"priority": "low", "title": "Fleet Operating Normally",
            "description": f"All systems performing within optimal parameters. Fleet health score: {fleet_health:.0f}/100."})
    else:
        recommendations.append({"priority": "low", "title": "Fleet-Wide Performance Trend",
            "description": f"Fleet health at {fleet_health:.0f}/100. Monitor for sustained patterns indicating capacity planning needs."})

    priority_styles = {
        "high":   ("#fee2e2", "#dc2626", "#991b1b"),
        "medium": ("#fef3c7", "#f59e0b", "#92400e"),
        "low":    ("#f0fdf4", "#059669", "#166534"),
    }
    for rec in recommendations[:3]:
        bg, border, fg = priority_styles[rec["priority"]]
        st.markdown(f"""
            <div style="background:{bg};border-left:4px solid {border};padding:0.875rem 1rem;border-radius:0.5rem;margin-bottom:0.6rem;">
                <div style="font-weight:600;color:{fg};font-size:0.875rem;margin-bottom:0.2rem;">{rec['title']}</div>
                <div style="color:{fg};font-size:0.8rem;opacity:0.85;">{rec['description']}</div>
            </div>""", unsafe_allow_html=True)

    st.divider()

    # ---- AI FLEET INTELLIGENCE ----
    st.markdown('<div class="section-header">AI Fleet Intelligence</div>', unsafe_allow_html=True)

    ai_data = api_client.get_ai_insights(token=token)

    if ai_data and not ai_data.get("is_fallback"):
        summary       = ai_data.get("fleet_summary", "—")
        ts            = ai_data.get("analysis_timestamp", "")
        model         = ai_data.get("model_used", "—")
        anomaly_count = len(ai_data.get("anomalies", []))
        rec_count     = len(ai_data.get("recommendations", []))
        pred_count    = len(ai_data.get("predictions", []))

        try:
            dt     = datetime.fromisoformat(ts)
            ts_fmt = dt.strftime("%d %b %Y, %H:%M UTC")
        except Exception:
            ts_fmt = ts

        st.markdown(
            f'<div class="section-subheader">Model: {model} &nbsp;·&nbsp; Last analysed: {ts_fmt}</div>',
            unsafe_allow_html=True
        )

        # Fleet summary narrative
        st.markdown(f"""
            <div style="background:#f8fafc;border-left:4px solid #6366f1;padding:0.875rem 1rem;
                        border-radius:0.5rem;margin-bottom:1rem;">
                <div style="color:#1e3a5f;font-size:0.875rem;line-height:1.65;">{summary}</div>
            </div>
        """, unsafe_allow_html=True)

        # Metric cards — each one links silently to AI Insights
        ai_page   = "ai_insights"
        ac_color  = "#dc2626" if anomaly_count > 0 else "#059669"
        ac_delta  = "delta-negative" if anomaly_count > 0 else "delta-positive"
        ac_sub    = "Requires attention" if anomaly_count > 0 else "None detected"
        rc_color  = "#d97706" if rec_count > 0 else "#059669"
        rc_delta  = "delta-neutral" if rec_count > 0 else "delta-positive"
        rc_sub    = "Action items identified" if rec_count > 0 else "No actions needed"
        pc_color  = "#6366f1" if pred_count > 0 else "#059669"
        pc_sub    = "Trend forecasts available" if pred_count > 0 else "No trends flagged"

        ai_c1, ai_c2, ai_c3 = st.columns(3)
        with ai_c1:
            st.markdown(f"""
                <a href="{ai_page}" target="_self" style="text-decoration:none;">
                <div class="metric-card">
                    <div class="metric-card-header">Anomalies Detected</div>
                    <div class="metric-card-value" style="color:{ac_color};">{anomaly_count}</div>
                    <div class="metric-card-delta {ac_delta}">{ac_sub}</div>
                </div></a>""", unsafe_allow_html=True)
        with ai_c2:
            st.markdown(f"""
                <a href="{ai_page}" target="_self" style="text-decoration:none;">
                <div class="metric-card">
                    <div class="metric-card-header">Recommendations</div>
                    <div class="metric-card-value" style="color:{rc_color};">{rec_count}</div>
                    <div class="metric-card-delta {rc_delta}">{rc_sub}</div>
                </div></a>""", unsafe_allow_html=True)
        with ai_c3:
            st.markdown(f"""
                <a href="{ai_page}" target="_self" style="text-decoration:none;">
                <div class="metric-card">
                    <div class="metric-card-header">Predictions</div>
                    <div class="metric-card-value" style="color:{pc_color};">{pred_count}</div>
                    <div class="metric-card-delta delta-neutral">{pc_sub}</div>
                </div></a>""", unsafe_allow_html=True)

    elif ai_data and ai_data.get("is_fallback"):
        st.markdown('<div class="section-subheader">AI service temporarily unavailable</div>', unsafe_allow_html=True)
        st.markdown("""
            <div style="background:#fef3c7;border-left:4px solid #f59e0b;padding:0.875rem 1rem;border-radius:0.5rem;">
                <div style="font-weight:600;color:#92400e;font-size:0.875rem;margin-bottom:0.2rem;">Service Unavailable</div>
                <div style="color:#78350f;font-size:0.8rem;">Check your Groq API key and run an analysis from the AI Insights page.</div>
            </div>""", unsafe_allow_html=True)

    else:
        st.markdown('<div class="section-subheader">No analysis run yet — visit AI Insights to generate your first fleet analysis</div>', unsafe_allow_html=True)
        ai_c1, ai_c2, ai_c3 = st.columns(3)
        for col, label in zip([ai_c1, ai_c2, ai_c3], ["Anomalies Detected", "Recommendations", "Predictions"]):
            with col:
                st.markdown(f"""
                    <a href="pages/ai_insights.py" target="_self" style="text-decoration:none;">
                    <div class="metric-card">
                        <div class="metric-card-header">{label}</div>
                        <div class="metric-card-value" style="color:#cbd5e1;">—</div>
                        <div class="metric-card-delta delta-neutral">Run analysis to populate</div>
                    </div></a>""", unsafe_allow_html=True)

    st.divider()

    # ---- VM TABLE ----
    st.markdown('<div class="section-header">Virtual Machines</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subheader">Click a row to open VM Health Monitor</div>', unsafe_allow_html=True)

    df_vms = pd.DataFrame(vms_list)

    def get_health_badge(health):
        if health >= 80: return "Healthy"
        elif health >= 60: return "Warning"
        return "Critical"

    df_vms["connectivity"] = df_vms["status"].apply(lambda s: "Online" if s == "online" else "Offline")
    df_vms["health_badge"] = df_vms["health_score"].apply(get_health_badge)
    df_display = df_vms[["vm_id", "name", "connectivity", "health_badge", "current_cpu", "health_score", "alert_count"]].copy()
    df_display["current_cpu"]  = df_display["current_cpu"].fillna(0)
    df_display["health_score"] = df_display["health_score"].fillna(0)
    df_display["alert_count"]  = df_display["alert_count"].fillna(0).astype(int)

    styled_df = df_display.style.map(
        lambda v: "background-color:#dcfce7;color:#166534;font-weight:600;" if v >= 80
                  else "background-color:#fef3c7;color:#92400e;font-weight:600;" if v >= 60
                  else "background-color:#fee2e2;color:#991b1b;font-weight:600;",
        subset=["health_score"]
    )

    event = st.dataframe(
        styled_df,
        column_config={
            "vm_id": st.column_config.TextColumn("VM ID"),
            "name": "Name",
            "connectivity": "Connectivity",
            "health_badge": "Health",
            "current_cpu": st.column_config.ProgressColumn("CPU %", min_value=0, max_value=100, format="%.1f%%"),
            "health_score": st.column_config.NumberColumn("Score", format="%d"),
            "alert_count":  st.column_config.NumberColumn("Alerts", format="%d"),
        },
        width="stretch", hide_index=True, height=400,
        column_order=["vm_id", "name", "connectivity", "health_badge", "current_cpu", "health_score", "alert_count"],
        selection_mode="single-row",
        on_select="rerun",
    )
    st.caption(f"Displaying {len(vms_list)} VMs · Click a row to open VM Health Monitor — {datetime.now().strftime('%H:%M:%S')} | Project Fortify v0.8.0")

    selected_rows = event.selection.rows
    if selected_rows:
        selected_vm_id = df_display.iloc[selected_rows[0]]["vm_id"]
        st.session_state["_nav_vm"] = selected_vm_id
        st.switch_page("pages/vm_health_monitor.py")

else:
    st.markdown("""
        <div class="error-card">
            <strong>Unable to load data</strong>
            Verify the backend is running and refresh the page.
        </div>""", unsafe_allow_html=True)
    st.stop()