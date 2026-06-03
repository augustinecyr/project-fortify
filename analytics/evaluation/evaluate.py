"""
Offline evaluation harness for Project Fortify.

Runs five experiments against the project's anomaly detector and health-scoring
model and writes machine-readable results (CSV) and report-ready figures (PNG)
to `analytics/evaluation/results/`:

  A. Detection accuracy vs injected ground truth (precision / recall / F1).
  B. Threshold sensitivity sweep (justifies / critiques the hard-coded t=2.0).
  C. Baseline comparison (z-score vs fixed threshold, robust z-score, iso-forest).
  D. Masking / self-contamination (recall vs anomaly rate).
  E. Health-score construct validation (does the 40/30/30 model behave as designed).

Everything runs offline in seconds — no API, database, Docker, or Groq needed.

Usage:
    python analytics/evaluation/evaluate.py
    python analytics/evaluation/evaluate.py --no-plots      # CSV only
    python analytics/evaluation/evaluate.py --seed 7
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

# Make sibling modules and the analytics package importable whether this is run
# as a script or as a module.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from detectors import (  # noqa: E402
    DETECTORS,
    zscore_detector,
    robust_zscore_detector,
)
from metrics import Scores, score_prediction  # noqa: E402
from synthetic import make_dataset, make_labeled_series, generate_normal_series  # noqa: E402
from scoring import calculate_health_score  # noqa: E402

RESULTS_DIR = _HERE / "results"


# --------------------------------------------------------------------------- #
# Output helpers
# --------------------------------------------------------------------------- #
def _ensure_results_dir() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def _write_csv(name: str, rows: List[dict]) -> None:
    if not rows:
        return
    path = RESULTS_DIR / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"    wrote {path.relative_to(_HERE.parents[1])}")


def _try_savefig(fig, name: str, enabled: bool) -> None:
    if not enabled:
        return
    path = RESULTS_DIR / name
    fig.savefig(path, dpi=130, bbox_inches="tight")
    print(f"    wrote {path.relative_to(_HERE.parents[1])}")


# --------------------------------------------------------------------------- #
# Experiment A — detection accuracy at the production threshold
# --------------------------------------------------------------------------- #
def experiment_a(base_seed: int) -> List[dict]:
    print("\n[A] Detection accuracy vs injected ground truth (z-score, t=2.0)")
    rows: List[dict] = []
    for mode, label in [("clear", "clear (>=4 sigma)"),
                        ("realistic", "subtle (overlaps variance)")]:
        dataset = make_dataset(
            series_per_profile=25, n_anomalies=5, mode=mode, base_seed=base_seed
        )
        total = Scores(0, 0, 0, 0)
        f1s: List[float] = []
        for s in dataset:
            sc = score_prediction(zscore_detector(s.values, threshold=2.0), s.labels)
            total = total + sc
            f1s.append(sc.f1)

        micro = total.as_dict()
        macro_f1 = float(np.mean(f1s))
        print(
            f"    anomaly tier = {label}\n"
            f"      series={len(dataset)}  precision={micro['precision']:.3f}  "
            f"recall={micro['recall']:.3f}  F1(micro)={micro['f1']:.3f}  "
            f"F1(macro)={macro_f1:.3f}"
        )
        print(f"      confusion: TP={micro['tp']} FP={micro['fp']} "
              f"FN={micro['fn']} TN={micro['tn']}")
        rows.append({
            "anomaly_tier": label,
            "detector": "z-score (project, t=2.0)",
            "series": len(dataset),
            **micro,
            "f1_macro": round(macro_f1, 4),
        })

    _write_csv("exp_a_detection_accuracy.csv", rows)
    return rows


# --------------------------------------------------------------------------- #
# Experiment B — threshold sensitivity
# --------------------------------------------------------------------------- #
def experiment_b(base_seed: int, plots: bool) -> List[dict]:
    print("\n[B] Threshold sensitivity sweep")
    dataset = make_dataset(series_per_profile=25, n_anomalies=5, base_seed=base_seed)
    thresholds = np.round(np.arange(1.0, 4.01, 0.25), 2)

    rows: List[dict] = []
    for t in thresholds:
        total = Scores(0, 0, 0, 0)
        for s in dataset:
            total = total + score_prediction(
                zscore_detector(s.values, threshold=float(t)), s.labels
            )
        d = total.as_dict()
        rows.append({"threshold": float(t), **d})
        print(f"    t={t:>4}  precision={d['precision']:.3f}  "
              f"recall={d['recall']:.3f}  F1={d['f1']:.3f}")

    _write_csv("exp_b_threshold_sweep.csv", rows)

    if plots:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.plot(thresholds, [r["precision"] for r in rows], "o-", label="Precision")
        ax.plot(thresholds, [r["recall"] for r in rows], "s-", label="Recall")
        ax.plot(thresholds, [r["f1"] for r in rows], "^-", label="F1")
        ax.axvline(2.0, color="grey", ls="--", lw=1, label="production t=2.0")
        ax.set_xlabel("z-score threshold")
        ax.set_ylabel("score")
        ax.set_title("Detection performance vs z-score threshold")
        ax.set_ylim(0, 1.05)
        ax.legend()
        ax.grid(alpha=0.3)
        _try_savefig(fig, "exp_b_threshold_sweep.png", plots)
        plt.close(fig)
    return rows


# --------------------------------------------------------------------------- #
# Experiment C — baseline comparison
# --------------------------------------------------------------------------- #
def experiment_c(base_seed: int, plots: bool) -> List[dict]:
    print("\n[C] Baseline comparison")
    rows: List[dict] = []
    for mode, label in [("clear", "clear"), ("realistic", "subtle")]:
        dataset = make_dataset(
            series_per_profile=25, n_anomalies=5, mode=mode, base_seed=base_seed
        )
        print(f"    -- {label} anomalies --")
        for name, detector in DETECTORS.items():
            total = Scores(0, 0, 0, 0)
            for s in dataset:
                total = total + score_prediction(detector(s.values), s.labels)
            d = total.as_dict()
            if d["tp"] + d["fp"] + d["fn"] + d["tn"] == 0:
                continue  # detector unavailable (e.g. sklearn missing)
            rows.append({"anomaly_tier": label, "detector": name, **d})
            print(f"      {name:<28}  precision={d['precision']:.3f}  "
                  f"recall={d['recall']:.3f}  F1={d['f1']:.3f}")

    _write_csv("exp_c_baseline_comparison.csv", rows)

    if plots and rows:
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), sharey=True)
        for ax, tier in zip(axes, ["clear", "subtle"]):
            tier_rows = [r for r in rows if r["anomaly_tier"] == tier]
            names = [r["detector"] for r in tier_rows]
            x = np.arange(len(names))
            width = 0.27
            ax.bar(x - width, [r["precision"] for r in tier_rows], width, label="Precision")
            ax.bar(x, [r["recall"] for r in tier_rows], width, label="Recall")
            ax.bar(x + width, [r["f1"] for r in tier_rows], width, label="F1")
            ax.set_xticks(x)
            ax.set_xticklabels(names, rotation=25, ha="right", fontsize=7)
            ax.set_ylim(0, 1.05)
            ax.set_title(f"{tier} anomalies")
            ax.grid(alpha=0.3, axis="y")
        axes[0].set_ylabel("score")
        axes[0].legend()
        fig.suptitle("Detector comparison on identical labelled data")
        _try_savefig(fig, "exp_c_baseline_comparison.png", plots)
        plt.close(fig)
    return rows


# --------------------------------------------------------------------------- #
# Experiment D — masking / self-contamination
# --------------------------------------------------------------------------- #
def experiment_d(base_seed: int, plots: bool) -> List[dict]:
    print("\n[D] Masking / self-contamination (recall vs anomaly rate)")
    n = 144
    anomaly_counts = [1, 2, 4, 8, 12, 16, 20, 28]
    profiles = ["web", "api", "db", "worker", "cache", "batch"]

    rows: List[dict] = []
    for k in anomaly_counts:
        z_total = Scores(0, 0, 0, 0)
        r_total = Scores(0, 0, 0, 0)
        seed = base_seed
        for profile in profiles:
            for _ in range(25):
                s = make_labeled_series(profile, n=n, n_anomalies=k, seed=seed)
                seed += 1
                z_total = z_total + score_prediction(
                    zscore_detector(s.values, threshold=2.0), s.labels)
                r_total = r_total + score_prediction(
                    robust_zscore_detector(s.values, threshold=2.0), s.labels)
        rate = round(100 * k / n, 1)
        rows.append({
            "n_anomalies": k,
            "anomaly_rate_pct": rate,
            "zscore_recall": round(z_total.recall, 4),
            "zscore_f1": round(z_total.f1, 4),
            "robust_recall": round(r_total.recall, 4),
            "robust_f1": round(r_total.f1, 4),
        })
        print(f"    {k:>3} anomalies ({rate:>4}%)  "
              f"z-score recall={z_total.recall:.3f}  "
              f"robust recall={r_total.recall:.3f}")

    _write_csv("exp_d_masking.csv", rows)

    if plots:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4.5))
        rates = [r["anomaly_rate_pct"] for r in rows]
        ax.plot(rates, [r["zscore_recall"] for r in rows], "o-",
                label="z-score (project)")
        ax.plot(rates, [r["robust_recall"] for r in rows], "s-",
                label="robust z-score (MAD)")
        ax.set_xlabel("anomaly rate (% of window)")
        ax.set_ylabel("recall")
        ax.set_title("Recall degradation as anomalies contaminate the window")
        ax.set_ylim(0, 1.05)
        ax.legend()
        ax.grid(alpha=0.3)
        _try_savefig(fig, "exp_d_masking.png", plots)
        plt.close(fig)
    return rows


# --------------------------------------------------------------------------- #
# Experiment E — health-score construct validation
# --------------------------------------------------------------------------- #
def experiment_e(base_seed: int, plots: bool) -> Dict[str, List[dict]]:
    print("\n[E] Health-score construct validation")
    rng = np.random.default_rng(base_seed)

    # E1: rising mean CPU should lower the score (historical component).
    mean_rows: List[dict] = []
    for level in range(0, 101, 10):
        series = list(np.full(60, float(level)))
        res = calculate_health_score(series)
        mean_rows.append({
            "mean_cpu": level,
            "health_score": res["health_score"],
            "historical": res["components"]["historical_score"],
            "stability": res["components"]["stability_score"],
        })

    # E2: rising variance (fixed mean=50) should lower the stability component.
    var_rows: List[dict] = []
    for sd in range(0, 41, 5):
        series = list(np.clip(rng.normal(50.0, sd, 200), 0, 100))
        res = calculate_health_score(series)
        var_rows.append({
            "target_std": sd,
            "health_score": res["health_score"],
            "stability": res["components"]["stability_score"],
        })

    # E3: injecting anomalies should lower the score monotonically.
    anom_rows: List[dict] = []
    for k in [0, 1, 3, 6, 10, 15]:
        s = make_labeled_series("web", n=144, n_anomalies=k, seed=base_seed)
        res = calculate_health_score(list(s.values))
        anom_rows.append({
            "n_anomalies": k,
            "health_score": res["health_score"],
            "anomaly_component": res["components"]["anomaly_score"],
        })

    _write_csv("exp_e_construct_mean.csv", mean_rows)
    _write_csv("exp_e_construct_variance.csv", var_rows)
    _write_csv("exp_e_construct_anomalies.csv", anom_rows)

    mono_mean = all(
        mean_rows[i]["health_score"] >= mean_rows[i + 1]["health_score"]
        for i in range(len(mean_rows) - 1)
    )
    mono_var = all(
        var_rows[i]["stability"] >= var_rows[i + 1]["stability"]
        for i in range(len(var_rows) - 1)
    )
    print(f"    health monotonically falls with mean CPU:  {mono_mean}")
    print(f"    stability monotonically falls with variance: {mono_var}")

    if plots:
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 3, figsize=(13, 4))
        axes[0].plot([r["mean_cpu"] for r in mean_rows],
                     [r["health_score"] for r in mean_rows], "o-")
        axes[0].set_xlabel("mean CPU %"); axes[0].set_ylabel("health score")
        axes[0].set_title("Score vs mean CPU")
        axes[1].plot([r["target_std"] for r in var_rows],
                     [r["stability"] for r in var_rows], "s-", color="tab:orange")
        axes[1].set_xlabel("CPU std dev"); axes[1].set_ylabel("stability component")
        axes[1].set_title("Stability vs variance")
        axes[2].plot([r["n_anomalies"] for r in anom_rows],
                     [r["health_score"] for r in anom_rows], "^-", color="tab:red")
        axes[2].set_xlabel("injected anomalies"); axes[2].set_ylabel("health score")
        axes[2].set_title("Score vs anomaly count")
        for ax in axes:
            ax.grid(alpha=0.3)
        fig.suptitle("Health-score construct validation")
        _try_savefig(fig, "exp_e_construct_validation.png", plots)
        plt.close(fig)

    return {"mean": mean_rows, "variance": var_rows, "anomalies": anom_rows}


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description="Project Fortify evaluation harness")
    parser.add_argument("--seed", type=int, default=42, help="base RNG seed")
    parser.add_argument("--no-plots", action="store_true", help="skip PNG figures")
    args = parser.parse_args()

    plots = not args.no_plots
    _ensure_results_dir()

    print("=" * 70)
    print("  PROJECT FORTIFY - ANALYTICS EVALUATION HARNESS")
    print(f"  seed={args.seed}  plots={'on' if plots else 'off'}")
    print("=" * 70)

    experiment_a(args.seed)
    experiment_b(args.seed, plots)
    experiment_c(args.seed, plots)
    experiment_d(args.seed, plots)
    experiment_e(args.seed, plots)

    print("\nDone. Results in analytics/evaluation/results/\n")


if __name__ == "__main__":
    main()
