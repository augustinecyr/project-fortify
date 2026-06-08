"""
Classification metrics for point-wise anomaly detection.

Each detector returns the set of indices it flags as anomalous; we compare that
against the ground-truth label vector to derive a confusion matrix and the
standard precision / recall / F1 figures used in the evaluation chapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass
class Scores:
    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def __add__(self, other: "Scores") -> "Scores":
        return Scores(
            self.tp + other.tp,
            self.fp + other.fp,
            self.fn + other.fn,
            self.tn + other.tn,
        )

    def as_dict(self) -> dict:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "tn": self.tn,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
        }


def score_prediction(predicted_indices: Iterable[int], labels: np.ndarray) -> Scores:
    """Confusion matrix from a set of predicted-positive indices vs labels."""
    pred = np.zeros(len(labels), dtype=int)
    idx = list(predicted_indices)
    if idx:
        pred[idx] = 1
    tp = int(np.sum((pred == 1) & (labels == 1)))
    fp = int(np.sum((pred == 1) & (labels == 0)))
    fn = int(np.sum((pred == 0) & (labels == 1)))
    tn = int(np.sum((pred == 0) & (labels == 0)))
    return Scores(tp, fp, fn, tn)
