"""
Health scoring module for Project Fortify.
Calculates VM health scores based on CPU metrics and anomaly detection.
"""
import statistics
from typing import List, Dict

from anomaly_detection import detect_anomalies


def calculate_stability_score(values: List[float]) -> float:
    """
    Calculate stability score based on metric variance.
    Lower variance = higher stability.
    
    Args:
        values: List of CPU percentage values
    
    Returns:
        Stability score (0-1), higher is more stable
    """
    if len(values) < 2:
        return 1.0
    
    std_dev = statistics.stdev(values)
    
    # Normalize: std_dev of 0 = perfect stability (1.0)
    # std_dev of 50+ = very unstable (0.0)
    stability = max(0.0, 1.0 - (std_dev / 50.0))
    
    return round(stability, 4)


def calculate_historical_score(values: List[float]) -> float:
    """
    Calculate historical score based on average CPU usage.
    Lower average CPU = healthier.
    
    Args:
        values: List of CPU percentage values
    
    Returns:
        Historical score (0-1), higher is healthier
    """
    if not values:
        return 1.0
    
    mean = statistics.mean(values)
    
    # Normalize: mean of 0 = perfect (1.0)
    # mean of 100 = worst (0.0)
    historical = max(0.0, 1.0 - (mean / 100.0))
    
    return round(historical, 4)


def calculate_health_score(cpu_values: List[float], anomaly_threshold: float = 2.0) -> Dict:
    """
    Calculate overall VM health score.
    
    Score breakdown (0-100):
        - Anomaly component (40%): Based on anomaly detection results
        - Stability component (30%): Based on metric variance
        - Historical component (30%): Based on average CPU usage
    
    Args:
        cpu_values: List of CPU percentage values (last 24 hours)
        anomaly_threshold: Z-score threshold for anomaly detection
    
    Returns:
        Dictionary containing:
            - health_score: integer (0-100)
            - components: breakdown of each score component
            - anomaly_details: details from anomaly detection
    """
    if not cpu_values:
        return {
            "health_score": 100,
            "components": {
                "anomaly_score": 1.0,
                "stability_score": 1.0,
                "historical_score": 1.0,
            },
            "anomaly_details": {},
        }
    
    # Run anomaly detection
    anomaly_result = detect_anomalies(cpu_values, threshold=anomaly_threshold)
    
    # Component 1: Anomaly score (inverted - lower anomaly = higher score)
    anomaly_component = round(1.0 - anomaly_result["anomaly_score"], 4)
    
    # Component 2: Stability score
    stability_component = calculate_stability_score(cpu_values)
    
    # Component 3: Historical score
    historical_component = calculate_historical_score(cpu_values)
    
    # Weighted health score
    weighted_score = (
        anomaly_component * 0.4 +
        stability_component * 0.3 +
        historical_component * 0.3
    )
    
    # Convert to 0-100 scale
    health_score = round(weighted_score * 100)
    
    return {
        "health_score": health_score,
        "components": {
            "anomaly_score": anomaly_component,
            "stability_score": stability_component,
            "historical_score": historical_component,
        },
        "anomaly_details": anomaly_result,
    }