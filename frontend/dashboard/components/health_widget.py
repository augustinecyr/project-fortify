# frontend/dashboard/components/health_widget.py
import streamlit as st

def render_health_score(score, status, components):
    """
    Render a modern health score widget with:
    - Large score card with status badge
    - Three component cards with weights and progress bars
    """
    # Custom CSS – injected once per session
    st.markdown("""
    <style>
        /* Health score main card */
        .health-score-card {
            background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
            border-radius: 24px;
            padding: 2rem 1.5rem;
            color: white;
            box-shadow: 0 10px 25px rgba(37, 99, 235, 0.15);
            margin-bottom: 1rem;
            border: 1px solid rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
        }
        .health-score-label {
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            opacity: 0.9;
            margin-bottom: 0.5rem;
        }
        .health-score-number {
            font-size: 3.5rem;
            font-weight: 700;
            line-height: 1;
            margin-bottom: 0.5rem;
        }
        .health-status-badge {
            display: inline-block;
            padding: 0.35rem 1.2rem;
            background: rgba(255,255,255,0.2);
            border-radius: 50px;
            font-size: 0.85rem;
            font-weight: 500;
            backdrop-filter: blur(4px);
            border: 1px solid rgba(255,255,255,0.3);
            margin-top: 0.5rem;
        }
        
        /* Component cards */
        .component-card {
            background: white;
            border-radius: 20px;
            padding: 1.25rem 1.5rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.02);
            border: 1px solid #f1f5f9;
            margin-bottom: 0.75rem;
            transition: all 0.2s ease;
        }
        .component-card:hover {
            border-color: #e2e8f0;
            box-shadow: 0 8px 16px rgba(0,0,0,0.04);
        }
        .component-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }
        .component-name {
            font-weight: 600;
            color: #0f172a;
            font-size: 1rem;
        }
        .component-weight {
            color: #64748b;
            font-size: 0.8rem;
            background: #f8fafc;
            padding: 0.2rem 0.6rem;
            border-radius: 12px;
            font-weight: 500;
        }
        .component-score-row {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 0.75rem;
        }
        .component-score-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: #0f172a;
            line-height: 1;
        }
        .component-score-max {
            color: #94a3b8;
            font-size: 0.9rem;
            margin-left: 0.25rem;
        }
        .component-trend {
            font-size: 0.8rem;
            padding: 0.25rem 0.5rem;
            border-radius: 16px;
            background: #f1f5f9;
            color: #475569;
        }
        .progress-bar-bg {
            background: #e2e8f0;
            height: 6px;
            border-radius: 10px;
            overflow: hidden;
        }
        .progress-bar-fill {
            height: 6px;
            border-radius: 10px;
            transition: width 0.3s ease;
        }
    </style>
    """, unsafe_allow_html=True)

    # ---- Health Score Card ----
    st.markdown(f"""
    <div class="health-score-card">
        <div class="health-score-label">Overall Health</div>
        <div class="health-score-number">{score:.0f}</div>
        <div class="health-status-badge">{status.upper()}</div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Component Cards ----
    components_config = [
        ("Anomaly Detection", "anomaly_score", "40%"),
        ("Stability", "stability_score", "30%"),
        ("Historical Baseline", "historical_score", "30%")
    ]

    for name, key, weight in components_config:
        comp_score = components.get(key, 0)
        
        # Determine colour based on score
        if comp_score >= 80:
            bar_color = "#10b981"
            trend_symbol = "▲"
            trend_color = "#059669"
        elif comp_score >= 50:
            bar_color = "#f59e0b"
            trend_symbol = "◆"
            trend_color = "#b45309"
        else:
            bar_color = "#ef4444"
            trend_symbol = "▼"
            trend_color = "#b91c1c"

        st.markdown(f"""
        <div class="component-card">
            <div class="component-header">
                <span class="component-name">{name}</span>
                <span class="component-weight">weight {weight}</span>
            </div>
            <div class="component-score-row">
                <span>
                    <span class="component-score-value">{comp_score:.1f}</span>
                    <span class="component-score-max">/100</span>
                </span>
                <span class="component-trend" style="color: {trend_color};">
                    {trend_symbol} {comp_score - 50:.0f}%
                </span>
            </div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: {comp_score}%; background: {bar_color};"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)