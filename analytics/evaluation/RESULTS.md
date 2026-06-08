# Evaluation Results

Prose interpretation of the harness outputs in `results/`. Numbers below are
from the default run (`python analytics/evaluation/evaluate.py`, seed 42); the
run is deterministic, so they reproduce exactly. Each experiment is defined in
[`README.md`](README.md). Read this file alongside the CSVs and PNGs — it
states *what the numbers mean*, including where the chosen method fails.

All detection metrics are point-wise and micro-averaged across 150 synthetic
CPU series of 144 points each (6 workload profiles × 25 series).

---

## Headline findings

1. On **clear** (out-of-distribution) anomalies the project z-score detector is
   strong: **F1 = 0.958** (precision 0.966, recall 0.949), and it beats every
   baseline by a wide margin.
2. On **subtle** anomalies that overlap normal variance, *no* method works well
   (best F1 = 0.254). This is a property of the problem, not a bug: such points
   are statistically indistinguishable from noise.
3. The default threshold **|z| > 2.0 is F1-optimal** on the hard tier — the
   sweep peaks there.
4. The classic z-score's **masking weakness is real and measurable**: its
   recall falls from 0.30 to 0.12 as contamination rises to ~19 %, and the
   robust MAD variant overtakes it beyond ~8 % contamination.
5. The 40/30/30 health score **behaves as designed** — each component moves
   monotonically with its intended driver — with one explainable exception at
   extreme variance (see Experiment E).

---

## Experiment A — detection accuracy (`exp_a_detection_accuracy.csv`)

| Tier | Precision | Recall | F1 (micro) | F1 (macro) |
|------|-----------|--------|------------|------------|
| clear (≥ 4σ) | 0.966 | 0.949 | **0.958** | 0.953 |
| subtle (overlaps variance) | 0.244 | 0.264 | **0.254** | 0.299 |

The ~0.70 F1 gap between tiers is the central result of the whole study. It
demonstrates that the detector is **capable** where capability is possible
(clear, separable anomalies) and **honestly limited** where the signal genuinely
overlaps the noise. Reporting both tiers prevents the common evaluation trap of
quoting a single flattering number. The close micro/macro agreement on the
clear tier (0.958 vs 0.953) shows the result is not driven by a few
easy series.

---

## Experiment B — threshold sweep (`exp_b_threshold_sweep.{csv,png}`)

Run on the **subtle** tier (the only regime where the threshold choice is
non-trivial; on the clear tier almost any threshold succeeds).

| Threshold | Precision | Recall | F1 |
|-----------|-----------|--------|-----|
| 1.5 | 0.114 | 0.383 | 0.175 |
| 1.75 | 0.170 | 0.329 | 0.224 |
| **2.0** | **0.244** | **0.264** | **0.254** |
| 2.25 | 0.288 | 0.213 | 0.245 |
| 2.5 | 0.319 | 0.159 | 0.212 |
| 3.0 | 0.399 | 0.103 | 0.163 |

Precision rises monotonically with the threshold and recall falls monotonically
— the textbook trade-off. **F1 peaks at exactly 2.0**, the production default.
This is the quantitative justification for the chosen threshold: it is not an
arbitrary round number but the empirical sweet spot between flagging too much
(low precision below 2.0) and missing too much (low recall above 2.0). A
deployment that valued precision over recall could justifiably raise it toward
2.5–3.0; the data makes that trade-off explicit rather than hidden.

---

## Experiment C — baseline comparison (`exp_c_baseline_comparison.{csv,png}`)

**Clear tier:**

| Detector | Precision | Recall | F1 |
|----------|-----------|--------|-----|
| **z-score (project, t=2.0)** | 0.966 | 0.949 | **0.958** |
| robust z-score (MAD) | 0.440 | 0.903 | 0.591 |
| fixed threshold (>80) | 0.422 | 0.291 | 0.344 |
| isolation forest | 0.148 | 0.992 | 0.257 |

**Subtle tier:**

| Detector | Precision | Recall | F1 |
|----------|-----------|--------|-----|
| **z-score (project, t=2.0)** | 0.244 | 0.264 | **0.254** |
| robust z-score (MAD) | 0.239 | 0.248 | 0.244 |
| isolation forest | 0.061 | 0.485 | 0.109 |
| fixed threshold (>80) | 0.053 | 0.473 | 0.096 |

On clear anomalies the project z-score wins decisively. The contrast with
Isolation Forest is instructive: it achieves near-perfect recall (0.992) but
precision of only 0.148 — it flags almost everything, so its high recall is
nearly worthless. The fixed threshold — the rule the simulator itself uses to
plant spikes — manages only F1 0.344, confirming that adapting to each series'
own distribution genuinely adds value over an absolute cutoff. The MAD variant
trades precision for recall and lands in between.

On the subtle tier every method collapses toward the noise floor and the
project z-score is only *marginally* the best (0.254 vs 0.244 for MAD). The
honest reading: when the anomaly's magnitude is the same as normal variation,
detector choice barely matters — the information simply is not there. This
bounds the claims the report can make and motivates richer features (multi-metric
correlation, seasonality) as future work rather than a different point detector.

---

## Experiment D — masking under contamination (`exp_d_masking.{csv,png}`)

Increasing the anomaly rate within a single window directly tests the
self-contamination weakness of the classic z-score (Section 2 of
`docs/related-work.md`).

| Anomaly rate | z-score recall | z-score F1 | robust recall | robust F1 |
|--------------|----------------|------------|---------------|-----------|
| 0.7 % | 0.300 | 0.102 | 0.287 | 0.107 |
| 2.8 % | 0.277 | 0.240 | 0.257 | 0.226 |
| 5.6 % | 0.255 | 0.294 | 0.249 | 0.287 |
| 8.3 % | 0.223 | 0.292 | 0.237 | **0.303** |
| 13.9 % | 0.154 | 0.230 | 0.193 | **0.276** |
| 19.4 % | 0.117 | 0.188 | 0.181 | **0.271** |

This is the clearest demonstration of a *known limitation made quantitative*.
At low contamination the two methods are equivalent. As contamination grows,
the classic z-score's recall decays steeply (0.30 → 0.12) because the spikes
inflate the standard deviation and pull the mean toward themselves, shrinking
every z-score — the masking effect. The robust MAD estimator degrades much more
gently and **overtakes the classic z-score on F1 beyond ~8 % contamination**.

The operational implication is recorded as a design boundary: Fortify's z-score
is appropriate because real VM windows are expected to be sparsely anomalous
(< 5 %). Should that assumption break — many simultaneous failures — the MAD
detector is the documented upgrade path, already implemented and measured.

---

## Experiment E — construct validation of the health score (`exp_e_construct_*.csv`)

This experiment checks the 40/30/30 score against its *design intent* (does each
component move the right way?) rather than against anomaly labels.

**Rising mean load** (`exp_e_construct_mean.csv`): as mean CPU goes 0 → 100, the
historical component falls 1.0 → 0.0 and health falls 100 → 70, both strictly
monotonic; stability stays 1.0 throughout (mean shift alone adds no variance).
Exactly as designed. ✔

**Rising variance** (`exp_e_construct_variance.csv`): as target σ goes 0 → 40,
stability falls monotonically 1.0 → 0.345. ✔ Health falls 85 → 63 up to σ = 25,
then **ticks back up to 66–68** at σ = 30–40. This non-monotonicity is *expected
and explainable*: at very high variance the z-score detector begins to mask
(the inflated σ hides spikes), so the 40 %-weighted anomaly component *rises*
and partially offsets the falling stability component. It is the same masking
effect from Experiment D surfacing in the score, not a scoring bug — and it is
documented rather than hidden.

**Rising anomaly count** (`exp_e_construct_anomalies.csv`): as injected
anomalies go 0 → 15, the anomaly component falls 0.821 → 0.768 and health falls
71 → 67, both monotonic. ✔

**Verdict:** the composite behaves as specified, each component is individually
inspectable, and the one non-monotonic region is a traceable consequence of the
detector's documented limitation — which is itself evidence the components are
wired together correctly.

---

## Threats to validity

- **Synthetic data.** Ground-truth labels are only available because the data
  is generated from the project's own simulator. Results characterise the
  detector against that generative model; a real fleet may differ. This is a
  deliberate, disclosed trade-off (see `README.md`, "Why synthetic data").
- **Single metric.** Only CPU is evaluated. Multi-metric and cross-host
  correlation are out of scope and listed as future work.
- **Point-wise scoring.** Metrics are per-point; an event-wise scoring scheme
  (credit for catching *any* point of an anomaly run) would report higher
  recall. Point-wise is the stricter, more conservative choice.
- **One seed.** Headline numbers are from seed 42. The harness accepts `--seed`
  for replication; qualitative conclusions are stable across seeds.
