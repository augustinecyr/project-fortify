"""
AI Insights — Groq LLM-powered fleet intelligence.
On-demand analysis with fleet summary, anomalies, recommendations, and risk outlooks.

Place at: frontend/dashboard/views/ai_insights.py
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# ---- PATH FIXES ----
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "components"))

# ---- IMPORTS ----
try:
    from api_client import FortifyAPIClient
    from helpers import esc
except ImportError as e:
    st.markdown('<div class="error-card"><strong>Unable to load data</strong>Verify the backend is running and refresh the page.</div>', unsafe_allow_html=True)
    st.stop()

# ---- PAGE CONFIG ----
st.set_page_config(page_title="AI Insights", page_icon="🛡️", layout="wide")

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
.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #0f172a;
    margin: 0 0 0.25rem 0;
}
.section-subheader {
    font-size: 0.8rem;
    color: #94a3b8;
    margin-bottom: 1rem;
}
.summary-bar {
    background: #f8fafc;
    border-left: 4px solid #6366f1;
    border-radius: 0.5rem;
    padding: 0.875rem 1rem;
    font-size: 0.875rem;
    color: #1e3a5f;
    line-height: 1.65;
    margin-bottom: 1.5rem;
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
    font-size: 0.875rem;
    color: #0f172a;
    margin-bottom: 0.2rem;
}
.rec-desc {
    font-size: 0.825rem;
    color: #475569;
    line-height: 1.5;
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
    color: #94a3b8;
    margin-top: 0.3rem;
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
div[data-testid="stButton"] button[kind="primary"] {
    background: #0f172a !important;
    color: white !important;
    border-color: #0f172a !important;
    font-size: 0.8rem !important;
    padding: 0.35rem 1rem !important;
    border-radius: 6px !important;
}
div[data-testid="stButton"] button[kind="primary"]:hover {
    background: #1e293b !important;
    border-color: #1e293b !important;
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

# ---- HELPERS ----
SEVERITY_STYLES = {
    "critical": ("#fee2e2", "#991b1b", "#dc2626"),
    "warning":  ("#fef3c7", "#92400e", "#d97706"),
    "info":     ("#f0fdf4", "#166534", "#059669"),
}

PRIORITY_STYLES = {
    "high":   ("#fee2e2", "#991b1b"),
    "medium": ("#fef3c7", "#92400e"),
    "low":    ("#f0fdf4", "#166534"),
}


def fmt_timestamp(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        return ts


def render_anomalies(anomalies: list):
    if not anomalies:
        st.markdown("""
            <div style="background:#f0fdf4;border-left:4px solid #059669;
                        padding:0.875rem 1rem;border-radius:8px;">
                <div style="font-weight:600;color:#166534;font-size:0.875rem;margin-bottom:0.15rem;">
                    No anomalies detected
                </div>
                <div style="color:#14532d;font-size:0.8rem;">
                    All VMs are operating within normal parameters.
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    for a in anomalies:
        bg, fg, border = SEVERITY_STYLES.get(a.get("severity", "info"), SEVERITY_STYLES["info"])
        st.markdown(f"""
            <div class="anomaly-card" style="background:{bg};border-color:{border};">
                <div style="font-weight:600;font-size:0.875rem;color:{fg};margin-bottom:0.2rem;">
                    {esc(a.get('vm_id', '—'))} &nbsp;·&nbsp; {esc(a.get('vm_name', '—'))}
                    <span style="font-size:0.7rem;font-weight:500;margin-left:8px;
                        background:{border};color:white;padding:1px 8px;border-radius:9999px;
                        text-transform:uppercase;letter-spacing:0.04em;">
                        {esc(a.get('severity', 'info'))}
                    </span>
                </div>
                <div style="font-size:0.825rem;color:{fg};opacity:0.9;">
                    {esc(a.get('explanation', '—'))}
                </div>
            </div>
        """, unsafe_allow_html=True)


def render_recommendations(recommendations: list):
    if not recommendations:
        st.markdown("""
            <div style="background:#f8fafc;border:1px solid #e2e8f0;
                        padding:0.875rem 1rem;border-radius:8px;">
                <div style="font-weight:600;color:#475569;font-size:0.875rem;">
                    No recommendations generated.
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    for rec in recommendations:
        bg, fg = PRIORITY_STYLES.get(rec.get("priority", "low"), PRIORITY_STYLES["low"])
        affected = rec.get("affected_vms", [])
        affected_str = ", ".join(affected) if affected else "—"
        st.markdown(f"""
            <div class="rec-card">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:0.25rem;">
                    <span class="rec-title">{esc(rec.get('title', '—'))}</span>
                    <span style="font-size:0.7rem;font-weight:500;
                        background:{bg};color:{fg};padding:1px 8px;
                        border-radius:9999px;text-transform:uppercase;
                        letter-spacing:0.04em;white-space:nowrap;">
                        {esc(rec.get('priority', '').upper())}
                    </span>
                </div>
                <div class="rec-desc">{esc(rec.get('description', '—'))}</div>
                <div style="font-size:0.775rem;color:#94a3b8;margin-top:0.35rem;">
                    Affected: {esc(affected_str)}
                </div>
            </div>
        """, unsafe_allow_html=True)



# ---- INIT ----
from session import load_token

token = load_token()

api_client = FortifyAPIClient()

# Pre-populate from Redis cache on first load — no Groq call, no empty state flash
if "ai_insights" not in st.session_state:
    cached = api_client.get_ai_insights(token=token)
    st.session_state.ai_insights = cached if (cached and not cached.get("is_fallback")) else None

# ---- HEADER ROW — title left, refresh button right (mirrors home.py) ----
title_col, btn_col = st.columns([9, 0.4])

with title_col:
    st.markdown("""
        <div class="page-header-title">AI Insights</div>
        <div class="page-header-sub">
            On-demand LLM-powered analysis — fleet summary, anomalies, recommendations, and risk outlooks
        </div>
    """, unsafe_allow_html=True)

with btn_col:
    st.markdown("<br>", unsafe_allow_html=True)
    analyse_clicked = st.button(
        "↻",
        help="Refresh analysis — clears cache and triggers a fresh Groq LLM call. Results cached for 5 minutes.",
        width="stretch"
    )

st.markdown('<hr class="header-divider">', unsafe_allow_html=True)

# ---- META ROW — shown only when data exists ----
if st.session_state.ai_insights:
    data = st.session_state.ai_insights
    ts       = fmt_timestamp(data.get("analysis_timestamp", ""))
    model    = data.get("model_used", "—")
    vm_count = data.get("vm_count", "—")
    st.markdown(
        f'<div class="section-subheader">'
        f'Last analysed: {esc(ts)} &nbsp;·&nbsp; Model: {esc(model)} &nbsp;·&nbsp; {esc(vm_count)} VMs'
        f'</div>',
        unsafe_allow_html=True
    )

    # ---- FLEET SUMMARY ----
    st.markdown(f'<div class="summary-bar">{esc(data.get("fleet_summary", "—"))}</div>',
                unsafe_allow_html=True)

    # ---- ANOMALIES | RECOMMENDATIONS ----
    left_col, right_col = st.columns(2)

    with left_col:
        anomalies = data.get("anomalies", [])
        st.markdown(
            f'<div class="section-header">Anomalies'
            f'<span style="font-size:0.8rem;font-weight:400;color:#94a3b8;margin-left:8px;">'
            f'{len(anomalies)} flagged</span></div>',
            unsafe_allow_html=True
        )
        st.markdown('<div class="section-subheader">VMs flagged by the LLM as operating outside normal parameters</div>',
                    unsafe_allow_html=True)
        render_anomalies(anomalies)

    with right_col:
        recs = data.get("recommendations", [])
        st.markdown(
            f'<div class="section-header">Recommendations'
            f'<span style="font-size:0.8rem;font-weight:400;color:#94a3b8;margin-left:8px;">'
            f'{len(recs)} items</span></div>',
            unsafe_allow_html=True
        )
        st.markdown('<div class="section-subheader">Prioritised actions based on current fleet state</div>',
                    unsafe_allow_html=True)
        render_recommendations(recs)

    st.divider()

    # ---- PREDICTIONS ----
    import plotly.graph_objects as go

    preds = data.get("predictions", [])
    st.markdown(
        f'<div class="section-header">Risk Outlook'
        f'<span style="font-size:0.8rem;font-weight:400;color:#94a3b8;margin-left:8px;">'
        f'{len(preds)} outlooks</span></div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="section-subheader">Trend-based risk outlooks, not forecasts — urgency derived '
        'from the stated timeframe (shorter window = higher urgency)</div>',
        unsafe_allow_html=True
    )

    if preds:
        # Map timeframe text to urgency score (0–100)
        def timeframe_to_urgency(tf: str) -> int:
            tf = tf.lower()
            if "hour" in tf:
                try:
                    n = int(''.join(filter(str.isdigit, tf)) or 24)
                    return max(10, 100 - int(n * 2))
                except Exception:
                    return 85
            if "day" in tf:
                try:
                    n = int(''.join(filter(str.isdigit, tf)) or 7)
                    return max(10, 100 - int(n * 10))
                except Exception:
                    return 50
            if "week" in tf:
                return 25
            return 40

        def urgency_color(score: int) -> str:
            if score >= 75:
                return "#dc2626"
            if score >= 45:
                return "#d97706"
            return "#6366f1"

        # Escaped — plotly axis labels and hover templates render an HTML subset.
        vm_labels    = [f"{esc(p.get('vm_id','—'))} · {esc(p.get('vm_name','—'))}" for p in preds]
        urgency_vals = [timeframe_to_urgency(p.get("timeframe", "")) for p in preds]
        colors       = [urgency_color(v) for v in urgency_vals]
        timeframes   = [esc(p.get("timeframe", "—")) for p in preds]
        predictions  = [esc(p.get("prediction", "—")) for p in preds]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=urgency_vals,
            y=vm_labels,
            orientation="h",
            marker=dict(color=colors, opacity=0.85),
            customdata=list(zip(timeframes, predictions)),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Timeframe: %{customdata[0]}<br>"
                "Urgency: %{x}/100<br>"
                "<i>%{customdata[1]}</i>"
                "<extra></extra>"
            ),
            text=timeframes,
            textposition="outside",
            textfont=dict(size=11, color="#64748b"),
        ))

        # Urgency threshold lines
        fig.add_vline(x=75, line=dict(color="#dc2626", width=1, dash="dot"),
                      annotation_text="High", annotation_position="top",
                      annotation_font=dict(size=10, color="#dc2626"))
        fig.add_vline(x=45, line=dict(color="#d97706", width=1, dash="dot"),
                      annotation_text="Medium", annotation_position="top",
                      annotation_font=dict(size=10, color="#d97706"))

        fig.update_layout(
            height=max(180, len(preds) * 56),
            margin=dict(l=20, r=120, t=20, b=40),
            xaxis=dict(
                title="Urgency Score",
                range=[0, 115],
                showgrid=True,
                gridcolor="#f1f5f9",
                zeroline=False,
            ),
            yaxis=dict(
                showgrid=False,
                automargin=True,
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Inter, sans-serif", size=12),
            showlegend=False,
        )

        st.plotly_chart(fig, width="stretch")

        # Prediction narratives below the chart
        for pred in preds:
            st.markdown(f"""
                <div class="pred-card">
                    <div class="pred-vm">
                        {esc(pred.get('vm_id', '—'))} &nbsp;·&nbsp; {esc(pred.get('vm_name', '—'))}
                        <span style="font-size:0.75rem;font-weight:400;color:#78716c;margin-left:8px;">
                            {esc(pred.get('timeframe', '—'))}
                        </span>
                    </div>
                    <div class="pred-text">{esc(pred.get('prediction', '—'))}</div>
                </div>
            """, unsafe_allow_html=True)

    else:
        st.markdown("""
            <div style="background:#f5f3ff;border-left:4px solid #8b5cf6;
                        padding:0.875rem 1rem;border-radius:8px;">
                <div style="font-weight:600;color:#4c1d95;font-size:0.875rem;margin-bottom:0.15rem;">
                    No concerning trends detected
                </div>
                <div style="color:#5b21b6;font-size:0.8rem;">
                    Fleet metrics appear stable over the observed period.
                </div>
            </div>
        """, unsafe_allow_html=True)

else:
    # ---- EMPTY STATE ----
    st.markdown("""
        <div style="padding:4rem 0;text-align:center;">
            <div style="font-size:1rem;font-weight:600;color:#0f172a;margin-bottom:0.4rem;">
                No analysis available
            </div>
            <div style="font-size:0.875rem;color:#64748b;">
                Click the <strong>↻</strong> button above to generate AI-powered insights for your fleet.
            </div>
        </div>
    """, unsafe_allow_html=True)

# ---- TRIGGER (runs after render to avoid flash) ----
if analyse_clicked:
    with st.spinner("Requesting fresh analysis..."):
        api_client.clear_ai_cache(token=token)
        result = api_client.get_ai_insights(token=token)
    if result:
        st.session_state.ai_insights = result
        st.rerun()
    else:
        st.markdown('<div class="error-card"><strong>Unable to load data</strong>Verify the backend is running and refresh the page.</div>', unsafe_allow_html=True)

st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Project Fortify v1.1.1")