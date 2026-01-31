"""
Anomaly detection module for Project Fortify.
Uses z-score method to detect anomalous CPU metrics.
"""
import statistics
from typing import List, Dict


def calculate_z_scores(values: List[float]) -> List[float]:
    """
    Calculate z-scores for a list of values.
    
    Args:
        values: List of numeric values
    
    Returns:
        List of z-scores corresponding to each value
    """
    if len(values) < 2:
        return [0.0] * len(values)
    
    mean = statistics.mean(values)
    std_dev = statistics.stdev(values)
    
    # Avoid division by zero
    if std_dev == 0:
        return [0.0] * len(values)
    
    return [(v - mean) / std_dev for v in values]


def detect_anomalies(values: List[float], threshold: float = 2.0) -> Dict:
    """
    Detect anomalies in a list of CPU metric values using z-score method.
    
    A data point is considered anomalous if its z-score exceeds the threshold.
    
    Args:
        values: List of CPU percentage values
        threshold: Z-score threshold for anomaly detection (default: 2.0)
    
    Returns:
        Dictionary containing:
            - anomaly_score: float (0-1), higher means more anomalous
            - anomaly_count: number of anomalous points detected
            - total_points: total number of data points analyzed
            - anomalous_indices: list of indices where anomalies were detected
            - mean: mean of the values
            - std_dev: standard deviation of the values
    """
    if len(values) < 2:
        return {
            "anomaly_score": 0.0,
            "anomaly_count": 0,
            "total_points": len(values),
            "anomalous_indices": [],
            "mean": values[0] if values else 0.0,
            "std_dev": 0.0,
        }
    
    mean = statistics.mean(values)
    std_dev = statistics.stdev(values)
    z_scores = calculate_z_scores(values)
    
    # Find anomalous points
    anomalous_indices = [
        i for i, z in enumerate(z_scores) if abs(z) > threshold
    ]
    
    anomaly_count = len(anomalous_indices)
    
    # Calculate anomaly score (0-1)
    # Based on proportion of anomalous points and severity
    if anomaly_count == 0:
        anomaly_score = 0.0
    else:
        # Factor 1: proportion of anomalous points
        proportion = anomaly_count / len(values)
        
        # Factor 2: average severity of anomalous points
        avg_severity = sum(
            abs(z_scores[i]) for i in anomalous_indices
        ) / anomaly_count
        
        # Normalize severity (cap at threshold * 3)
        normalized_severity = min(avg_severity / (threshold * 3), 1.0)
        
        # Combined score (weighted)
        anomaly_score = round(min(proportion * 0.5 + normalized_severity * 0.5, 1.0), 4)
    
    return {
        "anomaly_score": anomaly_score,
        "anomaly_count": anomaly_count,
        "total_points": len(values),
        "anomalous_indices": anomalous_indices,
        "mean": round(mean, 2),
        "std_dev": round(std_dev, 2),
    }