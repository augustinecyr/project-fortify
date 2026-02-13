"""
Export utilities for VM Health reports.
Generates comprehensive CSV or JSON reports with all VM data.
"""
import pandas as pd
import json
from io import StringIO
from datetime import datetime

def generate_csv_report(vm_id, vm_name, health_data, metrics_df, time_range):
    """
    Generate a complete CSV report with sections.
    """
    output = StringIO()
    
    # Header metadata
    output.write("VM HEALTH REPORT\n")
    output.write(f"Generated,{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    output.write(f"VM ID,{vm_id}\n")
    output.write(f"VM Name,{vm_name}\n")
    output.write(f"Time Range,{time_range}\n\n")
    
    # Health Summary
    output.write("HEALTH SUMMARY\n")
    health_summary = pd.DataFrame([
        ["Health Score", f"{health_data['health_score']:.1f}"],
        ["Health Status", health_data['status']],
        ["Anomaly Score", f"{health_data['anomaly_score']:.1f}"],
        ["Stability Score", f"{health_data['stability_score']:.1f}"],
        ["Historical Score", f"{health_data['historical_score']:.1f}"],
        ["Metrics Analyzed", f"{health_data['metrics_analyzed']:,}"]
    ])
    health_summary.to_csv(output, header=False, index=False)
    output.write("\n")
    
    # Anomaly Details
    output.write("ANOMALY DETAILS\n")
    anomaly_df = pd.DataFrame([
        ["Anomalies Detected", health_data['anomaly_count']],
        ["Total Data Points", f"{health_data['total_points']:,}"],
        ["Average CPU", f"{health_data['mean_cpu']:.1f}%"],
        ["Std Deviation", f"{health_data['std_dev']:.1f}"]
    ])
    anomaly_df.to_csv(output, header=False, index=False)
    output.write("\n")
    
    # CPU Statistics
    output.write("CPU STATISTICS\n")
    stats_df = pd.DataFrame([
        ["Minimum CPU", f"{metrics_df['cpu_percent'].min():.2f}%"],
        ["Maximum CPU", f"{metrics_df['cpu_percent'].max():.2f}%"],
        ["Average CPU", f"{metrics_df['cpu_percent'].mean():.2f}%"],
        ["Current CPU", f"{metrics_df['cpu_percent'].iloc[-1]:.2f}%"]
    ])
    stats_df.to_csv(output, header=False, index=False)
    output.write("\n")
    
    # Detailed Metrics
    output.write("DETAILED METRICS\n")
    metrics_df[['timestamp', 'cpu_percent']].to_csv(output, index=False)
    
    return output.getvalue()


def generate_json_report(vm_id, vm_name, health_data, metrics_list, time_range):
    """
    Generate a complete JSON report with nested structure.
    """
    report = {
        "export_info": {
            "generated": datetime.now().isoformat(),
            "vm_id": vm_id,
            "vm_name": vm_name,
            "time_range": time_range
        },
        "health_summary": {
            "health_score": health_data['health_score'],
            "health_status": health_data['status'],
            "component_scores": {
                "anomaly_score": health_data['anomaly_score'],
                "stability_score": health_data['stability_score'],
                "historical_score": health_data['historical_score']
            },
            "metrics_analyzed": health_data['metrics_analyzed']
        },
        "anomaly_details": {
            "anomaly_count": health_data['anomaly_count'],
            "total_points": health_data['total_points'],
            "mean_cpu": health_data['mean_cpu'],
            "std_dev": health_data['std_dev']
        },
        "cpu_metrics": metrics_list
    }
    return json.dumps(report, indent=2, default=str)