"""
Unit tests for anomaly detection module.
"""
import sys
from pathlib import Path

# Add analytics to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "analytics"))

from anomaly_detection import calculate_z_scores, detect_anomalies


class TestCalculateZScores:
    """Tests for z-score calculation."""

    def test_basic_z_scores(self):
        """Z-scores should center data around 0."""
        values = [10, 20, 30, 40, 50]
        z_scores = calculate_z_scores(values)
        # Middle value should have z-score closest to 0
        assert abs(z_scores[2]) < abs(z_scores[0])
        assert abs(z_scores[2]) < abs(z_scores[4])

    def test_single_value(self):
        """Single value should return z-score of 0."""
        values = [50.0]
        z_scores = calculate_z_scores(values)
        assert z_scores == [0.0]

    def test_empty_list(self):
        """Empty list should return empty list."""
        values = []
        z_scores = calculate_z_scores(values)
        assert z_scores == []

    def test_identical_values(self):
        """Identical values should all have z-score of 0 (std_dev = 0)."""
        values = [50.0, 50.0, 50.0, 50.0]
        z_scores = calculate_z_scores(values)
        assert z_scores == [0.0, 0.0, 0.0, 0.0]

    def test_known_z_scores(self):
        """Test with known values where z-scores can be verified."""
        # Mean = 3, std_dev = 1 (approx)
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        z_scores = calculate_z_scores(values)
        # First and last should be equal and opposite
        assert abs(z_scores[0] + z_scores[4]) < 0.01


class TestDetectAnomalies:
    """Tests for anomaly detection."""

    def test_no_anomalies(self):
        """Stable data should have no anomalies."""
        # Generate stable data around 50
        values = [50.0 + (i % 3) for i in range(100)]
        result = detect_anomalies(values)
        assert result["anomaly_score"] == 0.0
        assert result["anomaly_count"] == 0
        assert result["total_points"] == 100

    def test_clear_anomaly(self):
        """A clear outlier should be detected."""
        # 99 stable values + 1 extreme outlier
        values = [50.0] * 99 + [200.0]
        result = detect_anomalies(values)
        assert result["anomaly_count"] > 0
        assert result["anomaly_score"] > 0.0
        # The outlier is at index 99
        assert 99 in result["anomalous_indices"]

    def test_multiple_anomalies(self):
        """Multiple outliers should all be detected."""
        values = [50.0] * 95 + [200.0, 200.0, 200.0, 200.0, 200.0]
        result = detect_anomalies(values)
        assert result["anomaly_count"] == 5

    def test_empty_values(self):
        """Empty input should return zero anomaly score."""
        result = detect_anomalies([])
        assert result["anomaly_score"] == 0.0
        assert result["anomaly_count"] == 0
        assert result["total_points"] == 0

    def test_single_value(self):
        """Single value should return zero anomaly score."""
        result = detect_anomalies([50.0])
        assert result["anomaly_score"] == 0.0
        assert result["anomaly_count"] == 0

    def test_custom_threshold(self):
        """Lower threshold should detect more anomalies."""
        values = [50.0] * 90 + [70.0] * 10
        result_strict = detect_anomalies(values, threshold=1.0)
        result_lenient = detect_anomalies(values, threshold=3.0)
        assert result_strict["anomaly_count"] >= result_lenient["anomaly_count"]

    def test_anomaly_score_range(self):
        """Anomaly score should always be between 0 and 1."""
        values = [50.0] * 90 + [200.0] * 10
        result = detect_anomalies(values)
        assert 0.0 <= result["anomaly_score"] <= 1.0

    def test_mean_and_std_dev(self):
        """Mean and std_dev should be calculated correctly."""
        values = [40.0, 50.0, 60.0]
        result = detect_anomalies(values)
        assert result["mean"] == 50.0
        assert result["std_dev"] == 10.0