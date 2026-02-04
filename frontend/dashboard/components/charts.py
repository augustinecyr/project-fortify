"""
Reusable chart components for the dashboard.
"""
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict


def create_health_gauge(health_score: int, height: int = 300) -> go.Figure:
    """
    Create a health score gauge chart.
    
    Args:
        health_score: Health score value (0-100)
        height: Chart height in pixels
    
    Returns:
        Plotly figure object
    """
    # Determine color and status
    if health_score >= 80:
        color = "#28a745"
        status = "Excellent"
    elif health_score >= 65:
        color = "#5cb85c"
        status = "Good"
    elif health_score >= 50:
        color = "#ffc107"
        status = "Warning"
    else:
        color = "#dc3545"
        status = "Critical"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=health_score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': status, 'font': {'size': 20}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 50], 'color': '#ffebee'},
                {'range': [50, 65], 'color': '#fff9c4'},
                {'range': [65, 80], 'color': '#e8f5e9'},
                {'range': [80, 100], 'color': '#c8e6c9'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 50
            }
        }
    ))
    
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


def create_cpu_timeseries(
    metrics: List[Dict],
    mean_cpu: float,
    anomalous_indices: List[int] = None,
    height: int = 400
) -> go.Figure:
    """
    Create CPU metrics time-series chart with anomaly highlights.
    
    Args:
        metrics: List of metric dictionaries
        mean_cpu: Mean CPU value for reference line
        anomalous_indices: List of indices where anomalies occurred
        height: Chart height in pixels
    
    Returns:
        Plotly figure object
    """
    df = pd.DataFrame(metrics)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    fig = go.Figure()
    
    # Add CPU line
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['cpu_percent'],
        mode='lines',
        name='CPU Usage',
        line=dict(color='#1f77b4', width=2),
        hovertemplate='<b>Time</b>: %{x}<br><b>CPU</b>: %{y:.2f}%<extra></extra>'
    ))
    
    # Add mean line
    fig.add_hline(
        y=mean_cpu,
        line_dash="dash",
        line_color="green",
        annotation_text=f"Mean: {mean_cpu:.1f}%",
        annotation_position="right"
    )
    
    # Highlight anomalies
    if anomalous_indices and len(anomalous_indices) > 0:
        # Filter indices that are within the current dataframe range
        valid_indices = [i for i in anomalous_indices if i < len(df)]
        
        if valid_indices:
            anomaly_df = df.iloc[valid_indices]
            fig.add_trace(go.Scatter(
                x=anomaly_df['timestamp'],
                y=anomaly_df['cpu_percent'],
                mode='markers',
                name='Anomalies',
                marker=dict(color='red', size=8, symbol='x'),
                hovertemplate='<b>Anomaly</b><br><b>Time</b>: %{x}<br><b>CPU</b>: %{y:.2f}%<extra></extra>'
            ))
    
    fig.update_layout(
        title="CPU Utilization Over Time",
        xaxis_title="Time",
        yaxis_title="CPU Usage (%)",
        hovermode='x unified',
        height=height,
        showlegend=True
    )
    
    return fig


def create_component_bars(components: Dict[str, float]) -> go.Figure:
    """
    Create horizontal bar chart for score components.
    
    Args:
        components: Dictionary of component scores (0-1 range)
    
    Returns:
        Plotly figure object
    """
    # Convert to percentages
    data = {
        'Anomaly Detection': components.get('anomaly_score', 0) * 100,
        'Stability': components.get('stability_score', 0) * 100,
        'Historical Performance': components.get('historical_score', 0) * 100
    }
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    
    fig = go.Figure(go.Bar(
        x=list(data.values()),
        y=list(data.keys()),
        orientation='h',
        marker=dict(color=colors),
        text=[f"{v:.1f}" for v in data.values()],
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>Score: %{x:.1f}/100<extra></extra>'
    ))
    
    fig.update_layout(
        title="Score Component Breakdown",
        xaxis_title="Score (0-100)",
        yaxis_title="",
        height=250,
        showlegend=False,
        xaxis=dict(range=[0, 100])
    )
    
    return fig