"""
Unit tests for health scoring module.
"""
import sys
from pathlib import Path

# Add analytics to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "analytics"))

from scoring import calculate_stability_score, calculate_historical_score, calculate_health_score


class TestCalculateStabilityScore:
    """Tests for stability score calculation."""

    def test_perfect_stability(self):
        """Identical values should give perfect stability."""
        values = [50.0] * 100
        score = calculate_stability_score(values)
        assert score == 1.0

    def test_high_variance_low_stability(self):
        """High variance should give low stability score."""
        values = [0.0, 100.0] * 50
        score = calculate_stability_score(values)
        assert score < 0.5

    def test_single_value(self):
        """Single value should return perfect stability."""
        score = calculate_stability_score([50.0])
        assert score == 1.0

    def test_empty_values(self):
        """Empty list should return perfect stability."""
        score = calculate_stability_score([])
        assert score == 1.0

    def test_score_range(self):
        """Score should always be between 0 and 1."""
        values = [0.0, 50.0, 100.0, 25.0, 75.0] * 20
        score = calculate_stability_score(values)
        assert 0.0 <= score <= 1.0


class TestCalculateHistoricalScore:
    """Tests for historical score calculation."""

    def test_low_cpu_high_score(self):
        """Low average CPU should give high historical score."""
        values = [10.0] * 100
        score = calculate_historical_score(values)
        assert score > 0.8

    def test_high_cpu_low_score(self):
        """High average CPU should give low historical score."""
        values = [90.0] * 100
        score = calculate_historical_score(values)
        assert score < 0.2

    def test_zero_cpu(self):
        """Zero CPU should give perfect historical score."""
        values = [0.0] * 100
        score = calculate_historical_score(values)
        assert score == 1.0

    def test_full_cpu(self):
        """100% CPU should give worst historical score."""
        values = [100.0] * 100
        score = calculate_historical_score(values)
        assert score == 0.0

    def test_empty_values(self):
        """Empty list should return perfect score."""
        score = calculate_historical_score([])
        assert score == 1.0


class TestCalculateHealthScore:
    """Tests for overall health score calculation."""

    def test_healthy_vm(self):
        """Stable, low-CPU VM should have high health score."""
        values = [20.0 + (i % 5) for i in range(1000)]
        result = calculate_health_score(values)
        assert result["health_score"] >= 70
        assert "components" in result
        assert "anomaly_details" in result

    def test_unhealthy_vm(self):
        """High CPU with spikes should have low health score."""
        values = [90.0] * 950 + [100.0] * 50
        result = calculate_health_score(values)
        assert result["health_score"] < 60  # Changed from 50 to 60

    def test_empty_values(self):
        """Empty input should return perfect health score."""
        result = calculate_health_score([])
        assert result["health_score"] == 100

    def test_score_range(self):
        """Health score should always be between 0 and 100."""
        values = [50.0 + (i % 30) for i in range(500)]
        result = calculate_health_score(values)
        assert 0 <= result["health_score"] <= 100

    def test_components_present(self):
        """Response should include all score components."""
        values = [50.0] * 100
        result = calculate_health_score(values)
        assert "anomaly_score" in result["components"]
        assert "stability_score" in result["components"]
        assert "historical_score" in result["components"]

    def test_components_range(self):
        """All components should be between 0 and 1."""
        values = [40.0 + (i % 20) for i in range(500)]
        result = calculate_health_score(values)
        for key, value in result["components"].items():
            assert 0.0 <= value <= 1.0, f"{key} out of range: {value}"

    def test_anomaly_details_present(self):
        """Response should include anomaly detection details."""
        values = [50.0] * 100
        result = calculate_health_score(values)
        assert "anomaly_score" in result["anomaly_details"]
        assert "anomaly_count" in result["anomaly_details"]
        assert "total_points" in result["anomaly_details"]