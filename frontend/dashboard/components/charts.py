"""
Chart components for VM Health monitoring.
Always returns a valid Plotly Figure – never None.
"""
import plotly.graph_objects as go
import pandas as pd

def create_cpu_timeseries(metrics_list, mean_cpu, anomalous_indices=None, height=400):
    """
    Create a time series chart of CPU metrics with optional anomaly highlights.
    Returns a Plotly Figure in all cases (even with empty data).
    """
    # --- Default empty figure with "No data" message ---
    fig = go.Figure()
    fig.add_annotation(
        text="No CPU metrics available",
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=16, color="#64748b")
    )
    fig.update_layout(height=height)

    # If we have real data, replace with proper chart
    if metrics_list and len(metrics_list) > 0:
        try:
            df = pd.DataFrame(metrics_list)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Create new figure
            fig = go.Figure()
            
            # CPU line
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['cpu_percent'],
                mode='lines',
                name='CPU %',
                line=dict(color='#1f77b4', width=2),
                hovertemplate='%{y:.1f}%<extra></extra>'
            ))
            
            # Mean line
            fig.add_hline(
                y=mean_cpu,
                line_dash="dash",
                line_color="#64748b",
                opacity=0.5,
                annotation_text=f"Avg: {mean_cpu:.1f}%",
                annotation_position="bottom right"
            )
            
            # Anomaly points
            if anomalous_indices and len(anomalous_indices) > 0:
                valid_indices = [i for i in anomalous_indices if i < len(df)]
                if valid_indices:
                    anomaly_df = df.iloc[valid_indices]
                    fig.add_trace(go.Scatter(
                        x=anomaly_df['timestamp'],
                        y=anomaly_df['cpu_percent'],
                        mode='markers',
                        name='Anomalies',
                        marker=dict(color='#ef4444', size=8, symbol='circle'),
                        hovertemplate='Anomaly: %{y:.1f}%<extra></extra>'
                    ))
            
            # Layout
            fig.update_layout(
                height=height,
                margin=dict(l=40, r=40, t=20, b=40),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                xaxis_title="Time",
                yaxis_title="CPU Usage (%)",
                yaxis=dict(range=[0, 100]),
                hovermode='x unified',
                template='plotly_white'
            )
        except Exception:
            # If anything fails, return the safe "No data" figure
            pass  # fig is already the empty figure
    
    return fig