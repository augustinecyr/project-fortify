"""
Security Posture - Full implementation.
Fleet-wide security analytics: KPI cards, score distribution, patch lag, per-VM table.
"""
import streamlit as st
import pandas as pd
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
except ImportError as e:
    st.error(f"Import failed: {e}. Make sure all component files exist.")
    st.stop()

# ---- PAGE CONFIG ----
st.set_page_config(page_title="Security Posture", page_icon="🔒", layout="wide")

# ---- CSS (matches existing metric-card design system) ----
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


def score_color(score):
    if score is None:
        return "#94a3b8"
    if score >= 80:
        return "#059669"
    if score >= 60:
        return "#d97706"
    return "#dc2626"


def tier_badge(tier):
    colors = {
        "high":   ("🟢", "#dcfce7", "#166534"),
        "medium": ("🟡", "#fef3c7", "#92400e"),
        "low":    ("🔴", "#fee2e2", "#991b1b"),
    }
    icon, bg, fg = colors.get(tier, ("⚪", "#f1f5f9", "#475569"))
    return f'<span style="background:{bg};color:{fg};padding:2px 10px;border-radius:9999px;font-size:0.75rem;font-weight:600;">{icon} {tier.capitalize()}</span>'


def bool_icon(val):
    if val is True:
        return "✅"
    if val is False:
        return "❌"
    return "—"


# ---- INIT ----
api_client = FortifyAPIClient()

title_col, btn_col = st.columns([9, 0.4])
with title_col:
    st.markdown("""
        <div class="page-header-title">Security Posture</div>
        <div class="page-header-sub">Fleet-wide security analytics — vulnerability tracking, patch compliance, and risk distribution</div>
    """, unsafe_allow_html=True)
with btn_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↻", help="Refresh", width="stretch"):
        st.cache_data.clear()
        st.rerun()
st.markdown('<hr class="header-divider">', unsafe_allow_html=True)

# ---- FETCH DATA ----
with st.spinner("Loading security data..."):
    security_data = api_client.get_security_summary()

if not security_data:
    st.markdown("""
        <div style="background:#fee2e2;border-left:4px solid #ef4444;padding:1rem;border-radius:0.5rem;">
            <strong style="color:#991b1b;">⚠️ Unable to load security data</strong><br>
            <span style="color:#7f1d1d;font-size:0.875rem;">Check that the API is running at localhost:8000</span>
        </div>
    """, unsafe_allow_html=True)
    st.stop()

vms = security_data.get("vms", [])
patch_lag = security_data.get("patch_lag_distribution", {})

# ---- KPI CARDS ----
st.markdown('<div class="section-header">Fleet Security Overview</div>', unsafe_allow_html=True)
st.caption("Aggregated security metrics across all virtual machines")

k1, k2, k3, k4 = st.columns(4)

avg_score = security_data.get("avg_security_score", 0)
with k1:
    render_card(
        "Avg Security Score",
        f"{avg_score}/100",
        delta="✓ Good standing" if avg_score >= 80 else "⚠ Needs improvement",
        value_color=score_color(avg_score)
    )
with k2:
    total_vulns = security_data.get("total_open_vulnerabilities", 0)
    render_card("Open Vulnerabilities", total_vulns, delta="Across all VMs")

with k3:
    critical_vulns = security_data.get("total_critical_vulnerabilities", 0)
    render_card(
        "Critical Vulnerabilities",
        critical_vulns,
        delta="Require immediate attention",
        value_color="#dc2626" if critical_vulns > 0 else "#059669"
    )
with k4:
    fw_disabled = security_data.get("firewall_disabled_count", 0)
    render_card(
        "Firewall Disabled",
        fw_disabled,
        delta="VMs with no firewall active",
        value_color="#dc2626" if fw_disabled > 0 else "#059669"
    )

st.divider()

# ---- CHARTS ROW ----
st.markdown('<div class="section-header">Risk Distribution</div>', unsafe_allow_html=True)
chart_col1, chart_col2 = st.columns(2)

# Chart 1 — Security Score Tiers (horizontal bar)
with chart_col1:
    st.markdown("**Security Score Tiers**")

    tier_labels = ["Low (<60)", "Medium (60-79)", "High (>=80)"]
    tier_counts = [0, 0, 0]
    tier_colors = ["#dc2626", "#d97706", "#059669"]

    for vm in vms:
        tier = vm.get("score_tier", "low")
        if tier == "high":
            tier_counts[2] += 1
        elif tier == "medium":
            tier_counts[1] += 1
        else:
            tier_counts[0] += 1

    fig_tiers = go.Figure(go.Bar(
        x=tier_counts,
        y=tier_labels,
        orientation="h",
        marker_color=tier_colors,
        text=[f"{v} VM{'s' if v != 1 else ''}" for v in tier_counts],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x} VMs<extra></extra>"
    ))
    fig_tiers.update_layout(
        height=320,
        margin=dict(l=20, r=80, t=20, b=40),
        xaxis=dict(
            title="Number of VMs",
            showgrid=True,
            gridcolor="#f1f5f9",
            zeroline=False,
            rangemode="nonnegative",
            range=[0, max(tier_counts) * 1.4 if max(tier_counts) > 0 else 5]
        ),
        yaxis=dict(showgrid=False),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=13)
    )
    st.plotly_chart(fig_tiers, width='stretch')
    
# Chart 2 — Patch Lag Distribution (bar)
with chart_col2:
    st.markdown("**Days Since Last Patch**")

    lag_labels = ["0–7 days", "8–30 days", "31–90 days", "90+ days"]
    lag_values = [
        patch_lag.get("0_7_days", 0),
        patch_lag.get("8_30_days", 0),
        patch_lag.get("31_90_days", 0),
        patch_lag.get("90_plus_days", 0),
    ]
    lag_colors = ["#059669", "#3b82f6", "#d97706", "#dc2626"]

    fig_bar = go.Figure(go.Bar(
        x=lag_labels,
        y=lag_values,
        marker_color=lag_colors,
        text=lag_values,
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y} VMs<extra></extra>"
    ))
    fig_bar.update_layout(
        height=320,
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis=dict(title="Patch Age", showgrid=False),
        yaxis=dict(
            title="Number of VMs",
            showgrid=True,
            gridcolor="#f1f5f9",
            zeroline=False,
            rangemode="nonnegative",
            range=[0, max(lag_values) * 1.3 if max(lag_values) > 0 else 5]
        ),      
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=12)
    )
    st.plotly_chart(fig_bar, width='stretch')

st.divider()

# ---- PER-VM SECURITY TABLE ----
st.markdown('<div class="section-header">VM Security Details</div>', unsafe_allow_html=True)
st.caption("Sorted by security score — lowest first. Click VM ID to view full health details.")

if vms:
    rows = []
    for vm in vms:  # already sorted worst-first by API
        rows.append({
            "vm_id": f"/vm_health_monitor?vm={vm['vm_id']}",
            "name": vm.get("name", "—"),
            "security_score": vm.get("security_score") or 0,
            "open_vulns": vm.get("open_vulnerabilities", 0),
            "critical_vulns": vm.get("critical_vulnerabilities", 0),
            "firewall": vm.get("firewall_enabled"),
            "ssh_key": vm.get("ssh_key_auth"),
            "encryption": vm.get("disk_encryption"),
            "compliance": vm.get("compliance_score") or "—",
            "last_patch": vm.get("last_patch_date", "—"),
            "days_since_patch": vm.get("days_since_patch"),
        })

    df = pd.DataFrame(rows)

    # Format last_patch to date only
    def fmt_date(val):
        if not val or val == "—":
            return "—"
        try:
            return pd.to_datetime(val).strftime("%Y-%m-%d")
        except Exception:
            return str(val)

    df["last_patch"] = df["last_patch"].apply(fmt_date)

    # Style the security_score column
    def style_score(val):
        if val >= 80:
            return "background-color:#dcfce7;color:#166534;font-weight:600;"
        elif val >= 60:
            return "background-color:#fef3c7;color:#92400e;font-weight:600;"
        return "background-color:#fee2e2;color:#991b1b;font-weight:600;"

    styled_df = df.style.map(style_score, subset=["security_score"])

    st.dataframe(
        styled_df,
        column_config={
            "vm_id": st.column_config.LinkColumn(
                "VM ID",
                help="Click to view full VM health details",
                display_text=r"vm=([^&]+)"
            ),
            "name": "Name",
            "security_score": st.column_config.NumberColumn("Security Score", format="%d"),
            "open_vulns": st.column_config.NumberColumn("Open Vulns", format="%d"),
            "critical_vulns": st.column_config.NumberColumn("Critical Vulns", format="%d"),
            "firewall": st.column_config.CheckboxColumn("Firewall"),
            "ssh_key": st.column_config.CheckboxColumn("SSH Key Auth"),
            "encryption": st.column_config.CheckboxColumn("Disk Encryption"),
            "compliance": "Compliance",
            "last_patch": "Last Patch",
            "days_since_patch": st.column_config.NumberColumn("Days Since Patch", format="%d days"),
        },
        hide_index=True,
        width='stretch',
        height=450,
        column_order=["vm_id", "name", "security_score", "open_vulns", "critical_vulns",
                      "firewall", "ssh_key", "encryption", "compliance", "last_patch", "days_since_patch"]
    )
else:
    st.info("No VM security data available.")

st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Project Fortify v0.5.0")