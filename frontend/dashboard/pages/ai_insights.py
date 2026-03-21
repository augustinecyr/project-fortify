"""
AI Insights — Groq LLM-powered fleet intelligence.
On-demand analysis with fleet summary, anomalies, recommendations, and predictions.

Place at: frontend/dashboard/pages/ai_insights.py
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timezone

# ---- PATH FIXES ----
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "components"))

# ---- IMPORTS ----
try:
    from api_client import FortifyAPIClient
except ImportError as e:
    st.error(f"Import failed: {e}")
    st.stop()

# ---- PAGE CONFIG ----
st.set_page_config(page_title="AI Insights", page_icon="🤖", layout="wide")

# ---- CSS ----
st.markdown("""
<style>
.section-header {
    font-size: 1.15rem;
    font-weight: 600;
    color: #0f172a;
    margin: 1.25rem 0 0.4rem 0;
}
.ai-summary-box {
    background: linear-gradient(135deg, #eff6ff 0%, #f5f3ff 100%);
    border: 1px solid #bfdbfe;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    font-size: 0.975rem;
    color: #1e3a5f;
    line-height: 1.7;
}
.anomaly-card {
    border-radius: 8px;
    padding: 0.875rem 1rem;
    margin-bottom: 0.6rem;
    border-left: 4px solid;
}
.rec-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.875rem 1rem;
    margin-bottom: 0.6rem;
}
.rec-title {
    font-weight: 600;
    font-size: 0.9rem;
    color: #0f172a;
    margin-bottom: 0.2rem;
}
.rec-desc {
    font-size: 0.825rem;
    color: #475569;
}
.pred-card {
    background: #fafaf9;
    border: 1px solid #e7e5e4;
    border-left: 4px solid #8b5cf6;
    border-radius: 8px;
    padding: 0.875rem 1rem;
    margin-bottom: 0.6rem;
}
.pred-vm {
    font-weight: 600;
    font-size: 0.875rem;
    color: #4c1d95;
    margin-bottom: 0.2rem;
}
.pred-text {
    font-size: 0.825rem;
    color: #44403c;
    line-height: 1.5;
}
.pred-timeframe {
    font-size: 0.775rem;
    color: #78716c;
    margin-top: 0.3rem;
}
.timestamp-badge {
    display: inline-block;
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 9999px;
    padding: 3px 12px;
    font-size: 0.75rem;
    color: #64748b;
}
.fallback-banner {
    background: #fef3c7;
    border-left: 4px solid #f59e0b;
    border-radius: 8px;
    padding: 0.875rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.875rem;
    color: #92400e;
}
</style>
""", unsafe_allow_html=True)

# ---- HELPERS ----
SEVERITY_STYLES = {
    "critical": ("#fee2e2", "#991b1b", "#dc2626"),
    "warning":  ("#fef3c7", "#92400e", "#d97706"),
    "info":     ("#f0fdf4", "#166534", "#059669"),
}

PRIORITY_BADGE = {
    "high":   ("🔴", "#fee2e2", "#991b1b"),
    "medium": ("🟡", "#fef3c7", "#92400e"),
    "low":    ("🟢", "#f0fdf4", "#166534"),
}


def fmt_timestamp(ts: str) -> str:
    """Format ISO timestamp to readable local time."""
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        return ts


def render_anomalies(anomalies: list):
    if not anomalies:
        st.markdown("""
            <div style="background:#f0fdf4;border-left:4px solid #059669;padding:0.875rem 1rem;border-radius:8px;">
                <strong style="color:#166534;">✓ No anomalies detected</strong><br>
                <span style="color:#14532d;font-size:0.825rem;">All VMs appear to be operating within normal parameters.</span>
            </div>
        """, unsafe_allow_html=True)
        return

    for a in anomalies:
        bg, fg, border = SEVERITY_STYLES.get(a.get("severity", "info"), SEVERITY_STYLES["info"])
        severity_label = a.get("severity", "info").upper()
        st.markdown(f"""
            <div class="anomaly-card" style="background:{bg};border-color:{border};">
                <div style="font-weight:600;font-size:0.875rem;color:{fg};margin-bottom:0.2rem;">
                    {a.get('vm_id', '—')} · {a.get('vm_name', '—')}
                    <span style="font-size:0.75rem;font-weight:400;margin-left:8px;
                        background:{border};color:white;padding:1px 8px;border-radius:9999px;">
                        {severity_label}
                    </span>
                </div>
                <div style="font-size:0.825rem;color:{fg};">{a.get('explanation', '—')}</div>
            </div>
        """, unsafe_allow_html=True)


def render_recommendations(recommendations: list):
    if not recommendations:
        st.info("No recommendations generated.")
        return

    for rec in recommendations:
        icon, bg, fg = PRIORITY_BADGE.get(rec.get("priority", "low"), PRIORITY_BADGE["low"])
        affected = rec.get("affected_vms", [])
        affected_str = ", ".join(affected) if affected else "—"
        st.markdown(f"""
            <div class="rec-card">
                <div class="rec-title">
                    {icon} {rec.get('title', '—')}
                    <span style="font-size:0.75rem;font-weight:400;color:#64748b;margin-left:8px;">
                        {rec.get('priority', '').upper()} PRIORITY
                    </span>
                </div>
                <div class="rec-desc">{rec.get('description', '—')}</div>
                <div style="font-size:0.775rem;color:#94a3b8;margin-top:0.35rem;">
                    Affected: {affected_str}
                </div>
            </div>
        """, unsafe_allow_html=True)


def render_predictions(predictions: list):
    if not predictions:
        st.markdown("""
            <div style="background:#f5f3ff;border-left:4px solid #8b5cf6;padding:0.875rem 1rem;border-radius:8px;">
                <strong style="color:#4c1d95;">✓ No concerning trends detected</strong><br>
                <span style="color:#5b21b6;font-size:0.825rem;">Fleet metrics appear stable over the observed period.</span>
            </div>
        """, unsafe_allow_html=True)
        return

    for pred in predictions:
        st.markdown(f"""
            <div class="pred-card">
                <div class="pred-vm">{pred.get('vm_id', '—')} · {pred.get('vm_name', '—')}</div>
                <div class="pred-text">{pred.get('prediction', '—')}</div>
                <div class="pred-timeframe">⏱ {pred.get('timeframe', '—')}</div>
            </div>
        """, unsafe_allow_html=True)


# ---- INIT ----
api_client = FortifyAPIClient()

# ---- HEADER ----
st.markdown("# 🤖 AI Insights")
st.caption("Groq LLM-powered fleet intelligence — on-demand analysis, anomaly explanations, and trend predictions.")

st.divider()

# ---- SESSION STATE ----
if "ai_insights" not in st.session_state:
    st.session_state.ai_insights = None
if "ai_insights_loading" not in st.session_state:
    st.session_state.ai_insights_loading = False

# ---- ANALYSE BUTTON ----
col_btn, col_info = st.columns([2, 5])

with col_btn:
    analyse_clicked = st.button(
        "🔍 Analyse Fleet",
        type="primary",
        use_container_width=True,
        help="Triggers a fresh LLM analysis of all VMs. Results are cached for 5 minutes."
    )

with col_info:
    if st.session_state.ai_insights:
        ts = st.session_state.ai_insights.get("analysis_timestamp", "")
        model = st.session_state.ai_insights.get("model_used", "—")
        vm_count = st.session_state.ai_insights.get("vm_count", "—")
        st.markdown(f"""
            <div style="padding-top:0.5rem;">
                <span class="timestamp-badge">🕐 Last analysed: {fmt_timestamp(ts)}</span>
                &nbsp;
                <span class="timestamp-badge">🧠 {model}</span>
                &nbsp;
                <span class="timestamp-badge">🖥 {vm_count} VMs</span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="padding-top:0.6rem;font-size:0.875rem;color:#64748b;">
                Click <strong>Analyse Fleet</strong> to run your first AI analysis.
            </div>
        """, unsafe_allow_html=True)

# ---- TRIGGER ANALYSIS ----
if analyse_clicked:
    with st.spinner("Clearing cache and requesting fresh analysis..."):
        api_client.clear_ai_cache()

    with st.spinner("Analysing fleet with Groq LLM — this may take a few seconds..."):
        result = api_client.get_ai_insights()

    if result:
        st.session_state.ai_insights = result
        st.rerun()
    else:
        st.error("Failed to retrieve AI insights. Check the API is running and GROQ_API_KEY is set.")

# ---- RENDER RESULTS ----
if st.session_state.ai_insights:
    data = st.session_state.ai_insights

    # Fallback warning banner
    if data.get("is_fallback"):
        st.markdown("""
            <div class="fallback-banner">
                ⚠️ <strong>AI service is temporarily unavailable.</strong>
                The Groq API could not be reached. Check your API key and connectivity, then try again.
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ---- FLEET SUMMARY ----
    st.markdown('<div class="section-header">📋 Fleet Summary</div>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="ai-summary-box">
            {data.get('fleet_summary', 'No summary available.')}
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- ANOMALIES + RECOMMENDATIONS side by side ----
    left_col, right_col = st.columns(2)

    with left_col:
        anomalies = data.get("anomalies", [])
        st.markdown(
            f'<div class="section-header">⚠️ Anomalies '
            f'<span style="font-size:0.8rem;font-weight:400;color:#64748b;">({len(anomalies)} flagged)</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        render_anomalies(anomalies)

    with right_col:
        recs = data.get("recommendations", [])
        st.markdown(
            f'<div class="section-header">💡 Recommendations '
            f'<span style="font-size:0.8rem;font-weight:400;color:#64748b;">({len(recs)} items)</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        render_recommendations(recs)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- PREDICTIONS ----
    preds = data.get("predictions", [])
    st.markdown(
        f'<div class="section-header">🔮 Predictions '
        f'<span style="font-size:0.8rem;font-weight:400;color:#64748b;">({len(preds)} forecasts)</span>'
        f'</div>',
        unsafe_allow_html=True
    )
    render_predictions(preds)

else:
    # ---- EMPTY STATE ----
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align:center;padding:3rem 1rem;">
            <div style="font-size:3rem;margin-bottom:1rem;">🤖</div>
            <div style="font-size:1.1rem;font-weight:600;color:#0f172a;margin-bottom:0.5rem;">
                No analysis yet
            </div>
            <div style="font-size:0.875rem;color:#64748b;max-width:400px;margin:0 auto;">
                Click <strong>Analyse Fleet</strong> above to generate AI-powered insights
                for your entire VM fleet using Groq LLM.
            </div>
        </div>
    """, unsafe_allow_html=True)

st.divider()
st.caption(f"Powered by Groq · llama-3.1-8b-instant · Project Fortify v0.5.0")