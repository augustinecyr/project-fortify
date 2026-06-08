# Related Work

This document surveys the prior art that Project Fortify builds on and
positions the system against existing approaches. It is deliberately critical:
the goal is not to catalogue tools but to show *why* the design choices in
Fortify (a classic z-score detector, a weighted health score, and an LLM
explanation layer) are reasonable given what came before, and where they fall
short of the state of the art. The numbered references collected in
[References](#references) follow IEEE style and seed the final report's
bibliography.

The survey is organised around the three technical claims Fortify makes:

1. anomalies in VM metrics can be flagged with a lightweight statistical method
   (Sections [1](#1-threshold-and-rule-based-monitoring)–[2](#2-statistical-process-control));
2. a single interpretable score can summarise fleet health
   (Section [4](#4-health-scoring-and-aiops));
3. natural-language explanation lowers the operator's cognitive load
   (Section [5](#5-llm-assisted-operations)).

Each section ends with an explicit *Relevance to Fortify* note.

---

## 1. Threshold and rule-based monitoring

The oldest and still most widely deployed approach to infrastructure
monitoring is the static threshold: raise an alert when a metric crosses a
fixed cutoff (e.g. CPU > 80 %). Every mainstream observability platform —
Nagios, Zabbix, and the alerting rules in Prometheus [1] — supports this, and
its appeal is obvious: it is trivial to implement, fully transparent, and
requires no training data.

Its weaknesses are equally well documented. A fixed cutoff cannot adapt to
workload that is legitimately bursty or diurnal, so it produces both false
positives (a nightly batch job that always peaks at 85 %) and false negatives
(a host that is anomalous at 60 % because it normally idles at 10 %). Alert
fatigue from poorly tuned static thresholds is a recurring theme in the SRE
literature [2], and is the practical problem that adaptive and statistical
methods set out to solve.

**Relevance to Fortify.** The fixed-threshold rule is included in the
evaluation harness (`fixed threshold (>80)` in `analytics/evaluation/`) as the
*lower-bound baseline*. It is also the rule the metric simulator itself uses to
inject spikes, which makes it the most honest possible reference point: Fortify
must beat the very definition its own test data was generated from, or the
statistical approach adds nothing.

---

## 2. Statistical process control

Statistical process control (SPC), originating with Shewhart's control charts
in manufacturing [3], reframes "is this point abnormal?" as "is this point
outside the expected variation of the process?". A point is flagged when it
falls more than *k* standard deviations from the mean — most commonly the
"three-sigma" rule. The z-score Fortify uses is exactly this idea applied
online to a rolling window of CPU readings.

SPC is attractive for the same reasons it has survived a century: it is
parameter-light (one threshold, *k*), interpretable (the z-score *is* the
explanation), and computationally negligible. Its assumptions, however, are
strong and routinely violated by real telemetry:

- **Normality.** The three-sigma heuristic assumes roughly Gaussian data.
  CPU utilisation is bounded [0, 100], often skewed, and multi-modal across
  workloads.
- **Stationarity.** Mean and variance are assumed stable over the window;
  diurnal and seasonal load break this.
- **Self-contamination / masking.** Because the mean and standard deviation are
  computed *from the same window that contains the anomalies*, a cluster of
  large spikes inflates the standard deviation and pulls the mean toward
  itself, shrinking every z-score and hiding the very anomalies it should
  expose. This is the classic masking effect [4].

The standard mitigation is to replace mean/standard-deviation with robust
estimators — the median and the median absolute deviation (MAD) — giving the
"modified z-score" [4]. Robust statistics tolerate a fraction of contaminating
points before the estimate breaks down, directly addressing masking.

**Relevance to Fortify.** Fortify's production detector
(`analytics/anomaly_detection.py`) is a classic mean/standard-deviation z-score
with `|z| > 2.0`. The known masking weakness is not hand-waved away: the
robust MAD variant is implemented as a baseline (`robust z-score (MAD)`) and
the harness's Experiment D specifically measures recall degradation under
increasing contamination. This lets the report state the limitation *and* quantify
it, rather than claim the method is unconditionally adequate.

---

## 3. Time-series and machine-learning anomaly detection

Beyond SPC lies a large literature on learned anomaly detection, surveyed
comprehensively by Chandola et al. [5]. The approaches most relevant to
infrastructure telemetry fall into three families:

- **Forecasting residuals.** Fit a time-series model (Holt-Winters,
  ARIMA, or the decomposition behind Facebook's Prophet [6]) and flag points
  whose observed value departs from the forecast. This captures seasonality
  that plain SPC cannot, at the cost of model fitting and seasonality
  specification.
- **Isolation-based methods.** Isolation Forest [7] isolates points by random
  partitioning; anomalies, being few and different, are isolated in fewer
  splits. It is unsupervised, near-linear, makes no distributional assumption,
  and is the de-facto ML baseline for tabular anomaly detection.
- **Deep / reconstruction methods.** Autoencoders and LSTM-based detectors
  learn a model of "normal" and flag high reconstruction error. Benchmarking
  efforts such as the Numenta Anomaly Benchmark [8] show these can outperform
  simpler methods on complex streams, but they demand substantially more data,
  tuning, and compute, and they sacrifice the interpretability that operations
  teams value.

A recurring and uncomfortable finding in this literature is that sophisticated
detectors do not reliably beat simple ones: several studies report that
well-tuned thresholds or classical statistics are competitive with deep models
on many real workloads [8], and that reported deep-learning gains are often
fragile to evaluation methodology.

**Relevance to Fortify.** This body of work justifies *not* reaching for a deep
model. Fortify includes scikit-learn's Isolation Forest [7] as a baseline —
making good on the "scikit-learn baseline models" line in the tech stack — but
keeps the z-score as the shipped detector because, for a single bounded metric
over a short window, the added complexity of a learned model is not justified
by the evaluation results. The harness's Experiment C reports this comparison
on both "clear" and "subtle" anomaly tiers so the claim is evidenced, not
asserted. PyTorch/LSTM detectors are correctly scoped as *future work* in the
tech stack rather than over-engineered into the capstone.

---

## 4. Health scoring and AIOps

Raising per-metric anomalies is necessary but not sufficient for operators, who
need a fleet-level summary of "what should I look at first?". Two strands of
prior art inform Fortify's health score:

- **Commercial AIOps and APM.** Datadog's Watchdog, Dynatrace's Davis, and New
  Relic's applied-intelligence layer all combine anomaly detection with
  automated grouping and severity ranking [9]. They are powerful but
  proprietary, opaque (the scoring logic is not published), and priced for
  enterprise scale. The broader AIOps paradigm — coined by Gartner — is
  surveyed academically by Notaro et al. [10], who note that *explainability*
  and *reproducible evaluation* remain weak points across the field.
- **Composite scoring / service-health indices.** Aggregating several
  normalised indicators into one 0–100 score is standard practice (Google's
  SRE "error budget" and SLO framework [2] is the canonical operational
  example). The well-known risk is that an opaque weighted sum can be gamed or
  can hide a critical sub-signal behind healthy-looking averages, so the
  weighting must be justified and the components must remain individually
  visible.

**Relevance to Fortify.** Fortify's health score (`analytics/scoring.py`) is a
deliberately transparent composite: 40 % anomaly, 30 % stability (inverse
variance), 30 % historical (inverse mean load), each normalised to [0, 1] and
reported alongside the final number rather than hidden behind it. The choice of
an interpretable weighted score over a proprietary black box is a direct
response to the explainability gap identified in [10]. To avoid the
"unjustified weights" critique, the harness's Experiment E performs *construct
validation* — checking each component moves monotonically with its design
intent — so the report can defend the 40/30/30 split as behaving as designed,
with the rationale itself recorded as an ADR (see `docs/design-decisions.md`).

---

## 5. LLM-assisted operations

The newest strand is the use of large language models to summarise incidents
and explain telemetry in natural language. Early studies and industry reports
show LLMs can accelerate root-cause analysis and lower the expertise barrier
for interpreting alerts [11], and reliability research frames the surrounding
trade-offs — hallucination, latency, and the need to ground generation in real
data [12].

The honest assessment from this literature is that LLM explanations are an
*assistive presentation layer*, not a detector. They must be grounded in
deterministic signals (here, the z-score and component scores) and must fail
safe when the model is unavailable, or they risk fabricating plausible but
wrong explanations.

**Relevance to Fortify.** Fortify uses an open-source LLM strictly for
*explanation and summarisation* of results the statistical layer has already
produced — never to decide whether something is anomalous. This separation
keeps the detection path deterministic and testable (it is what the evaluation
harness exercises) while still delivering the operator-facing benefit reported
in [11]. It also matches the grounding discipline urged in [12].

---

## 6. Summary: the gap Fortify addresses

The prior art leaves a specific gap for a student-scale, self-hosted AIOps
project:

- Static thresholds (Section 1) are transparent but rigid.
- Commercial AIOps suites (Section 4) are capable but proprietary, opaque, and
  not reproducibly evaluable.
- Deep anomaly detectors (Section 3) are powerful but data-hungry and hard to
  interpret, and frequently fail to beat simpler methods on single-metric
  workloads.

Fortify occupies the middle ground: an **interpretable statistical detector**
with a **transparent composite health score** and a **grounded LLM explanation
layer**, the whole pipeline **reproducibly evaluated** against named baselines
(`analytics/evaluation/`). The contribution is not a novel algorithm but a
defensible, end-to-end, fully open and measured integration — and, crucially,
an honest account of where the simple method's assumptions break, backed by
quantitative evidence rather than assertion.

---

## References

[1] Prometheus Authors, "Alerting rules," *Prometheus Documentation*. [Online].
Available: https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/

[2] B. Beyer, C. Jones, J. Petoff, and N. R. Murphy, Eds., *Site Reliability
Engineering: How Google Runs Production Systems*. Sebastopol, CA, USA:
O'Reilly Media, 2016.

[3] W. A. Shewhart, *Economic Control of Quality of Manufactured Product*.
New York, NY, USA: D. Van Nostrand Company, 1931.

[4] B. Iglewicz and D. C. Hoaglin, *How to Detect and Handle Outliers*, vol. 16
of *The ASQC Basic References in Quality Control*. Milwaukee, WI, USA: ASQC
Quality Press, 1993.

[5] V. Chandola, A. Banerjee, and V. Kumar, "Anomaly detection: A survey,"
*ACM Computing Surveys*, vol. 41, no. 3, pp. 1–58, Jul. 2009,
doi: 10.1145/1541880.1541882.

[6] S. J. Taylor and B. Letham, "Forecasting at scale," *The American
Statistician*, vol. 72, no. 1, pp. 37–45, 2018,
doi: 10.1080/00031305.2017.1380080.

[7] F. T. Liu, K. M. Ting, and Z.-H. Zhou, "Isolation forest," in *Proc. 8th
IEEE Int. Conf. Data Mining (ICDM)*, Pisa, Italy, 2008, pp. 413–422,
doi: 10.1109/ICDM.2008.17.

[8] S. Ahmad, A. Lavin, S. Purdy, and Z. Agha, "Unsupervised real-time anomaly
detection for streaming data," *Neurocomputing*, vol. 262, pp. 134–147, 2017,
doi: 10.1016/j.neucom.2017.04.070.

[9] Datadog, Inc., "Watchdog: automated anomaly and outlier detection,"
*Datadog Documentation*. [Online]. Available:
https://docs.datadoghq.com/watchdog/

[10] P. Notaro, J. Cardoso, and M. Gerndt, "A survey of AIOps methods for
failure management," *ACM Transactions on Intelligent Systems and Technology*,
vol. 12, no. 6, pp. 1–45, 2021, doi: 10.1145/3483424.

[11] Y. Chen et al., "Automatic root cause analysis via large language models
for cloud incidents," in *Proc. 19th European Conf. Computer Systems
(EuroSys)*, Athens, Greece, 2024, pp. 674–688, doi: 10.1145/3627703.3629553.

[12] Z. Ji et al., "Survey of hallucination in natural language generation,"
*ACM Computing Surveys*, vol. 55, no. 12, pp. 1–38, 2023,
doi: 10.1145/3571730.
