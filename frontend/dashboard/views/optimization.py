"""
Cost Optimization - Full implementation.
Resource utilization analysis and rule-based VM optimization recommendations.
"""
import streamlit as st
import plotly.graph_objects as go
import sys
from pathlib import Path
from datetime import datetime

# ---- PATH FIXES ----
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "components"))

# ---- IMPORTS ----
try:
    from api_client import FortifyAPIClient
    from helpers import paginated_table
except ImportError as e:
    st.markdown('<div class="error-card"><strong>Unable to load data</strong>Verify the backend is running and refresh the page.</div>', unsafe_allow_html=True)
    st.stop()

# ---- PAGE CONFIG ----
st.set_page_config(page_title="Cost Optimization", page_icon="📉", layout="wide")

# ---- CSS ----
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
.metric-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    height: 100%;
}
.info-label {
    font-size: 0.75rem;
    color: #64748b;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.35rem;
}
.info-value {
    font-size: 2rem;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.1;
}
.info-delta {
    font-size: 0.8rem;
    margin-top: 0.35rem;
    color: #64748b;
}
.section-header {
    font-size: 1.25rem;
    font-weight: 600;
    color: #0f172a;
    margin: 1.5rem 0 0.5rem 0;
}
.section-subheader {
    font-size: 0.8rem;
    color: #94a3b8;
    margin-bottom: 1rem;
}
.alert-box {
    padding: 0.875rem 1rem;
    border-radius: 0.5rem;
    margin-bottom: 0.75rem;
}
.alert-box-title {
    font-weight: 600;
    margin-bottom: 0.2rem;
    font-size: 0.9rem;
}
.alert-box-text {
    font-size: 0.825rem;
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


# ---- HELPERS ----
def render_card(label, value, delta=None, value_color="#0f172a"):
    st.markdown(f"""
        <div class="metric-card">
            <div class="info-label">{label}</div>
            <div class="info-value" style="color:{value_color};">{value}</div>
            {f'<div class="info-delta">{delta}</div>' if delta else ''}
        </div>
    """, unsafe_allow_html=True)


def utilization_color(pct):
    """Color code a utilization percentage."""
    if pct is None:
        return "#94a3b8"
    if pct > 85:
        return "#dc2626"   # overloaded
    if pct < 20:
        return "#3b82f6"   # wasteful/idle
    return "#059669"       # optimal


def efficiency_zone(cpu, memory):
    """Classify a VM into an efficiency zone based on CPU and memory."""
    if cpu is None or memory is None:
        return "Unknown", "#94a3b8"
    if cpu > 85 or memory > 85:
        return "Overloaded", "#dc2626"
    if cpu < 20 and memory < 40:
        return "Wasteful", "#3b82f6"
    return "Optimal", "#059669"


SEVERITY_STYLES = {
    "critical": ("🔴", "#fee2e2", "#991b1b", "#dc2626"),
    "warning":  ("🟡", "#fef3c7", "#92400e", "#d97706"),
    "info":     ("🟢", "#f0fdf4", "#166534", "#059669"),
}

REC_TYPE_LABELS = {
    "downsize":       "Downsize Instance",
    "scale_up":       "Scale Up",
    "disk_cleanup":   "Disk Cleanup Required",
    "review_offline": "Review Offline VM",
}


# ---- INIT ----
from session import load_token

token = load_token()

api_client = FortifyAPIClient()

title_col, btn_col = st.columns([9, 0.4])
with title_col:
    st.markdown("""
        <div class="page-header-title">Cost Optimization</div>
        <div class="page-header-sub">Resource utilization analysis and actionable recommendations to right-size your VM fleet</div>
    """, unsafe_allow_html=True)
with btn_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↻", help="Refresh", width="stretch"):
        st.cache_data.clear()
        st.rerun()
st.markdown('<hr class="header-divider">', unsafe_allow_html=True)

# ---- FETCH DATA ----
opt_data = api_client.get_optimization_recommendations(token=token)

if not opt_data:
    st.markdown('<div class="error-card"><strong>Unable to load data</strong>Verify the backend is running and refresh the page.</div>', unsafe_allow_html=True)
    st.stop()

fleet = opt_data.get("fleet_summary", {})
recommendations = opt_data.get("recommendations", [])
fleet_vms = fleet.get("vms", [])

# ---- KPI CARDS ----
st.markdown('<div class="section-header">Fleet Utilization Overview</div>', unsafe_allow_html=True)
st.caption("Current resource utilization snapshot across all online VMs")

k1, k2, k3, k4 = st.columns(4)

avg_cpu = fleet.get("avg_cpu", 0)
avg_mem = fleet.get("avg_memory", 0)
over_count = fleet.get("overprovisioned_count", 0)
under_count = fleet.get("underprovisioned_count", 0)

with k1:
    render_card(
        "Avg CPU Utilization",
        f"{avg_cpu}%",
        delta="Fleet average across online VMs",
        value_color=utilization_color(avg_cpu)
    )
with k2:
    render_card(
        "Avg Memory Utilization",
        f"{avg_mem}%",
        delta="Fleet average across online VMs",
        value_color=utilization_color(avg_mem)
    )
with k3:
    render_card(
        "Over-provisioned VMs",
        over_count,
        delta="CPU < 20% — candidates for downsizing",
        value_color="#3b82f6" if over_count > 0 else "#059669"
    )
with k4:
    render_card(
        "Under-provisioned VMs",
        under_count,
        delta="CPU > 85% — candidates for scaling up",
        value_color="#dc2626" if under_count > 0 else "#059669"
    )

st.divider()

# ---- UTILIZATION CHART ----
st.markdown('<div class="section-header">CPU vs Memory Utilization</div>', unsafe_allow_html=True)
st.caption("Each bubble represents a VM — color indicates efficiency zone")

if fleet_vms:
    chart_vms = [vm for vm in fleet_vms if vm.get("current_cpu") is not None and vm.get("current_memory") is not None]

    if chart_vms:
        cpu_vals  = [vm["current_cpu"] for vm in chart_vms]
        mem_vals  = [vm["current_memory"] for vm in chart_vms]
        names     = [f"{vm['vm_id']} — {vm['name']}" for vm in chart_vms]
        zones     = [efficiency_zone(vm["current_cpu"], vm["current_memory"]) for vm in chart_vms]
        colors    = [z[1] for z in zones]
        zone_labels = [z[0] for z in zones]

        fig_scatter = go.Figure()

        # Background zones
        fig_scatter.add_hrect(y0=85, y1=100, fillcolor="#fee2e2", opacity=0.3, line_width=0)
        fig_scatter.add_vrect(x0=85, x1=100, fillcolor="#fee2e2", opacity=0.3, line_width=0)
        fig_scatter.add_hrect(y0=0, y1=40,  fillcolor="#eff6ff", opacity=0.3, line_width=0)
        fig_scatter.add_vrect(x0=0, x1=20,  fillcolor="#eff6ff", opacity=0.3, line_width=0)

        fig_scatter.add_trace(go.Scatter(
            x=cpu_vals,
            y=mem_vals,
            mode="markers+text",
            text=[vm["vm_id"] for vm in chart_vms],
            textposition="top center",
            textfont=dict(size=10, color="#475569"),
            marker=dict(
                size=16,
                color=colors,
                line=dict(color="white", width=2),
                opacity=0.85,
            ),
            customdata=list(zip(names, zone_labels)),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "CPU: %{x:.1f}%<br>"
                "Memory: %{y:.1f}%<br>"
                "Zone: %{customdata[1]}<extra></extra>"
            )
        ))

        # Zone annotations
        fig_scatter.add_annotation(x=10, y=95, text="⚠ Overloaded", showarrow=False,
            font=dict(size=10, color="#991b1b"), bgcolor="#fee2e2", borderpad=3)
        fig_scatter.add_annotation(x=10, y=5,  text="💤 Wasteful", showarrow=False,
            font=dict(size=10, color="#1d4ed8"), bgcolor="#dbeafe", borderpad=3)
        fig_scatter.add_annotation(x=52, y=52, text="✓ Optimal Zone", showarrow=False,
            font=dict(size=11, color="#166534"), bgcolor="#dcfce7", borderpad=3)

        fig_scatter.update_layout(
            height=420,
            margin=dict(l=60, r=40, t=20, b=60),
            xaxis=dict(
                title="CPU Utilization (%)",
                range=[0, 105],
                showgrid=True,
                gridcolor="#f1f5f9",
                zeroline=False
            ),
            yaxis=dict(
                title="Memory Utilization (%)",
                range=[0, 105],
                showgrid=True,
                gridcolor="#f1f5f9",
                zeroline=False
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Inter, sans-serif", size=12),
            showlegend=False
        )
        st.plotly_chart(fig_scatter, width="stretch")
    else:
        st.info("No utilization data available for chart.")

st.divider()

# ---- RECOMMENDATIONS ----
st.markdown('<div class="section-header">Optimization Recommendations</div>', unsafe_allow_html=True)
st.caption(f"{len(recommendations)} recommendation{'s' if len(recommendations) != 1 else ''} — sorted by severity")

if recommendations:
    # Summary counts
    rc1, rc2, rc3 = st.columns(3)
    critical_recs = sum(1 for r in recommendations if r["severity"] == "critical")
    warning_recs  = sum(1 for r in recommendations if r["severity"] == "warning")
    info_recs     = sum(1 for r in recommendations if r["severity"] == "info")

    with rc1:
        render_card("Critical", critical_recs, value_color="#dc2626" if critical_recs > 0 else "#059669")
    with rc2:
        render_card("Warnings", warning_recs, value_color="#d97706" if warning_recs > 0 else "#059669")
    with rc3:
        render_card("Info", info_recs, value_color="#3b82f6")

    st.markdown("<br>", unsafe_allow_html=True)

    # Render each recommendation as an alert box
    for rec in recommendations:
        icon, bg, fg, border = SEVERITY_STYLES.get(rec["severity"], ("⚪", "#f8fafc", "#475569", "#94a3b8"))
        rec_type = REC_TYPE_LABELS.get(rec["recommendation_type"], rec["recommendation_type"])
        vm_link = f"/vm_health_monitor?vm={rec['vm_id']}"

        st.markdown(f"""
            <div class="alert-box" style="background:{bg};border-left:4px solid {border};">
                <div class="alert-box-title" style="color:{fg};">
                    {icon} {rec_type} — <a href="{vm_link}" style="color:{fg};">{rec['vm_id']} ({rec['vm_name']})</a>
                </div>
                <div class="alert-box-text" style="color:{fg};">{rec['reason']}</div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.markdown("""
        <div style="background:#f0fdf4;border-left:4px solid #059669;padding:1rem;border-radius:0.5rem;">
            <strong style="color:#166534;">✓ No optimization actions needed</strong><br>
            <span style="color:#14532d;font-size:0.875rem;">All VMs are operating within optimal resource utilization thresholds.</span>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# ---- VM UTILIZATION TABLE ----
st.markdown('<div class="section-header">VM Utilization Breakdown</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subheader">Full resource snapshot per VM</div>', unsafe_allow_html=True)

if fleet_vms:
    rows = []
    for vm in fleet_vms:
        vm_id  = vm.get("vm_id", "—")
        name   = vm.get("name", "—")
        status = vm.get("status", "offline")
        cpu    = vm.get("current_cpu")
        mem    = vm.get("current_memory")
        disk   = vm.get("current_disk")
        zone, _ = efficiency_zone(cpu, mem)

        rec_types = [
            REC_TYPE_LABELS.get(r["recommendation_type"], r["recommendation_type"])
            for r in recommendations if r["vm_id"] == vm_id
        ]
        rec_label = ", ".join(rec_types) if rec_types else "—"

        s_color = "#166534" if status == "online" else "#991b1b"
        s_bg    = "#dcfce7" if status == "online" else "#fee2e2"
        s_label = "Online"  if status == "online" else "Offline"

        cpu_val = round(cpu, 1) if cpu is not None else None
        if cpu_val is None:
            cpu_str, cpu_color = "—", "#94a3b8"
        elif cpu_val > 85:
            cpu_str, cpu_color = f"{cpu_val}%", "#991b1b"
        elif cpu_val < 20:
            cpu_str, cpu_color = f"{cpu_val}%", "#1d4ed8"
        else:
            cpu_str, cpu_color = f"{cpu_val}%", "#166534"

        mem_str  = f"{round(mem,  1)}%" if mem  is not None else "—"
        disk_str = f"{round(disk, 1)}%" if disk is not None else "—"

        if zone == "Overloaded":
            z_color, z_bg = "#991b1b", "#fee2e2"
        elif zone == "Wasteful":
            z_color, z_bg = "#1d4ed8", "#dbeafe"
        elif zone == "Optimal":
            z_color, z_bg = "#166534", "#dcfce7"
        else:
            z_color, z_bg = "#475569", "#f1f5f9"

        rows.append(f"""
        <tr style="border-bottom:1px solid #f1f5f9;">
            <td style="padding:0.65rem 1rem;font-weight:600;font-family:monospace;color:#0f172a;">{vm_id}</td>
            <td style="padding:0.65rem 1rem;color:#0f172a;">{name}</td>
            <td style="padding:0.65rem 1rem;">
                <span style="background:{s_bg};color:{s_color};padding:2px 10px;border-radius:9999px;font-size:0.75rem;font-weight:600;">{s_label}</span>
            </td>
            <td style="padding:0.65rem 1rem;font-weight:600;color:{cpu_color};">{cpu_str}</td>
            <td style="padding:0.65rem 1rem;color:#334155;">{mem_str}</td>
            <td style="padding:0.65rem 1rem;color:#334155;">{disk_str}</td>
            <td style="padding:0.65rem 1rem;">
                <span style="background:{z_bg};color:{z_color};padding:2px 10px;border-radius:9999px;font-size:0.75rem;font-weight:600;">{zone}</span>
            </td>
            <td style="padding:0.65rem 1rem;color:#334155;font-size:0.8rem;">{rec_label}</td>
        </tr>""")

    th = "padding:0.6rem 1rem;color:#64748b;font-weight:600;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em;text-align:left;background:#f8fafc;border-bottom:2px solid #e2e8f0;"
    thead_html = f"""
        <thead>
            <tr>
                <th style="{th}">VM ID</th>
                <th style="{th}">Name</th>
                <th style="{th}">Status</th>
                <th style="{th}">CPU %</th>
                <th style="{th}">Memory %</th>
                <th style="{th}">Disk %</th>
                <th style="{th}">Zone</th>
                <th style="{th}">Action</th>
            </tr>
        </thead>"""
    paginated_table(rows, thead_html, key="optimization_vms", page_size=10)

st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Project Fortify v1.1.0")