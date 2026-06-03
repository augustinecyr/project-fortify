"""
Anomaly detectors under evaluation.

The detector under test is the project's own z-score method
(`analytics/anomaly_detection.py`). The remaining detectors are baselines used
to put its performance in context — this is what lets the report argue the
chosen approach against existing alternatives rather than in isolation:

  * fixed threshold   — the simplest possible rule (absolute CPU cutoff),
                        and the definition the live simulator itself uses.
  * robust z-score    — median + MAD instead of mean + std; resistant to the
                        self-contamination that inflates the classic z-score.
  * isolation forest  — scikit-learn's unsupervised model, making good on the
                        "scikit-learn baseline models" claim in the tech stack.

Every detector exposes the same contract: take a 1-D array of CPU values and
return a sorted list of indices flagged as anomalous.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Dict, List

import numpy as np

# Import the project's production detector directly so we evaluate the real
# code path, not a re-implementation.
_ANALYTICS_DIR = Path(__file__).resolve().parents[1]
if str(_ANALYTICS_DIR) not in sys.path:
    sys.path.insert(0, str(_ANALYTICS_DIR))

from anomaly_detection import detect_anomalies  # noqa: E402


def zscore_detector(values: np.ndarray, threshold: float = 2.0) -> List[int]:
    """The system under test: classic mean/std z-score (production code)."""
    result = detect_anomalies(list(values), threshold=threshold)
    return list(result["anomalous_indices"])


def fixed_threshold_detector(values: np.ndarray, cutoff: float = 80.0) -> List[int]:
    """Trivial baseline: flag any reading above an absolute CPU cutoff."""
    return list(np.flatnonzero(values > cutoff))


def robust_zscore_detector(values: np.ndarray, threshold: float = 2.0) -> List[int]:
    """
    Robust baseline: modified z-score using median and MAD.
    Far less sensitive to a handful of large spikes pulling the mean/std,
    so it directly tests the masking weakness of the classic z-score.
    """
    values = np.asarray(values, dtype=float)
    if len(values) < 2:
        return []
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    if mad == 0:
        return []
    modified_z = 0.6745 * (values - median) / mad
    return list(np.flatnonzero(np.abs(modified_z) > threshold))


def isolation_forest_detector(
    values: np.ndarray, contamination: float | str = "auto", seed: int = 0
) -> List[int]:
    """scikit-learn IsolationForest baseline (returns [] if sklearn absent)."""
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:  # keep the harness runnable without sklearn
        return []
    values = np.asarray(values, dtype=float).reshape(-1, 1)
    if len(values) < 2:
        return []
    model = IsolationForest(contamination=contamination, random_state=seed)
    pred = model.fit_predict(values)  # -1 = anomaly, 1 = normal
    return list(np.flatnonzero(pred == -1))


# Registry of detectors with their default settings, for the comparison runs.
DETECTORS: Dict[str, Callable[[np.ndarray], List[int]]] = {
    "z-score (project, t=2.0)": lambda v: zscore_detector(v, threshold=2.0),
    "fixed threshold (>80)": lambda v: fixed_threshold_detector(v, cutoff=80.0),
    "robust z-score (MAD, t=2.0)": lambda v: robust_zscore_detector(v, threshold=2.0),
    "isolation forest": lambda v: isolation_forest_detector(v),
}
