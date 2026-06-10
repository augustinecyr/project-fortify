# Design Decisions (ADRs)

This document records the significant architectural and algorithmic decisions
in Project Fortify as short Architecture Decision Records (ADRs). Each ADR
captures the **context**, the **decision**, and the **consequences** —
including what was given up — so the choices can be defended rather than merely
described. Where a decision is backed by measurement, it cites the evaluation
harness (`analytics/evaluation/`, interpreted in
[`RESULTS.md`](../analytics/evaluation/RESULTS.md)); where it rests on prior
art, it cites [`related-work.md`](related-work.md).

| # | Decision | Status |
|---|----------|--------|
| [ADR-1](#adr-1-z-score-anomaly-detection-over-machine-learning) | Z-score anomaly detection over ML | Accepted |
| [ADR-2](#adr-2-z-score-threshold-of-20) | Z-score threshold of 2.0 | Accepted |
| [ADR-3](#adr-3-403030-health-score-weighting) | 40/30/30 health-score weighting | Accepted |
| [ADR-4](#adr-4-llm-as-an-explanation-layer-only) | LLM as explanation layer only | Accepted |
| [ADR-5](#adr-5-fastapi--streamlit--postgresql--redis-stack) | FastAPI + Streamlit + Postgres + Redis | Accepted |
| [ADR-6](#adr-6-synthetic-simulated-fleet-over-live-agents) | Synthetic simulated fleet | Accepted |
| [ADR-7](#adr-7-role-based-access-control-over-perimeter-only-access) | RBAC over perimeter-only access | Accepted |
| [ADR-8](#adr-8-persisted-audit-trail-alongside-stdout-logs) | Persisted audit trail (DB) alongside stdout logs | Accepted |

---

## ADR-1: Z-score anomaly detection over machine learning

**Context.** Fortify must flag anomalous points in a single bounded metric (CPU
%) over a short rolling window. The tech stack lists scikit-learn and PyTorch as
options, so a learned detector (Isolation Forest, autoencoder, LSTM) was on the
table.

**Decision.** Ship the classic mean/standard-deviation z-score
(`analytics/anomaly_detection.py`) as the production detector. Keep Isolation
Forest only as an evaluation baseline; defer deep models to future work.

**Rationale.**
- The anomaly-detection literature repeatedly finds that sophisticated detectors
  do not reliably beat simple statistics on single-metric workloads
  (`related-work.md` §3). Our own measurement agrees: on clear anomalies the
  z-score scores **F1 0.958 vs 0.257 for Isolation Forest**, which achieves high
  recall only by flagging almost everything (precision 0.148). See
  `RESULTS.md`, Experiment C.
- The z-score is interpretable — the score *is* the explanation — which is a
  prerequisite for the LLM explanation layer (ADR-4) and for operator trust.
- It needs no training data, no model artefact, and runs in microseconds.

**Consequences.** Accepted that the method is weak on *subtle* anomalies that
overlap normal variance (F1 ≈ 0.25, Experiment A) and degrades under heavy
contamination via masking (Experiment D). Both limitations are measured and
disclosed, and a robust MAD variant is implemented as the documented upgrade
path. Deep models remain genuinely future work, not an unmet promise.

---

## ADR-2: Z-score threshold of 2.0

**Context.** The z-score detector flags points where `|z| > threshold`. The
threshold trades precision against recall and must be chosen, not guessed.

**Decision.** Default `threshold = 2.0`.

**Rationale.** The threshold sweep (`RESULTS.md`, Experiment B) shows **F1 peaks
at exactly 2.0** on the hard (subtle) tier: precision rises monotonically and
recall falls monotonically with the threshold, and 2.0 is the empirical balance
point. It is also defensible on first principles — ≈ 2σ corresponds to the
conventional ~95 % coverage of a normal distribution.

**Consequences.** 2.0 optimises F1, i.e. it assumes precision and recall matter
equally. A deployment that prefers fewer false alarms can raise the threshold
toward 2.5–3.0; the sweep makes that trade-off explicit. The parameter is
exposed as an argument (`detect_anomalies(..., threshold=)`), so changing it
needs no code edit.

---

## ADR-3: 40/30/30 health-score weighting

**Context.** The health score (`analytics/scoring.py`) collapses three
normalised [0,1] signals — anomaly (inverted), stability (inverse variance),
historical (inverse mean load) — into one 0–100 number. The weights determine
what "healthy" means.

**Decision.** Weight anomaly **0.40**, stability **0.30**, historical **0.30**.

**Rationale.**
- *Acute over chronic.* An active anomaly is the strongest signal of a problem
  needing attention now, so it carries the largest single weight. Stability and
  historical load are slower-moving context and are weighted equally to each
  other.
- *Anomaly < 0.5.* The anomaly component is deliberately kept below half so a
  single noisy reading cannot unilaterally crater the score; the steadier
  components temper it.
- *Transparency over tuning.* The weights are round and few on purpose — an
  opaque, finely-tuned weighting invites the "gamed score" critique levelled at
  proprietary AIOps scores (`related-work.md` §4). Construct validation
  (`RESULTS.md`, Experiment E) confirms each component moves monotonically with
  its intended driver and the components remain individually visible in the API
  response.

**Consequences.** The weights are a defensible default, not an optimum derived
from labelled incident outcomes (no such labels exist for a simulated fleet).
Experiment E surfaces one explainable non-monotonicity at extreme variance,
caused by the detector's masking interacting with the anomaly component — a
documented consequence, not a hidden flaw. If real incident data became
available, the weights could be fitted; that is out of scope here.

---

## ADR-4: LLM as an explanation layer only

**Context.** The tech stack includes an open-source LLM (Mistral/Llama-class).
LLMs can summarise and explain, but they hallucinate and are non-deterministic.

**Decision.** Use the LLM **strictly to explain and summarise** results already
produced by the deterministic statistical layer. The LLM never decides whether
something is anomalous and never feeds back into the score.

**Rationale.** This keeps the entire detection/scoring path deterministic,
unit-testable, and reproducible (it is exactly what the evaluation harness
exercises) while still delivering the operator-facing benefit — faster
interpretation, lower expertise barrier — reported for LLM-assisted ops
(`related-work.md` §5). It also follows the grounding discipline that
mitigates hallucination: generation is conditioned on real computed numbers.

**Consequences.** The system must **fail safe** when the LLM is unavailable —
detection and scoring continue without explanations. Explanations are
presentation, not ground truth, and are labelled as such in the UI.

**Update (v1.1.1, 10 Jun 2026).** The fail-safe boundary is now enforced
mechanically rather than by prompt discipline alone: completions are requested
in Groq's JSON mode and validated against Pydantic schemas
(`api/app/utils/groq_client.py`), so a syntactically or structurally invalid
response is retried once and then replaced by the labelled fallback — it can
never be cached or rendered. Extra keys the model invents are dropped at the
same boundary. The model ID moved to configuration (`GROQ_MODEL`). LLM
narratives are now also embedded in exported reports (CSV/JSON), explicitly
marked as advisory, with the section omitted entirely when the LLM is
unavailable. Forward-looking output is framed as **trend-grounded risk
outlooks** rather than forecasts (prompts and UI labels both) — no forecasting
model backs the system, so it must not assert specific future values.

---

## ADR-5: FastAPI + Streamlit + PostgreSQL + Redis stack

**Context.** Fortify needs an API, a dashboard, durable storage, and caching,
deliverable at student/solo scale and demonstrable in a container.

**Decision.** FastAPI (API) · Streamlit (dashboard) · PostgreSQL (durable
metadata/results) · Redis (optional caching/rate-limit) · Docker Compose.

**Rationale.**
- **FastAPI** — async Python, native Pydantic validation and OpenAPI docs, and
  it shares the language of the analytics code, so detector and API live in one
  toolchain with no serialisation boundary.
- **Streamlit** — turns Python analytics directly into an interactive dashboard
  with no separate front-end build, the right cost/benefit for a solo capstone
  where the analytics, not bespoke UI, is the contribution.
- **PostgreSQL** — mature relational store for structured metrics and results;
  the obvious default for queryable, durable data.
- **Redis** — kept *optional* (caching and metric-ingest rate-limiting, per
  commit `2dacbf3`) so the core system runs without it; it relieves repeated
  computation without becoming a hard dependency.
- **Docker Compose** — one-command reproducible bring-up of the whole stack,
  and Kubernetes-ready for the scaling story.

**Consequences.** Streamlit trades fine-grained UI control for speed — accepted,
since the dashboard is a means of demonstrating the analytics, not the
deliverable itself. The stack is conventional and well-documented, which lowers
risk and aids assessment, at the cost of novelty (novelty is not a goal here).

---

## ADR-6: Synthetic simulated fleet over live agents

**Context.** Evaluating detection rigorously needs labelled anomalies. A real VM
fleet provides neither labels nor, at student scale, a fleet.

**Decision.** Drive the system from a metric simulator
(`data/generators/metrics_simulator.py`) — per-profile baseline + diurnal factor
+ sinusoidal wave + bounded variance, with injectable spikes.

**Rationale.** The simulator is realistic enough to exercise the full pipeline
and, decisively, it makes **supervised evaluation possible**: the evaluation
harness reuses the same normal model but turns random spikes off and re-injects
them at *known* indices, yielding ground-truth labels a real deployment usually
cannot obtain (`RESULTS.md`, and `evaluation/README.md` "Why synthetic data").

**Consequences.** Results characterise the detector against the simulator's
generative model; a real fleet may differ. This is the headline threat to
validity and is disclosed as such. The trade-off is justified: without labels
there is no precision/recall study at all, and a measured-but-synthetic
evaluation is stronger evidence than an unmeasured "real" one.

---

## ADR-7: Role-based access control over perimeter-only access

**Context.** Fortify is intended to run as a containerised application on an
internal Singtel VM. A tempting simplification is to treat *network access to
the VM* as the only access control — "whoever can reach the app can use it" —
relying on existing OAuth2/JWT authentication (Sprint 8) for identity but
granting every authenticated user full capability.

**Decision.** Add a thin **role-based access control** layer over the existing
JWT authentication: three hierarchical roles — **viewer** (read-only
dashboards), **operator** (+ mutate fleet state: ingest metrics, update VMs,
refresh AI cache), **admin** (+ user/role management) — enforced by a
`require_role` dependency (`app/auth/dependencies.py`). Mutating and
administrative actions are attributed to the acting user in the audit log
(`log_action`).

**Rationale.**
- *Perimeter-only access is an enterprise anti-pattern.* It conflates network
  reachability with authorization, provides no least-privilege or segregation
  of duties, and — critically for a telco's compliance posture — no record of
  *who did what*. It also breaks the moment more than one person or team shares
  the host.
- *Least privilege is the expected design.* In a Singtel context, read-only
  monitoring users should not be able to mutate fleet state, and only
  administrators should provision accounts. The three-tier split maps directly
  onto those duties.
- *Cheap, high-leverage extension.* It reuses the existing JWT path; the change
  is a role column, one dependency, and per-route wiring — small effort for a
  materially stronger security posture and capstone narrative (extends the
  Sprint 8 cyber module from authentication into authorization).

**Consequences.** Authorization state lives in the local user store, which is
the deployable stand-in for enterprise IAM. **In production this layer would
federate to Singtel's corporate identity provider via OIDC** rather than manage
local credentials and roles — the local store demonstrates the model without
requiring SSO integration for the capstone. Roles are read from the database
per request (not embedded in the JWT) so a role change takes effect immediately
without waiting for token expiry. **Machine identity is deliberately out of
scope:** metric-pushing agents currently authenticate as `operator` users; a
dedicated service-account / scoped API-key path is documented as the next
evolution rather than built now (see the API/runbook notes).

---

## ADR-8: Persisted audit trail alongside stdout logs

**Context.** The first cut of auditing emitted structured JSON to stdout only
(captured by Docker's `json-file` driver). That is fine for observability but
weak as a *security record*: it is rotated and capped (lost on rotation), not
queryable except by grepping container logs, and cannot answer "show
everything user X did last week."

**Decision.** Add an `audit_logs` table (actor, role, event, target, detail,
ip, success, timestamp) and persist **security-relevant events** to it —
authentication outcomes, authorization denials, and state changes (user
creation/update, password reset/change, VM update, cache clear). Expose them
via an operator-gated `GET /api/v1/audit` (paged, filterable). Per-request
access logs are *not* stored here — they remain stdout-only.

**Rationale.**
- *Queryable and retained.* A relational store makes the trail filterable by
  actor/event/time and durable beyond log rotation — what an examiner or a
  telco compliance review expects.
- *Scope discipline.* Storing every read request would bloat the table and
  bury the security signal; access logs belong in observability, not the audit
  record. Splitting the two keeps each fit for purpose.
- *Availability over strictness.* Audit writes are best-effort on their own
  short-lived session: a write failure is swallowed (with a stdout fallback)
  and never breaks the request, and the separate session means the event is
  recorded even if the business transaction later rolls back.

**Consequences.** The best-effort policy trades a small risk of a missed row
(under DB failure) for not coupling user-facing availability to the audit
write — an explicit, documented choice; a stricter "fail-closed" audit would be
the hardening step if regulatory requirements demanded it. Read access is set
at **operator** level to match the intended operator-facing audit view; note
the trail contains other users' usernames and IPs, so tightening this to
admin-only is the conservative alternative if that exposure is a concern.
Retention/rotation of the table is not yet automated (future work).
