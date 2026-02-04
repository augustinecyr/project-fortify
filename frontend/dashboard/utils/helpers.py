"""
Helper functions for the dashboard.
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List


def get_health_status_class(score: int) -> tuple:
    """
    Get CSS class and label for health score.
    
    Args:
        score: Health score (0-100)
    
    Returns:
        Tuple of (css_class, status_label, color)
    """
    if score >= 80:
        return "health-score-excellent", "Excellent", "#28a745"
    elif score >= 65:
        return "health-score-good", "Good", "#5cb85c"
    elif score >= 50:
        return "health-score-warning", "Warning", "#ffc107"
    else:
        return "health-score-critical", "Critical", "#dc3545"


def export_to_csv(data: List[Dict], filename: str) -> str:
    """
    Convert data to CSV format.
    
    Args:
        data: List of dictionaries to export
        filename: Output filename
    
    Returns:
        CSV string
    """
    df = pd.DataFrame(data)
    return df.to_csv(index=False)


def format_timestamp(timestamp: str) -> str:
    """
    Format ISO timestamp to readable format.
    
    Args:
        timestamp: ISO 8601 timestamp string
    
    Returns:
        Formatted timestamp string
    """
    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def calculate_time_range(hours: int = 24) -> tuple:
    """
    Calculate start and end timestamps for time range.
    
    Args:
        hours: Number of hours to look back
    
    Returns:
        Tuple of (start_time, end_time) as ISO strings
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    return start_time.isoformat(), end_time.isoformat()


def format_large_number(num: int) -> str:
    """
    Format large numbers with K/M suffixes.
    
    Args:
        num: Number to format
    
    Returns:
        Formatted string
    """
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    else:
        return str(num)