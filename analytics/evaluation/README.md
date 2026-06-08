# Analytics Evaluation Harness

Offline, reproducible evaluation of Project Fortify's **anomaly detection**
(`analytics/anomaly_detection.py`) and **health-scoring** model
(`analytics/scoring.py`).

The harness imports those modules directly and generates its own synthetic,
labelled CPU data, so it runs in a few seconds with **no API, database, Docker,
Redis, or Groq** required.

## Run it

```powershell
python analytics/evaluation/evaluate.py            # full run, writes CSVs + PNGs
python analytics/evaluation/evaluate.py --no-plots # CSVs only
python analytics/evaluation/evaluate.py --seed 7   # different RNG seed
```

Outputs are written to `analytics/evaluation/results/` (CSV tables + PNG
figures), ready to drop into the project report.

## Methodology

### Why synthetic data with injected labels
Project Fortify's VM fleet is simulated, so there is no externally-labelled
anomaly set. We exploit this: the harness reuses the live simulator's *normal*
model (per-profile baseline + diurnal factor + sinusoidal wave + bounded
variance, from `data/generators/metrics_simulator.py`) but turns its random
spikes **off**, then re-injects spikes at **known indices**. Those indices are
the ground truth. This gives a supervised precision/recall evaluation that a
real deployment usually cannot perform for lack of labels.

### Detectors compared
| Detector | Description |
|---|---|
| **z-score (project)** | The system under test: mean/std z-score, `\|z\| > 2.0`. |
| fixed threshold (>80) | Trivial absolute-cutoff baseline (the simulator's own rule). |
| robust z-score (MAD) | Median + MAD variant; resistant to self-contamination. |
| isolation forest | scikit-learn unsupervised baseline. |

### Two anomaly tiers
Experiments A and C are run against two datasets to separate *capability* from
*limitation*:

* **clear** — unambiguous, out-of-distribution spikes (≥ 4σ above the point).
  The regime in which a statistical detector should succeed.
* **subtle** — spikes of the same magnitude as normal variance (+15..30), which
  genuinely overlap the normal distribution. The hard regime.

### Experiments
| ID | Question | Output |
|----|----------|--------|
| **A** | How accurate is the detector (clear vs subtle anomalies)? | `exp_a_detection_accuracy.csv` |
| **B** | How sensitive is performance to the threshold? Is 2.0 justified? | `exp_b_threshold_sweep.{csv,png}` |
| **C** | How does the method compare to baselines, on both tiers? | `exp_c_baseline_comparison.{csv,png}` |
| **D** | Does recall degrade as anomalies contaminate the window (masking)? | `exp_d_masking.{csv,png}` |
| **E** | Does the 40/30/30 health score behave as designed? | `exp_e_construct_*.csv`, `exp_e_construct_validation.png` |

### Metrics
Point-wise **precision, recall, F1** and a confusion matrix, aggregated
(micro-averaged) across all synthetic series. Experiment A also reports a
macro-averaged F1 (mean over series). Experiment E checks **monotonicity** of
the score components against their design intent rather than against labels
(construct validation).

## Reproducibility
All randomness flows through a seeded `numpy.random.default_rng`. The same
`--seed` produces identical numbers and figures on any machine.

## Files
| File | Role |
|---|---|
| `synthetic.py` | Normal-series generation + labelled anomaly injection. |
| `detectors.py` | Project detector wrapper + baselines (shared contract). |
| `metrics.py` | Confusion matrix, precision/recall/F1. |
| `evaluate.py` | Orchestrates experiments A–E; writes CSV + PNG. |
