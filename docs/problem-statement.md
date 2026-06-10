# Problem Statement

## Context

Enterprise infrastructure has consolidated onto virtualized and cloud
platforms, where a single operations team is responsible for fleets of
virtual machines that are provisioned, resized, and retired continuously.
Each VM emits a stream of resource and security telemetry, and the
operational questions asked of that telemetry — *is this machine healthy?
which machine should I look at first? why is this one misbehaving?* — have
not changed, but the volume and rate of the data answering them has outgrown
manual inspection.

## The problem

Operations teams face four compounding challenges:

1. **High manual effort in monitoring VM health.** The dominant practice is
   still the static threshold — alert when CPU exceeds a fixed cutoff. Fixed
   cutoffs cannot adapt to workloads that are legitimately bursty or
   diurnal, so they generate false positives on machines that are busy by
   design and false negatives on machines that are anomalous well below the
   cutoff. The resulting alert fatigue, and the manual tuning burden it
   creates, is a recurring theme in the site-reliability literature [1].

2. **Reactive incident handling and slow root-cause analysis.** Problems are
   typically discovered after impact, and diagnosis requires an experienced
   operator to correlate raw metrics across dashboards by hand. The
   expertise barrier is real: interpreting an alert correctly demands
   context (what is normal for *this* machine?) that junior operators do not
   have and senior operators cannot scale [2].

3. **Difficulty quantifying infrastructure and security posture.** Teams
   struggle to answer "how healthy is the fleet?" with a number they can
   defend. Commercial AIOps platforms do produce severity rankings and
   health indications, but their scoring logic is proprietary and opaque
   [3], which makes the numbers hard to audit, explain to stakeholders, or
   reproduce — explainability and reproducible evaluation are documented
   weak points across the AIOps field [4].

4. **Fragmented tooling across monitoring and security.** Resource health
   and security posture are usually watched in separate products with
   separate access models, forcing context switches during exactly the
   incidents where the two views need to be correlated, and leaving no
   single audit trail of who looked at or changed what.

Left unaddressed, these challenges raise operational cost (manual triage and
tuning), outage risk (late detection, slow diagnosis), and security exposure
(posture that is neither quantified nor consistently watched).

## Why existing approaches fall short

Static thresholds are transparent but rigid; commercial AIOps suites are
capable but opaque, priced for enterprise scale, and not reproducibly
evaluable; machine-learning detectors are powerful but data-hungry, hard to
interpret, and frequently fail to beat simpler statistical methods on
single-metric workloads. The full critical survey, with evidence for each of
these claims, is in [`docs/related-work.md`](related-work.md).

## Proposed solution

Project Fortify is an AI-assisted, modular AIOps platform that responds to
each challenge directly:

- **Adaptive statistical detection** (rolling z-score) replaces fixed
  cutoffs, flagging behaviour that is abnormal *for that machine* rather
  than abnormal against a global constant — reducing manual threshold
  tuning (challenge 1).
- **Grounded LLM explanations** translate every detection and trend into
  natural language for the operator, lowering the expertise barrier for
  diagnosis while keeping the detection path itself deterministic
  (challenge 2).
- **A transparent composite health score** (40 % anomaly / 30 % stability /
  30 % historical, components always shown alongside the total) quantifies
  fleet and per-VM posture with a number whose derivation is fully open and
  empirically validated (challenge 3).
- **A single dashboard** unifies resource health, security posture, and
  cost recommendations behind one authentication layer, with three-tier
  role-based access control and a persisted audit trail providing the
  accountability that fragmented tooling lacks (challenge 4).

## Success criteria

The solution is held to measurable standards rather than asserted benefits:

- Detection accuracy is quantified (precision/recall/F1) against named
  baselines on labelled synthetic data, with the detector's known failure
  modes measured rather than hidden (`analytics/evaluation/`).
- Every health score is decomposable into its components on screen — no
  unexplained numbers.
- The platform deploys as a single containerized command and is operable
  from its runbook by a non-author.
- All API access is authenticated, authorized by role, and security-relevant
  actions are audit-logged.

## Boundaries

Fortify is a capstone-scale system: it monitors a synthetic simulated fleet
rather than live agents, remains read-only (no automated remediation), and
is single-tenant. These boundaries, and how the scope evolved during
development, are recorded in [`docs/scope-definition.md`](scope-definition.md);
the rationale for each major design decision is in
[`docs/design-decisions.md`](design-decisions.md).

## References

[1] B. Beyer, C. Jones, J. Petoff, and N. R. Murphy, Eds., *Site Reliability
Engineering: How Google Runs Production Systems*. Sebastopol, CA, USA:
O'Reilly Media, 2016.

[2] Y. Chen et al., "Automatic root cause analysis via large language models
for cloud incidents," in *Proc. 19th European Conf. Computer Systems
(EuroSys)*, Athens, Greece, 2024, pp. 674–688, doi: 10.1145/3627703.3629553.

[3] Datadog, Inc., "Watchdog: automated anomaly and outlier detection,"
*Datadog Documentation*. [Online]. Available:
https://docs.datadoghq.com/watchdog/

[4] P. Notaro, J. Cardoso, and M. Gerndt, "A survey of AIOps methods for
failure management," *ACM Transactions on Intelligent Systems and
Technology*, vol. 12, no. 6, pp. 1–45, 2021, doi: 10.1145/3483424.
