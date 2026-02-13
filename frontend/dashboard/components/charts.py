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
    
    Args:
        metrics_list: List of metric dictionaries with 'timestamp' and 'cpu_percent'
        mean_cpu: Mean CPU value to display as reference line
        anomalous_indices: List of indices marking anomalies (only applied if valid)
        height: Chart height in pixels
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
            
            # CPU line with fill
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['cpu_percent'],
                mode='lines',
                name='CPU %',
                line=dict(color='#3b82f6', width=2.5),
                fill='tozeroy',
                fillcolor='rgba(59, 130, 246, 0.1)',
                hovertemplate='<b>%{x|%H:%M:%S}</b><br>CPU: %{y:.1f}%<extra></extra>'
            ))
            
            # Mean line with better styling
            fig.add_hline(
                y=mean_cpu,
                line_dash="dash",
                line_color="#64748b",
                line_width=2,
                opacity=0.6,
                annotation_text=f"Mean: {mean_cpu:.1f}%",
                annotation_position="top right",
                annotation_font=dict(size=11, color="#64748b")
            )
            
            # Anomaly points - only if indices are valid for current dataset
            if anomalous_indices and len(anomalous_indices) > 0:
                valid_indices = [i for i in anomalous_indices if 0 <= i < len(df)]
                if valid_indices:
                    anomaly_df = df.iloc[valid_indices]
                    fig.add_trace(go.Scatter(
                        x=anomaly_df['timestamp'],
                        y=anomaly_df['cpu_percent'],
                        mode='markers',
                        name='Anomalies',
                        marker=dict(
                            color='#ef4444',
                            size=10,
                            symbol='circle',
                            line=dict(color='white', width=1.5)
                        ),
                        hovertemplate='<b>Anomaly</b><br>%{x|%H:%M:%S}<br>CPU: %{y:.1f}%<extra></extra>'
                    ))
            
            # Calculate dynamic y-axis range for better visibility
            cpu_min = df['cpu_percent'].min()
            cpu_max = df['cpu_percent'].max()
            y_padding = (cpu_max - cpu_min) * 0.1 if cpu_max > cpu_min else 5
            y_min = max(0, cpu_min - y_padding)
            y_max = min(100, cpu_max + y_padding)
            
            # Layout with improved styling
            fig.update_layout(
                height=height,
                margin=dict(l=60, r=40, t=40, b=60),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor="#e5e7eb",
                    borderwidth=1
                ),
                xaxis=dict(
                    title="Time",
                    showgrid=True,
                    gridcolor='#f1f5f9',
                    zeroline=False
                ),
                yaxis=dict(
                    title="CPU Usage (%)",
                    range=[y_min, y_max],
                    showgrid=True,
                    gridcolor='#f1f5f9',
                    zeroline=False
                ),
                hovermode='x unified',
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(family="Inter, sans-serif", size=12)
            )
        except Exception:
            # If anything fails, return the safe "No data" figure
            pass  # fig is already the empty figure
    
    return fig