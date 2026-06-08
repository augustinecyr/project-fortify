"""
Synthetic CPU-series generator with ground-truth anomaly labels.

The "normal" model here mirrors the production simulator
(`data/generators/metrics_simulator.py`): a per-profile baseline modulated by a
time-of-day factor, a per-VM sinusoidal wave, a long-term drift, and bounded
random variance. Crucially, the *random spikes* that the live simulator injects
are turned OFF in the normal model and re-introduced here as *labelled*
anomalies at known indices.

Because the data is synthetic we control the ground truth exactly, which lets us
run a supervised evaluation (precision / recall / F1) of the z-score detector —
something a real AI-Ops deployment usually cannot do for lack of labels.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

import numpy as np

# Profiles copied from data/generators/metrics_simulator.py so the evaluation
# data is grounded in the same model the system was built against.
# name: (base_cpu, variance, profile_factor)
VM_PROFILES = {
    "web": (40, 15, 1.0),
    "api": (45, 18, 1.2),
    "db": (65, 12, 0.8),
    "cache": (25, 10, 0.5),
    "worker": (75, 20, 1.5),
    "monitor": (20, 8, 0.4),
    "backup": (15, 12, 0.6),
    "batch": (60, 25, 1.8),
    "idle": (5, 5, 0.1),
    "default": (35, 15, 1.0),
}


@dataclass
class LabeledSeries:
    """A synthetic CPU series with its ground-truth anomaly labels."""

    profile: str
    values: np.ndarray           # CPU percent per timestep, shape (n,)
    labels: np.ndarray           # 1 = injected anomaly, 0 = normal, shape (n,)
    anomaly_indices: List[int] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.values)

    @property
    def n_anomalies(self) -> int:
        return int(self.labels.sum())


def _time_factor(hour: float) -> float:
    """Diurnal load multiplier, matching the live simulator's bands."""
    if 9 <= hour <= 17:
        return 1.2
    if 0 <= hour <= 6:
        return 0.7
    return 1.0


def generate_normal_series(
    profile: str,
    n: int = 144,
    days: float = 1.0,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """
    Generate a 'normal' CPU series (no anomalies) for the given profile.

    `n` samples are spread evenly across `days` of simulated time so the
    diurnal band and sinusoidal wave are exercised. Default 144 samples ≈ one
    reading every 10 minutes over 24h, matching the simulator's cadence.
    """
    rng = rng or np.random.default_rng()
    base_cpu, variance, profile_factor = VM_PROFILES.get(profile, VM_PROFILES["default"])

    drift = rng.uniform(0.8, 1.2)            # persistent per-VM trend
    phase = rng.uniform(0, 2 * math.pi)      # per-VM wave offset

    values = np.empty(n, dtype=float)
    for i in range(n):
        hour = ((i / n) * 24.0 * days + phase / (2 * math.pi) * 24) % 24
        effective = base_cpu * _time_factor(hour) * drift * profile_factor
        wave = 0.2 * math.sin(2 * math.pi * (hour / 24) + phase)
        effective *= (1 + wave)
        cpu = effective + rng.uniform(-variance, variance)
        values[i] = min(100.0, max(0.0, cpu))
    return values


def inject_anomalies(
    values: np.ndarray,
    n_anomalies: int,
    magnitude: tuple[float, float] = (15.0, 30.0),
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Add spikes at random indices, mirroring the simulator's spike model
    (a +15..30 bump, clipped to 100). Returns (new_values, labels).
    """
    rng = rng or np.random.default_rng()
    values = values.copy()
    labels = np.zeros(len(values), dtype=int)
    if n_anomalies <= 0:
        return values, labels

    idx = rng.choice(len(values), size=min(n_anomalies, len(values)), replace=False)
    for i in idx:
        bump = rng.uniform(*magnitude)
        values[i] = min(100.0, values[i] + bump)
        labels[i] = 1
    return values, labels


def inject_clear_anomalies(
    values: np.ndarray,
    n_anomalies: int,
    sigma_mult: float = 4.0,
    floor: float = 25.0,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Inject *unambiguous* anomalies: each spike is at least `sigma_mult` standard
    deviations of the series above the affected point (with an absolute `floor`
    so it works even on very flat series), clipped to 100.

    This produces anomalies that are genuinely out-of-distribution — the regime
    in which a statistical detector *should* succeed — as a counterpart to the
    subtle, variance-overlapping anomalies from `inject_anomalies`.
    """
    rng = rng or np.random.default_rng()
    values = values.copy()
    labels = np.zeros(len(values), dtype=int)
    if n_anomalies <= 0 or len(values) < 2:
        return values, labels

    std = float(np.std(values, ddof=1))
    bump = max(sigma_mult * std, floor)
    idx = rng.choice(len(values), size=min(n_anomalies, len(values)), replace=False)
    for i in idx:
        values[i] = min(100.0, values[i] + bump)
        labels[i] = 1
    return values, labels


# Profiles with enough headroom below 100% that a clear spike is separable.
HEADROOM_PROFILES = ["web", "api", "cache", "monitor", "backup", "idle"]


def make_labeled_series(
    profile: str,
    n: int = 144,
    n_anomalies: int = 5,
    magnitude: tuple[float, float] = (15.0, 30.0),
    mode: str = "realistic",
    seed: int | None = None,
) -> LabeledSeries:
    """
    Build one normal series and inject labelled anomalies.

    mode="realistic" — subtle spikes (+15..30) that overlap normal variance.
    mode="clear"     — unambiguous, out-of-distribution spikes (>= 4 sigma).
    """
    rng = np.random.default_rng(seed)
    normal = generate_normal_series(profile, n=n, rng=rng)
    if mode == "clear":
        values, labels = inject_clear_anomalies(normal, n_anomalies, rng=rng)
    else:
        values, labels = inject_anomalies(normal, n_anomalies, magnitude, rng=rng)
    return LabeledSeries(
        profile=profile,
        values=values,
        labels=labels,
        anomaly_indices=list(np.flatnonzero(labels)),
    )


def make_dataset(
    profiles: List[str] | None = None,
    series_per_profile: int = 20,
    n: int = 144,
    n_anomalies: int = 5,
    mode: str = "realistic",
    base_seed: int = 0,
) -> List[LabeledSeries]:
    """Build a reproducible dataset spanning several profiles and seeds."""
    if profiles is None:
        profiles = (
            HEADROOM_PROFILES if mode == "clear"
            else ["web", "api", "db", "worker", "cache", "batch"]
        )
    dataset: List[LabeledSeries] = []
    seed = base_seed
    for profile in profiles:
        for _ in range(series_per_profile):
            dataset.append(
                make_labeled_series(
                    profile, n=n, n_anomalies=n_anomalies, mode=mode, seed=seed
                )
            )
            seed += 1
    return dataset
