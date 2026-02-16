"""
Enhanced Export utilities for VM Health reports - NULL-safe version.
Generates comprehensive CSV or JSON reports with all VM data including
security metrics, resource utilization, and compliance information.
Handles missing/None values gracefully.
"""
import pandas as pd
import json
from io import StringIO
from datetime import datetime


def safe_format(value, format_spec=".1f", default="N/A"):
    """Safely format a value that might be None."""
    if value is None:
        return default
    try:
        if format_spec:
            return f"{value:{format_spec}}"
        return str(value)
    except (ValueError, TypeError):
        return default


def safe_get(data, key, default="N/A"):
    """Safely get a value from dict, handling None."""
    value = data.get(key)
    return value if value is not None else default


def generate_csv_report(vm_id, vm_name, health_data, metrics_df, time_range):
    """
    Generate a comprehensive CSV report with all enhanced VM parameters.
    Handles None values gracefully.
    """
    output = StringIO()
    
    # ============= HEADER METADATA =============
    output.write("PROJECT FORTIFY - COMPREHENSIVE VM HEALTH REPORT\n")
    output.write(f"Generated,{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    output.write(f"Report Type,VM Health & Security Analysis\n")
    output.write(f"Time Range,{time_range}\n\n")
    
    # ============= VM IDENTIFICATION =============
    output.write("VM IDENTIFICATION\n")
    vm_info = pd.DataFrame([
        ["VM ID", vm_id],
        ["VM Name", vm_name],
        ["Status", safe_get(health_data, 'status')],
        ["Host", safe_get(health_data, 'host')],
        ["OS Version", safe_get(health_data, 'os_version')],
        ["Uptime (hours)", safe_format(health_data.get('uptime_hours'), '.1f') if health_data.get('uptime_hours') else "Offline"]
    ])
    vm_info.to_csv(output, header=False, index=False)
    output.write("\n")
    
    # ============= HEALTH & SECURITY SCORES =============
    output.write("HEALTH & SECURITY SCORES\n")
    scores_df = pd.DataFrame([
        ["Overall Health Score", f"{safe_get(health_data, 'health_score', 0)}/100"],
        ["Health Status", safe_get(health_data, 'health_status', 'Unknown')],
        ["Security Score", f"{safe_get(health_data, 'security_score', 0)}/100"],
        ["Anomaly Score", safe_format(health_data.get('anomaly_score', 0), '.1f') + "/100"],
        ["Stability Score", safe_format(health_data.get('stability_score', 0), '.1f') + "/100"],
        ["Historical Score", safe_format(health_data.get('historical_score', 0), '.1f') + "/100"]
    ])
    scores_df.to_csv(output, header=False, index=False)
    output.write("\n")
    
    # ============= RESOURCE UTILIZATION =============
    status = health_data.get('status', 'unknown')
    if status == 'online':
        output.write("CURRENT RESOURCE UTILIZATION\n")
        
        # CPU
        current_cpu = health_data.get('current_cpu')
        cpu_str = safe_format(current_cpu, '.1f', 'N/A') + "%" if current_cpu is not None else "N/A"
        
        # Memory
        current_mem = health_data.get('current_memory')
        mem_used = health_data.get('memory_used_mb')
        mem_total = health_data.get('memory_total_mb')
        mem_str = safe_format(current_mem, '.1f', 'N/A') + "%" if current_mem is not None else "N/A"
        mem_detail = f"{mem_used:,} MB / {mem_total:,} MB" if mem_used and mem_total else "N/A"
        
        # Disk
        current_disk = health_data.get('current_disk')
        disk_used = health_data.get('disk_used_gb')
        disk_total = health_data.get('disk_total_gb')
        disk_str = safe_format(current_disk, '.1f', 'N/A') + "%" if current_disk is not None else "N/A"
        disk_detail = f"{disk_used:,} GB / {disk_total:,} GB" if disk_used and disk_total else "N/A"
        
        # Network
        net_in = health_data.get('network_in_mbps')
        net_out = health_data.get('network_out_mbps')
        net_in_str = safe_format(net_in, '.2f', 'N/A') + " MB/s" if net_in is not None else "N/A"
        net_out_str = safe_format(net_out, '.2f', 'N/A') + " MB/s" if net_out is not None else "N/A"
        
        resources_df = pd.DataFrame([
            ["CPU Usage", cpu_str],
            ["Memory Usage", mem_str],
            ["Memory Used/Total", mem_detail],
            ["Disk Usage", disk_str],
            ["Disk Used/Total", disk_detail],
            ["Network In", net_in_str],
            ["Network Out", net_out_str]
        ])
        resources_df.to_csv(output, header=False, index=False)
        output.write("\n")
    else:
        output.write("RESOURCE UTILIZATION\n")
        output.write("Status,VM is offline - resource metrics unavailable\n\n")
    
    # ============= SECURITY & COMPLIANCE =============
    output.write("SECURITY & COMPLIANCE\n")
    
    last_patch = health_data.get('last_patch_date')
    last_patch_str = str(last_patch) if last_patch else "Not recorded"
    
    firewall = health_data.get('firewall_enabled')
    ssh_key = health_data.get('ssh_key_auth')
    encryption = health_data.get('disk_encryption')
    
    security_df = pd.DataFrame([
        ["Open Vulnerabilities", safe_get(health_data, 'open_vulnerabilities', 0)],
        ["Critical Vulnerabilities", safe_get(health_data, 'critical_vulnerabilities', 0)],
        ["Last Patch Date", last_patch_str],
        ["Compliance Score", safe_get(health_data, 'compliance_score')],
        ["Firewall Enabled", "Yes" if firewall else "No" if firewall is False else "Unknown"],
        ["SSH Key Authentication", "Yes" if ssh_key else "No" if ssh_key is False else "Unknown"],
        ["Disk Encryption", "Yes" if encryption else "No" if encryption is False else "Unknown"]
    ])
    security_df.to_csv(output, header=False, index=False)
    output.write("\n")
    
    # ============= ALERTS & ANOMALIES =============
    output.write("ALERTS & ANOMALY DETECTION\n")
    alerts_df = pd.DataFrame([
        ["Active Alerts", safe_get(health_data, 'alert_count', 0)],
        ["Anomaly Detected", "Yes" if health_data.get('anomaly_detected') else "No"],
        ["Anomalies in Period", safe_get(health_data, 'anomaly_count', 0)],
        ["Total Data Points", f"{safe_get(health_data, 'total_points', 0):,}"],
        ["Metrics Analyzed", f"{safe_get(health_data, 'metrics_analyzed', 0):,}"],
        ["Mean CPU", safe_format(health_data.get('mean_cpu', 0), '.1f', 'N/A') + "%"],
        ["Std Deviation", safe_format(health_data.get('std_dev', 0), '.1f', 'N/A')]
    ])
    alerts_df.to_csv(output, header=False, index=False)
    output.write("\n")
    
    # ============= CPU STATISTICS =============
    output.write("CPU STATISTICS\n")
    stats_df = pd.DataFrame([
        ["Minimum CPU", f"{metrics_df['cpu_percent'].min():.2f}%"],
        ["Maximum CPU", f"{metrics_df['cpu_percent'].max():.2f}%"],
        ["Average CPU", f"{metrics_df['cpu_percent'].mean():.2f}%"],
        ["Median CPU", f"{metrics_df['cpu_percent'].median():.2f}%"],
        ["Current CPU", f"{metrics_df['cpu_percent'].iloc[-1]:.2f}%"],
        ["75th Percentile", f"{metrics_df['cpu_percent'].quantile(0.75):.2f}%"],
        ["95th Percentile", f"{metrics_df['cpu_percent'].quantile(0.95):.2f}%"]
    ])
    stats_df.to_csv(output, header=False, index=False)
    output.write("\n")
    
    # ============= DETAILED METRICS =============
    output.write("DETAILED CPU METRICS\n")
    metrics_df[['timestamp', 'cpu_percent', 'source']].to_csv(output, index=False)
    
    # ============= FOOTER =============
    output.write("\n")
    output.write("END OF REPORT\n")
    output.write(f"Project Fortify - AI-Assisted Infrastructure Monitoring\n")
    
    return output.getvalue()


def generate_json_report(vm_id, vm_name, health_data, metrics_list, time_range):
    """
    Generate a comprehensive JSON report with nested structure.
    Handles None values gracefully.
    """
    report = {
        "export_metadata": {
            "generated_at": datetime.now().isoformat(),
            "report_type": "comprehensive_vm_health_security_analysis",
            "time_range": time_range,
            "format_version": "2.0"
        },
        
        "vm_identification": {
            "vm_id": vm_id,
            "vm_name": vm_name,
            "status": health_data.get('status', 'unknown'),
            "host": health_data.get('host'),
            "os_version": health_data.get('os_version'),
            "uptime_hours": health_data.get('uptime_hours')
        },
        
        "health_and_security_scores": {
            "overall_health_score": health_data.get('health_score', 0),
            "health_status": health_data.get('health_status', 'unknown'),
            "security_score": health_data.get('security_score', 0),
            "component_scores": {
                "anomaly_score": health_data.get('anomaly_score', 0),
                "stability_score": health_data.get('stability_score', 0),
                "historical_score": health_data.get('historical_score', 0)
            },
            "metrics_analyzed": health_data.get('metrics_analyzed', 0)
        },
        
        "resource_utilization": {
            "cpu": {
                "current_percent": health_data.get('current_cpu'),
                "average_24h": health_data.get('avg_cpu_24h'),
                "peak_24h": health_data.get('peak_cpu_24h')
            },
            "memory": {
                "current_percent": health_data.get('current_memory'),
                "used_mb": health_data.get('memory_used_mb'),
                "total_mb": health_data.get('memory_total_mb'),
                "available_mb": (health_data.get('memory_total_mb', 0) - health_data.get('memory_used_mb', 0)) if health_data.get('memory_total_mb') and health_data.get('memory_used_mb') else None
            },
            "disk": {
                "current_percent": health_data.get('current_disk'),
                "used_gb": health_data.get('disk_used_gb'),
                "total_gb": health_data.get('disk_total_gb'),
                "available_gb": (health_data.get('disk_total_gb', 0) - health_data.get('disk_used_gb', 0)) if health_data.get('disk_total_gb') and health_data.get('disk_used_gb') else None
            },
            "network": {
                "inbound_mbps": health_data.get('network_in_mbps'),
                "outbound_mbps": health_data.get('network_out_mbps')
            }
        },
        
        "security_and_compliance": {
            "vulnerabilities": {
                "open": health_data.get('open_vulnerabilities', 0),
                "critical": health_data.get('critical_vulnerabilities', 0),
                "severity_distribution": {
                    "critical": health_data.get('critical_vulnerabilities', 0),
                    "high": health_data.get('open_vulnerabilities', 0) - health_data.get('critical_vulnerabilities', 0)
                }
            },
            "patching": {
                "last_patch_date": health_data.get('last_patch_date'),
                "days_since_patch": None
            },
            "compliance": {
                "score": health_data.get('compliance_score'),
                "checks": {
                    "firewall_enabled": health_data.get('firewall_enabled'),
                    "ssh_key_authentication": health_data.get('ssh_key_auth'),
                    "disk_encryption": health_data.get('disk_encryption')
                }
            }
        },
        
        "alerts_and_anomalies": {
            "active_alerts": health_data.get('alert_count', 0),
            "anomaly_detected": health_data.get('anomaly_detected', False),
            "anomaly_analysis": {
                "anomaly_count": health_data.get('anomaly_count', 0),
                "total_data_points": health_data.get('total_points', 0),
                "anomaly_rate": (health_data.get('anomaly_count', 0) / health_data.get('total_points', 1) * 100) if health_data.get('total_points', 0) > 0 else 0,
                "statistics": {
                    "mean_cpu": health_data.get('mean_cpu', 0),
                    "std_deviation": health_data.get('std_dev', 0)
                }
            }
        },
        
        "cpu_metrics_analysis": {
            "time_range": time_range,
            "data_points": len(metrics_list),
            "statistics": {
                "minimum": min(m['cpu_percent'] for m in metrics_list) if metrics_list else 0,
                "maximum": max(m['cpu_percent'] for m in metrics_list) if metrics_list else 0,
                "average": sum(m['cpu_percent'] for m in metrics_list) / len(metrics_list) if metrics_list else 0,
                "current": metrics_list[-1]['cpu_percent'] if metrics_list else 0
            },
            "detailed_metrics": metrics_list
        },
        
        "report_summary": {
            "overall_status": "healthy" if health_data.get('health_score', 0) >= 80 else "warning" if health_data.get('health_score', 0) >= 60 else "critical",
            "requires_attention": health_data.get('alert_count', 0) > 0 or health_data.get('critical_vulnerabilities', 0) > 0,
            "critical_issues": {
                "critical_vulnerabilities": health_data.get('critical_vulnerabilities', 0) > 0,
                "active_alerts": health_data.get('alert_count', 0) > 0,
                "anomaly_detected": health_data.get('anomaly_detected', False),
                "low_health_score": health_data.get('health_score', 0) < 60
            },
            "data_completeness": {
                "has_host_info": health_data.get('host') is not None,
                "has_resource_metrics": health_data.get('current_memory') is not None,
                "has_security_data": health_data.get('open_vulnerabilities', 0) > 0 or health_data.get('compliance_score') is not None
            }
        }
    }
    
    return json.dumps(report, indent=2, default=str)