# Scope Definition

Project Fortify's scope was defined in January 2026 as a deliberately small
Phase 1 MVP and then expanded incrementally as development surfaced new
requirements. This document records the original baseline, when and why each
expansion was pulled into scope, and the delivered scope as of v1.1.2
(June 2026). Each expansion is planned and recorded in detail in
`docs/sprints/`; design rationale lives in `docs/design-decisions.md`.

## Original Scope — Phase 1 MVP (January 2026)

In scope at project start:

- CPU metrics ingestion from monitoring sources
- Detection of anomalous resource behavior
- VM health scoring
- Security posture scoring based on operational statistics
- Read-only recommendations and insights
- Standalone, containerized deployment

Out of scope at project start:

- Automated remediation actions
- Multi-tenant customer isolation
- Production-grade SLA guarantees
- Proprietary data schema exposure

Deferred to Phase 2+ at project start:

- Automated actions via APIs
- Cost optimization recommendations
- Multi-tenant enablement
- Extended security analytics

## Scope Evolution

| When | Sprint / release | Scope added | Why it entered scope |
|------|------------------|-------------|----------------------|
| Jan – early Feb 2026 | Sprints 1–2 | Baseline MVP: FastAPI ingestion + health scoring, PostgreSQL schema, Streamlit dashboard | Original plan, delivered as scoped |
| Mid-Feb 2026 | Sprint 3 | Report export workflow and UI professionalism pass | Stakeholder feedback after the first working demo |
| Mid–late Feb 2026 | Sprint 4 | VM data model expanded from CPU-centric metrics to 30+ parameters with fleet-level analytics | Single-metric ingestion proved too thin to support meaningful health and security scoring |
| Late Feb 2026 (v0.4.0) | Sprint 5 | **Cost optimization recommendations** — originally Phase 2+ — plus the full security posture page (API endpoints landed 27 Feb) | Both pages existed as navigation stubs; a rule-based, read-only recommendations engine fit the MVP's "read-only insights" boundary, so the Phase 2 item was pulled forward |
| Mar – Apr 2026 (v0.5.0) | Sprint 6 | LLM-powered AI insights (Groq-hosted Llama 3): fleet analysis, per-VM anomaly explanations, trend narratives (integrated 21 Mar – 10 Apr) | Numeric scores alone lacked explainability; the LLM explains detections but never performs them (ADR-4) |
| 15 May 2026 (v0.6.0) | Sprint 7 | Integration test suite and an error-handling sweep across all pages | Quality bar for capstone submission: every endpoint testable with a single `pytest` command |
| 17–18 May 2026 (v0.7.0) | Sprint 8 | OAuth2/JWT bearer authentication across all API endpoints | Cybersecurity module requirement; the API could not remain unauthenticated |
| 18–19 May 2026 (v0.8.0) | Sprint 9 | Full-stack containerization — single `docker compose up` including the frontend | Completed the original "standalone, containerized deployment" goal, which until then covered only API/DB/Redis |
| 24–30 May 2026 (v1.0.0) | Sprint 10 | Security hardening (secure headers, audit logging), structured JSON observability, operations runbook and handover guide, persistent sessions | Production-readiness gaps identified while containerizing in Sprint 9 |
| 3–8 Jun 2026 (v1.1.0) | Post-v1.0 cycle | Three-tier RBAC (viewer/operator/admin), persisted audit trail with operator-facing audit UI, user-management lifecycle, offline evaluation harness (precision/recall/F1, threshold and baseline studies), CI pipeline | Authentication alone left no least-privilege or accountability story (ADR-7, ADR-8); detector accuracy had been asserted but never measured (`analytics/evaluation/`) |
| 10 Jun 2026 (v1.1.1) | Post-v1.0 cycle | LLM-layer hardening (Groq JSON mode, Pydantic-validated responses, configurable `GROQ_MODEL`), AI analysis embedded in exported reports, Export Report page reworked into an explicit select → generate → download flow, LLM "predictions" reframed as trend-grounded risk outlooks | LLM responses were parsed but never shape-validated, so a malformed analysis could be cached; the "explainable, stakeholder-facing reporting" objective was not actually served by report exports; forecast-style language overclaimed what the system can substantiate (ADR-4 update) |
| 14–18 Jun 2026 (v1.1.2) | Post-v1.0 cycle | Uniform API error-handling contract (single `{detail, request_id}` envelope, `X-Request-ID` on every response, global handlers mapping DB faults to 409/503/500 with no internal-detail leakage), plus a dependency-security pass raising `python-jose`, `requests`, and `python-multipart` floors above known CVEs | API error semantics were inconsistent and a few handlers leaked raw exception text, which is examiner-visible and fails the "no information disclosure" security bar; advisory-flagged transitive dependencies had to be lifted above their CVE-affected ranges (ADR-9) |

Two of the original Phase 2+ items were therefore delivered ahead of plan:
cost optimization recommendations (Sprint 5) and a substantial part of
extended security analytics (security posture page, RBAC, audit trail).

## Delivered Scope (v1.1.2, June 2026)

- Ingestion of 30+ VM parameters with continuous simulation of a synthetic fleet (ADR-6)
- Statistical anomaly detection (z-score, threshold justified empirically) and composite health scoring
- Security posture scoring and fleet-level security dashboard
- Read-only, rule-based cost optimization recommendations
- LLM-generated explanations and trend narratives (explanation only, never detection), schema-validated at the API boundary and embedded in exportable stakeholder reports
- OAuth2/JWT authentication, three-tier RBAC, persisted audit trail, user-management lifecycle
- Single-command containerized deployment with structured observability, runbook, and handover documentation
- Uniform API error-handling contract (consistent `{detail, request_id}` envelope, request-ID tracing, no internal-detail leakage) with dependencies held above known CVEs (ADR-9)
- Offline evaluation harness with reproducible accuracy experiments; CI running the full test suite

## Out of Scope (unchanged)

- Automated remediation actions — the platform remains read-only by design
- Multi-tenant customer isolation
- Production-grade SLA guarantees
- Proprietary data schema exposure
- Integration with a real (non-synthetic) fleet

## Future Scope (Phase 2+)

- Automated actions via APIs
- Multi-tenant enablement
- Service identity for machine-to-machine callers such as the metrics simulator (deferred in ADR-7)
- Real monitoring-source integration to replace the synthetic fleet
