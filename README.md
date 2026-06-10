# Project Fortify

[![CI](https://github.com/augustinecyr/project-fortify/actions/workflows/ci.yml/badge.svg)](https://github.com/augustinecyr/project-fortify/actions/workflows/ci.yml)

Project Fortify is a modular, AI-assisted AI-Ops solution designed to
improve infrastructure reliability and security posture for virtualized
environments.

The project focuses on delivering proactive infrastructure insights,
security posture scoring, and explainable recommendations through a
standalone, containerized system that can also be integrated into
existing enterprise platforms.

Project Fortify is developed as part of the ICT3902C Capstone Project
under the B.Eng. (Hons) in Applied Computing programme.

---

## Problem Context

Enterprise infrastructure teams face increasing challenges in managing
large-scale virtual environments, including:

- High manual effort in monitoring VM health
- Reactive incident management and slow root-cause analysis
- Security gaps caused by inconsistent patching and alert handling
- Difficulty demonstrating infrastructure and security posture to
  stakeholders and customers

These challenges often result in increased operational cost, higher risk
of service outages, and reduced visibility into system health.

---

## Project Objectives

Project Fortify aims to:

- Provide AI-assisted insights into VM resource health
- Detect anomalous infrastructure behaviour early
- Quantify infrastructure and security posture using scoring models
- Generate explainable, human-readable recommendations
- Operate as a standalone, containerized solution
- Serve as a reusable demo and customer-facing artefact

---

## Solution Overview

Project Fortify is designed as a **three-dimensional AI-Ops solution**:

### 1. Infrastructure Intelligence
- CPU metrics ingestion from monitoring systems
- Anomaly detection on resource utilisation
- VM health scoring
- Preventive recommendations to reduce outage risk

### 2. Security Intelligence
- Security and compliance metadata analysis
- Patch and alert resolution tracking
- Security posture scoring based on operational statistics

### 3. Scheduling & Orchestration (Future Phase)
- Scheduled health checks
- Automated reporting
- Foundation for future remediation workflows

Each dimension is modular and can be deployed independently or combined
as part of a unified solution.

---

## Security & Access Control

Project Fortify protects every API and dashboard surface with a layered
authentication and authorization model:

- **OAuth2 / JWT authentication** — token-based login; inactive accounts are
  rejected at the token endpoint.
- **Role-based access control (RBAC)** — three hierarchical roles,
  `viewer < operator < admin`, enforced per route (reads require *viewer*,
  ingestion/state changes require *operator*, user management requires *admin*).
- **Persisted audit trail** — security-relevant events (authentication,
  authorization, state changes) are written to the database *and* stdout, and
  are queryable via the operator-gated `GET /api/v1/audit` endpoint and a
  dedicated dashboard page.
- **User-management lifecycle** — admins can create users, change roles,
  activate/deactivate accounts, and reset passwords, with a last-admin
  lock-out guard.

See [`docs/design-decisions.md`](docs/design-decisions.md) (ADR-7, ADR-8) for
the rationale.

---

## Scope

### In Scope (Phase 1 MVP)
- CPU metrics analysis
- Anomaly detection
- Health scoring
- Security posture scoring (high-level)
- Read-only recommendations
- Single-tenant, demo-oriented deployment

### Out of Scope (Phase 1)
- Automated remediation actions
- Multi-tenant customer environments
- Production-grade SLA guarantees
- Proprietary data schema exposure

---

## Quick Start (Docker)

Requires Docker Desktop. No Python or manual setup needed.

```powershell
# 1. Copy environment template and fill in secrets
Copy-Item .env.example .env
# Edit .env: set POSTGRES_PASSWORD, SECRET_KEY, GROQ_API_KEY

# 2. Build and start all services
docker compose up --build -d

# 3. Verify everything is healthy
docker compose ps

# Access points:
# Dashboard: http://localhost:8501  (login: admin / admin123)
# API docs:  http://localhost:8000/docs
```

> The stack starts four containers: **postgres**, **redis**, **api**, and **frontend**.
> Migrations, admin user, and VM seed data run automatically on first boot.
> To run the smoke test: `.\scripts\smoke_test.ps1`

---

## Technical Approach (High-Level)

- **Application Layer**: FastAPI (Python)
- **AI & Analytics**: Statistical methods and baseline ML models
- **Generative AI**: Open-source LLMs for explanation and summarisation
- **Data Layer**: Relational storage for metrics and results
- **Containerisation**: Docker-based packaging
- **Deployment Model**: Standalone service, Kubernetes-ready

The system prioritises explainability, modularity, and ease of
integration.

---

## Testing & Continuous Integration

Quality is enforced through an automated test suite and CI:

- **Unit tests** — anomaly-detection and scoring logic, plus the Groq LLM
  wrapper contract (JSON mode, schema validation, fallback behaviour)
  (`api/tests/test_anomaly_detection.py`, `test_scoring.py`, `test_groq_client.py`).
- **Integration tests** — full API coverage including auth, RBAC, audit, and
  user management, run against a real PostgreSQL test database
  (`api/tests/integration/`).
- **Continuous integration** — every push and pull request to `main` and
  `develop` runs the full suite on GitHub Actions
  ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).
- **Offline evaluation harness** — a reproducible precision/recall/F1 study of
  the anomaly-detection and scoring pipeline, with baselines, threshold
  justification, and construct validation
  ([`analytics/evaluation/`](analytics/evaluation/), see
  [`RESULTS.md`](analytics/evaluation/RESULTS.md)).

```powershell
# Run the API test suite locally (requires a fortify_test PostgreSQL database)
cd api
pytest tests/ -v
```

---

## Documentation

| Document | Purpose |
| --- | --- |
| [`docs/problem-statement.md`](docs/problem-statement.md) | Problem analysis and motivation |
| [`docs/scope-definition.md`](docs/scope-definition.md) | Scope and requirements |
| [`docs/related-work.md`](docs/related-work.md) | Critical prior-art survey |
| [`docs/design-decisions.md`](docs/design-decisions.md) | Architecture decision records (ADRs) |
| [`docs/runbook.md`](docs/runbook.md) | Operations runbook |
| [`docs/observability.md`](docs/observability.md) | Logging and monitoring |
| [`docs/handover.md`](docs/handover.md) | Handover guide |
| [`docs/sprints/`](docs/sprints/) | Sprint-by-sprint development log |

---

## Development Methodology

Project Fortify follows an **Agile development approach**, including:

- Sprint X for planning, architecture, and setup
- Incremental sprint-based development
- Continuous documentation and evaluation

This approach supports controlled scope, iterative validation, and clear
progress tracking.

---

## Ethical and Security Considerations

- AI models provide advisory insights only
- No autonomous actions in Phase 1
- Synthetic or anonymised data used for development and demos
- No proprietary schemas or sensitive implementation details exposed