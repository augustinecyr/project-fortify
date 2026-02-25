"""
Project Fortify - Home Dashboard
Modern card-based system overview with VM fleet monitoring.
Enhanced with donut chart and improved table columns.
Now uses last_seen for connectivity and health_score for health badge.
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timezone, timedelta
import plotly.graph_objects as go

# Add utils to path (needed for API client)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))

from api_client import FortifyAPIClient

# Initialize API client
api_client = FortifyAPIClient()

# Advanced CSS for modern card-based design
st.markdown("""
    <style>
    /* Global Layout */
    .main-header {
        font-size: 2.25rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.25rem;
        letter-spacing: -0.75px;
    }
    .main-subheader {
        font-size: 1rem;
        color: #64748b;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    /* Card Styles */
    .metric-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease;
        margin-bottom: 1rem;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .metric-card:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-color: #cbd5e1;
    }
    .metric-card-header {
        font-size: 0.875rem;
        font-weight: 500;
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
    .metric-card-delta {
        font-size: 0.875rem;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
    }
    .delta-positive {
        color: #059669;
    }
    .delta-negative {
        color: #dc2626;
    }
    .delta-neutral {
        color: #64748b;
    }
    
    /* Status Badge */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .status-healthy {
        background-color: #dcfce7;
        color: #166534;
    }
    .status-warning {
        background-color: #fef3c7;
        color: #92400e;
    }
    .status-critical {
        background-color: #fee2e2;
        color: #991b1b;
    }
    .status-offline {
        background-color: #f1f5f9;
        color: #475569;
    }
    
    /* Section Headers */
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #0f172a;
        margin: 2rem 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .section-subheader {
        font-size: 0.875rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    
    /* Fleet Health Score Card - Now same size as others */
    .health-score-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease;
        margin-bottom: 1rem;
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    .health-score-card:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-color: #cbd5e1;
    }
    
    /* Table Styling */
    [data-testid="stDataFrame"] {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
    }
    
    /* Streamlit Metric Override */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #0f172a;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.875rem;
        color: #64748b;
        font-weight: 500;
    }
    
    /* Alert Box */
    .alert-box {
        background-color: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .alert-box-title {
        font-weight: 600;
        color: #92400e;
        margin-bottom: 0.25rem;
    }
    .alert-box-text {
        color: #78350f;
        font-size: 0.875rem;
    }
    
    /* Health Value Badge */
    .health-value {
        font-weight: 600;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.875rem;
    }
    .health-good {
        background-color: #dcfce7;
        color: #166534;
    }
    .health-warning {
        background-color: #fef3c7;
        color: #92400e;
    }
    .health-critical {
        background-color: #fee2e2;
        color: #991b1b;
    }
    
    </style>
""", unsafe_allow_html=True)

# ----- HEADER -----
st.markdown('<p class="main-header">Project Fortify / Dashboard</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subheader">AI-Powered Infrastructure Health Monitoring & Analytics Platform</p>', unsafe_allow_html=True)

# Get VMs summary
with st.spinner("Loading fleet data..."):
    vms_summary = api_client.get_vms_summary()

if vms_summary:
    vms_list = vms_summary.get("vms", [])
    
    # Calculate fleet metrics using actual VM list data
    total_vms = len(vms_list)

    def is_vm_online(last_seen_str):
        """Return True if VM has sent metrics within the last 5 minutes."""
        if not last_seen_str:
            return False
        try:
            if last_seen_str.endswith('Z'):
                last_seen_str = last_seen_str.replace('Z', '+00:00')
            last_seen = datetime.fromisoformat(last_seen_str)
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return (now - last_seen) <= timedelta(minutes=5)
        except Exception:
            return False

    online_vms = sum(1 for vm in vms_list if is_vm_online(vm.get("last_seen")))
    offline_vms = total_vms - online_vms
    
    # Calculate health distribution using actual health_score field
    healthy_vms = sum(1 for vm in vms_list if vm.get("health_score") and vm["health_score"] >= 80)
    warning_vms = sum(1 for vm in vms_list if vm.get("health_score") and 60 <= vm["health_score"] < 80)
    critical_vms = sum(1 for vm in vms_list if vm.get("health_score") and vm["health_score"] < 60)
    
    # Calculate fleet health score from actual health scores
    online_vm_list = [vm for vm in vms_list if vm.get("health_score") is not None]
    if online_vm_list:
        fleet_health = sum(vm["health_score"] for vm in online_vm_list) / len(online_vm_list)
    else:
        fleet_health = 0
    
    # ============= FLEET OVERVIEW CARDS =============
    st.markdown('<div class="section-header">📊 Fleet Overview</div>', unsafe_allow_html=True)
    st.markdown('<p class="section-subheader">Real-time status across all virtual machines</p>', unsafe_allow_html=True)
    
    # Top row: Key metrics (4 equal cards)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        online_color = "#059669" if online_vms > 0 else "#94a3b8"
        offline_color = "#dc2626" if offline_vms > 0 else "#94a3b8"

        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-header">Total VMs</div>
                <div class="metric-card-value">{total_vms}</div>
                <div class="metric-card-delta delta-neutral">
                    <span style="color:{online_color}; font-weight:600;">
                        ● {online_vms} Online
                    </span>
                    &nbsp;&nbsp;
                    <span style="color:{offline_color}; font-weight:600;">
                        ● {offline_vms} Offline
                    </span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        health_percentage = (healthy_vms / total_vms * 100) if total_vms > 0 else 0
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-header">Healthy</div>
                <div class="metric-card-value">{healthy_vms}</div>
                <div class="metric-card-delta delta-positive">
                    ✓ {health_percentage:.0f}% of fleet
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-header">Warning</div>
                <div class="metric-card-value">{warning_vms}</div>
                <div class="metric-card-delta delta-neutral">
                    ⚠ Needs attention
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-header">Critical</div>
                <div class="metric-card-value">{critical_vms}</div>
                <div class="metric-card-delta delta-negative">
                    ⚠ Immediate action required
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Second row: 3 metrics + Fleet Health Score with Donut Chart
    col1, col2, col3 = st.columns(3)
    
    # Fleet Health Score - Same style as other cards
    with col1:

        # Determine health color
        if fleet_health >= 80:
            value_color = "#059669"   # green
            status_text = "✓ Operating within optimal range"
            delta_class = "delta-positive"
        elif fleet_health >= 60:
            value_color = "#d97706"   # orange
            status_text = "⚠ Moderate risk detected"
            delta_class = "delta-neutral"
        else:
            value_color = "#dc2626"   # red
            status_text = "⚠ Immediate attention required"
            delta_class = "delta-negative"

        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-header">Fleet Health Score</div>
                <div class="metric-card-value" style="color:{value_color};">
                    {fleet_health:.0f}
                    <span style="font-size:1rem; color:#94a3b8;">/100</span>
                </div>
                <div class="metric-card-delta {delta_class}">
                    {status_text}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
    
    # ============= VM TABLE WITH HEALTH AND CONNECTIVITY =============
    st.markdown('<div class="section-header">💻 Virtual Machines</div>', unsafe_allow_html=True)
    st.markdown('<p class="section-subheader">Click on a VM ID to view detailed health metrics</p>', unsafe_allow_html=True)

    # Prepare dataframe
    df_vms = pd.DataFrame(vms_list)

    # Define connectivity threshold (5 minutes)
    offline_threshold = timedelta(minutes=5)
    now = datetime.now(timezone.utc)

    def get_connectivity(last_seen_str):
        """Return connectivity badge based on last_seen timestamp."""
        if not last_seen_str:
            return "🔴 Offline"
        try:
            # Parse ISO string, convert 'Z' to UTC offset
            if last_seen_str.endswith('Z'):
                last_seen_str = last_seen_str.replace('Z', '+00:00')
            last_seen = datetime.fromisoformat(last_seen_str)
            
            # Ensure last_seen is timezone-aware (assume UTC if naive)
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            if now - last_seen > timedelta(minutes=5):
                return "🔴 Offline"
            else:
                return "🟢 Online"
        except Exception as e:
            # Optionally log the error for debugging
            # st.write(f"Debug: {e}")  # uncomment to see errors
            return "🔴 Offline"

    def get_health_badge(health):
        """Return health badge based on health score."""
        if health >= 80:
            return "🟢 Healthy"
        elif health >= 60:
            return "🟡 Warning"
        else:
            return "🔴 Critical"

    # Apply the functions
    df_vms["connectivity"] = df_vms["last_seen"].apply(get_connectivity)
    df_vms["health_badge"] = df_vms["health_score"].apply(get_health_badge)

    # Create display dataframe with the new columns
    df_display = df_vms[["vm_id", "name", "connectivity", "health_badge", "current_cpu", "health_score", "alert_count"]].copy()

    # Fill NaN values
    df_display["current_cpu"] = df_display["current_cpu"].fillna(0)
    df_display["health_score"] = df_display["health_score"].fillna(0)
    df_display["alert_count"] = df_display["alert_count"].fillna(0).astype(int)

    # Replace vm_id column with the full URL for linking
    df_display["vm_id"] = df_display["vm_id"].apply(
        lambda x: f"/vm_health_monitor?vm={x}"
    )

    # Configure columns
    column_config = {
        "vm_id": st.column_config.LinkColumn(
            "VM ID",
            help="Click to view detailed health metrics",
            display_text=r"vm=([^&]+)",
        ),
        "name": "Name",
        "connectivity": "Connectivity",
        "health_badge": "Health",
        "current_cpu": st.column_config.ProgressColumn(
            "Current CPU",
            help="Current CPU usage percentage",
            min_value=0,
            max_value=100,
            format="%.1f%%"
        ),
        "health_score": st.column_config.NumberColumn(
            "Score",
            help="Overall health score (0-100)",
            format="%d"
        ),
        "alert_count": st.column_config.NumberColumn(
            "Alerts",
            help="Number of active alerts",
            format="%d"
        ),
    }

    # Apply styling to health_score column
    def style_health(val):
        if val >= 80:
            return 'background-color: #dcfce7; color: #166534; font-weight: 600;'
        elif val >= 60:
            return 'background-color: #fef3c7; color: #92400e; font-weight: 600;'
        else:
            return 'background-color: #fee2e2; color: #991b1b; font-weight: 600;'

    styled_df = df_display.style.map(style_health, subset=['health_score'])

    # Display the interactive dataframe
    st.dataframe(
        styled_df,
        column_config=column_config,
        width='stretch',
        hide_index=True,
        height=400,
        column_order=["vm_id", "name", "connectivity", "health_badge", "current_cpu", "health_score", "alert_count"]
    )

    # Table footer
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    st.caption(f"📊 Displaying {len(vms_list)} virtual machines | 🔄 Last updated: {current_time}")
        # ============= AI RECOMMENDATIONS =============
    st.markdown('<div class="section-header">🤖 AI Recommendations</div>', unsafe_allow_html=True)
    st.markdown('<p class="section-subheader">Intelligent insights and proactive suggestions</p>', unsafe_allow_html=True)
    
    # Generate AI recommendations based on current state
    recommendations = []
    
    if critical_vms > 0:
        recommendations.append({
            "priority": "high",
            "title": "Critical Health Issues Detected",
            "description": f"{critical_vms} VM(s) with health score <60. Recommend immediate investigation and resource scaling."
        })
    
    if warning_vms > 0:
        recommendations.append({
            "priority": "medium",
            "title": "Resource Optimization Opportunity",
            "description": f"{warning_vms} VM(s) showing moderate health (60-80). Consider proactive optimization before issues escalate."
        })
    
    if offline_vms > 0:
        recommendations.append({
            "priority": "medium",
            "title": "Offline VMs Detected",
            "description": f"{offline_vms} VM(s) currently offline. Verify if this is intentional or investigate connectivity issues."
        })
    
    if fleet_health >= 80:
        recommendations.append({
            "priority": "low",
            "title": "Fleet Operating Normally",
            "description": f"All systems performing within optimal parameters. Fleet health score: {fleet_health:.0f}/100."
        })
    else:
        recommendations.append({
            "priority": "low",
            "title": "Fleet-Wide Performance Trend",
            "description": f"Fleet health at {fleet_health:.0f}/100. Monitor for sustained patterns that may indicate capacity planning needs."
        })
    
    # Display recommendations
    for rec in recommendations[:3]:  # Show top 3
        icon = "🔴" if rec["priority"] == "high" else "🟡" if rec["priority"] == "medium" else "🟢"
        st.markdown(f"""
            <div class="alert-box">
                <div class="alert-box-title">{icon} {rec['title']}</div>
                <div class="alert-box-text">{rec['description']}</div>
            </div>
        """, unsafe_allow_html=True)

else:
    # Error state
    st.markdown("""
        <div class="alert-box">
            <div class="alert-box-title">⚠️ Connection Error</div>
            <div class="alert-box-text">Unable to load VM data. Please check API connection and try again.</div>
        </div>
    """, unsafe_allow_html=True)

# Footer
st.divider()
st.caption("⚡ Project Fortify - AI-Assisted Infrastructure Monitoring | Version 0.2.1 | Built with Streamlit")