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

def create_memory_timeseries(metrics_list, mean_memory, anomalous_indices=None, height=400):
    """
    Create a time series chart of Memory metrics with optional anomaly highlights.
    """
    # Default empty figure with "No data" message
    fig = go.Figure()
    fig.add_annotation(
        text="No Memory metrics available",
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=16, color="#64748b")
    )
    fig.update_layout(height=height)

    if metrics_list and len(metrics_list) > 0:
        try:
            df = pd.DataFrame(metrics_list)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Determine the value column (adjust to match your API response)
            value_col = None
            if 'memory_percent' in df.columns:
                value_col = 'memory_percent'
            elif 'value' in df.columns:
                value_col = 'value'
            else:
                # No recognizable column – return empty figure
                return fig
            
            # Create new figure
            fig = go.Figure()
            
            # Memory line with fill
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df[value_col],
                mode='lines',
                name='Memory %',
                line=dict(color='#10b981', width=2.5),  # green
                fill='tozeroy',
                fillcolor='rgba(16, 185, 129, 0.1)',
                hovertemplate='<b>%{x|%H:%M:%S}</b><br>Memory: %{y:.1f}%<extra></extra>'
            ))
            
            # Mean line
            fig.add_hline(
                y=mean_memory,
                line_dash="dash",
                line_color="#64748b",
                line_width=2,
                opacity=0.6,
                annotation_text=f"Mean: {mean_memory:.1f}%",
                annotation_position="top right",
                annotation_font=dict(size=11, color="#64748b")
            )
            
            # Anomaly points (if any)
            if anomalous_indices and len(anomalous_indices) > 0:
                valid_indices = [i for i in anomalous_indices if 0 <= i < len(df)]
                if valid_indices:
                    anomaly_df = df.iloc[valid_indices]
                    fig.add_trace(go.Scatter(
                        x=anomaly_df['timestamp'],
                        y=anomaly_df[value_col],
                        mode='markers',
                        name='Anomalies',
                        marker=dict(
                            color='#ef4444',
                            size=10,
                            symbol='circle',
                            line=dict(color='white', width=1.5)
                        ),
                        hovertemplate='<b>Anomaly</b><br>%{x|%H:%M:%S}<br>Memory: %{y:.1f}%<extra></extra>'
                    ))
            
            # Dynamic y‑axis range
            mem_min = df[value_col].min()
            mem_max = df[value_col].max()
            y_padding = (mem_max - mem_min) * 0.1 if mem_max > mem_min else 5
            y_min = max(0, mem_min - y_padding)
            y_max = min(100, mem_max + y_padding)
            
            fig.update_layout(
                height=height,
                margin=dict(l=60, r=40, t=40, b=60),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    bgcolor="rgba(255,255,255,0.8)",
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
                    title="Memory Usage (%)",
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
            # Return the empty figure on any error
            pass
    
    return fig

def create_memory_gauge(percentage, used_mb=None, total_mb=None):
    """
    Create a gauge chart for memory usage.
    
    Args:
        percentage: Current memory usage percentage
        used_mb: Used memory in MB (optional, for tooltip)
        total_mb: Total memory in MB (optional, for tooltip)
    
    Returns:
        plotly.graph_objects.Figure
    """
    # Determine colour based on percentage
    if percentage >= 80:
        color = "#ef4444"  # red
    elif percentage >= 60:
        color = "#f59e0b"  # orange
    else:
        color = "#10b981"  # green

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=percentage,
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'suffix': '%', 'font': {'size': 28}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#94a3b8"},
            'bar': {'color': color, 'thickness': 0.3},
            'bgcolor': 'white',
            'borderwidth': 2,
            'bordercolor': '#e2e8f0',
            'steps': [
                {'range': [0, 60], 'color': '#dcfce7'},
                {'range': [60, 80], 'color': '#fef3c7'},
                {'range': [80, 100], 'color': '#fee2e2'}
            ],
            'threshold': {
                'line': {'color': color, 'width': 4},
                'thickness': 0.75,
                'value': percentage
            }
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
    return fig