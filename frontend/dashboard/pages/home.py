"""
Project Fortify - Home Dashboard
Modern card-based system overview with VM fleet monitoring.
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

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
    
    /* Fleet Score Card */
    .score-card {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
        border-radius: 12px;
        padding: 2rem;
        color: white;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .score-card-title {
        font-size: 0.875rem;
        font-weight: 500;
        opacity: 0.9;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .score-card-value {
        font-size: 3.5rem;
        font-weight: 800;
        line-height: 1;
        margin-bottom: 0.5rem;
    }
    .score-card-label {
        font-size: 0.875rem;
        opacity: 0.8;
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
    
    /* Grid Layout */
    .grid-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
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
    </style>
""", unsafe_allow_html=True)

# ----- HEADER (cleaned, no emojis) -----
st.markdown('<p class="main-header">Project Fortify / Dashboard</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subheader">AI-Powered Infrastructure Health Monitoring & Analytics Platform</p>', unsafe_allow_html=True)

# Get VMs summary
with st.spinner("🔄 Loading fleet data..."):
    vms_summary = api_client.get_vms_summary()

if vms_summary:
    vms_list = vms_summary.get("vms", [])
    
    # Calculate fleet metrics
    total_vms = vms_summary.get("total", 0)
    online_vms = vms_summary.get("online", 0)
    offline_vms = vms_summary.get("offline", 0)
    
    # Calculate health distribution
    healthy_vms = sum(1 for vm in vms_list if vm.get("status") == "online" and vm.get("avg_cpu_24h", 0) < 70)
    warning_vms = sum(1 for vm in vms_list if vm.get("status") == "online" and 70 <= vm.get("avg_cpu_24h", 0) < 85)
    critical_vms = sum(1 for vm in vms_list if vm.get("status") == "online" and vm.get("avg_cpu_24h", 0) >= 85)
    
    # Calculate fleet health score (0-100)
    online_vm_list = [vm for vm in vms_list if vm.get("avg_cpu_24h") is not None]
    if online_vm_list:
        avg_cpu = sum(vm["avg_cpu_24h"] for vm in online_vm_list) / len(online_vm_list)
        # Fleet health: inversely proportional to CPU usage
        fleet_health = max(0, min(100, 100 - (avg_cpu * 0.8)))
    else:
        fleet_health = 0
        avg_cpu = 0
    
    # ============= FLEET OVERVIEW CARDS =============
    st.markdown('<div class="section-header">📊 Fleet Overview</div>', unsafe_allow_html=True)
    st.markdown('<p class="section-subheader">Real-time status across all virtual machines</p>', unsafe_allow_html=True)
    
    # Top row: Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-header">Total VMs</div>
                <div class="metric-card-value">{total_vms}</div>
                <div class="metric-card-delta delta-neutral">
                    Across fleet
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
                    ⚠ Immediate action
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Second row: Performance metrics and Fleet Health Score
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1.5])
    
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-header">Online VMs</div>
                <div class="metric-card-value">{online_vms}</div>
                <div class="metric-card-delta delta-positive">
                    ↑ Active now
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-header">Offline VMs</div>
                <div class="metric-card-value">{offline_vms}</div>
                <div class="metric-card-delta delta-{'negative' if offline_vms > 0 else 'neutral'}">
                    ↓ Inactive
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-header">Avg CPU 24h</div>
                <div class="metric-card-value">{avg_cpu:.1f}%</div>
                <div class="metric-card-delta delta-{'negative' if avg_cpu > 70 else 'positive'}">
                    {'↑ High load' if avg_cpu > 70 else '✓ Normal'}
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="score-card">
                <div class="score-card-title">Fleet Health Score</div>
                <div class="score-card-value">{fleet_health:.0f}</div>
                <div class="score-card-label">Out of 100 • Updated just now</div>
            </div>
        """, unsafe_allow_html=True)
    
    # ============= AI RECOMMENDATIONS =============
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">🤖 AI Recommendations</div>', unsafe_allow_html=True)
    st.markdown('<p class="section-subheader">Intelligent insights and proactive suggestions</p>', unsafe_allow_html=True)
    
    # Generate AI recommendations based on current state
    recommendations = []
    
    if critical_vms > 0:
        recommendations.append({
            "priority": "high",
            "title": "Critical CPU Load Detected",
            "description": f"{critical_vms} VM(s) experiencing CPU usage ≥85%. Recommend immediate resource scaling or workload redistribution."
        })
    
    if warning_vms > 0:
        recommendations.append({
            "priority": "medium",
            "title": "Resource Optimization Opportunity",
            "description": f"{warning_vms} VM(s) showing elevated CPU usage (70-85%). Consider proactive scaling before reaching critical threshold."
        })
    
    if offline_vms > 0:
        recommendations.append({
            "priority": "medium",
            "title": "Offline VMs Detected",
            "description": f"{offline_vms} VM(s) currently offline. Verify if this is intentional or investigate connectivity issues."
        })
    
    if avg_cpu > 60:
        recommendations.append({
            "priority": "low",
            "title": "Fleet-Wide Performance Trend",
            "description": f"Fleet average CPU at {avg_cpu:.1f}%. Monitor for sustained high load patterns that may indicate capacity planning needs."
        })
    else:
        recommendations.append({
            "priority": "low",
            "title": "Fleet Operating Normally",
            "description": f"All systems performing within optimal parameters. Fleet health score: {fleet_health:.0f}/100."
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
    
    # ============= VM TABLE WITH PROGRESS BARS & CLICKABLE LINKS =============
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">💻 Virtual Machines</div>', unsafe_allow_html=True)
    st.markdown('<p class="section-subheader">Click on a VM ID to view detailed health metrics</p>', unsafe_allow_html=True)
    
    # Prepare dataframe with numeric values (not formatted strings)
    df_vms = pd.DataFrame(vms_list)
    
    # Add status column (as string for display)
    def get_status(row):
        if row.get("status") == "offline":
            return "🔴 Offline"
        cpu = row.get("avg_cpu_24h", 0)
        if cpu >= 85:
            return "🔴 Critical"
        elif cpu >= 70:
            return "🟡 Warning"
        else:
            return "🟢 Healthy"
    
    df_vms["health_status"] = df_vms.apply(get_status, axis=1)
    
    # Create display dataframe with numeric columns
    df_display = df_vms[["vm_id", "name", "health_status", "current_cpu", "avg_cpu_24h", "metric_count_24h"]].copy()
    
    # Fill NaN values for progress bars (use 0 for CPU)
    df_display["current_cpu"] = df_display["current_cpu"].fillna(0)
    df_display["avg_cpu_24h"] = df_display["avg_cpu_24h"].fillna(0)
    
    # ---- CORRECTED LINK HANDLING ----
    # Replace vm_id column with the full URL
    df_display["vm_id"] = df_display["vm_id"].apply(
        lambda x: f"/vm_health_monitor?vm={x}"
    )
    
    # Configure columns with LinkColumn and a regex display_text to extract the VM ID
    column_config = {
        "vm_id": st.column_config.LinkColumn(
            "VM ID",
            help="Click to view detailed health metrics",
            # Use regex capture group to display just the VM ID part (e.g., vm-001)
            display_text=r"vm=([^&]+)",
        ),
        "name": "Name",
        "health_status": "Status",
        "current_cpu": st.column_config.ProgressColumn(
            "Current CPU",
            help="Current CPU usage percentage",
            min_value=0,
            max_value=100,
            format="%.1f%%"
        ),
        "avg_cpu_24h": st.column_config.ProgressColumn(
            "Avg CPU (24h)",
            help="Average CPU usage over last 24 hours",
            min_value=0,
            max_value=100,
            format="%.1f%%"
        ),
        "metric_count_24h": "Metrics (24h)",
    }
    
    # Display the interactive dataframe
    st.dataframe(
        df_display,
        column_config=column_config,
        width='stretch',
        hide_index=True,
        height=400,
        column_order=["vm_id", "name", "health_status", "current_cpu", "avg_cpu_24h", "metric_count_24h"]
    )
    
    # Table footer
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    st.caption(f"📊 Displaying {len(vms_list)} virtual machines | 🔄 Last updated: {current_time}")
    
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
st.caption("⚡ Project Fortify - AI-Assisted Infrastructure Monitoring | Version 0.2.0 | Built with Streamlit")