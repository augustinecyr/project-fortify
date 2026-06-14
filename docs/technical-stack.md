# Technical Stack Overview

This document records the technology stack as **delivered** in v1.1.1
(June 2026). An aspirational stack was sketched in January 2026 at project
start; several of those choices were deliberately not pursued once the MVP
scope settled (see `docs/scope-definition.md`) and the design rationale was
recorded (see `docs/design-decisions.md`). The original sketch and the reasons
the delivered stack diverged from it are kept at the end of this document for
traceability.

A one-page visual of this stack is available at
[`application-stack.html`](application-stack.html) (open in a browser).

## Delivered Stack (v1.1.1)

### Application Layer
- FastAPI (Python 3.12), REST APIs
- Pydantic v2 / pydantic-settings for request validation and configuration
- Uvicorn ASGI server
- SQLAlchemy 2.0 ORM with Alembic migrations (psycopg 3 driver)
- slowapi rate limiting

### Authentication & Access Control
- OAuth2 password flow with JWT bearer tokens (python-jose)
- passlib / bcrypt password hashing
- Three-tier RBAC: viewer < operator < admin (ADR-7)
- Persisted audit trail of security and state-changing events (ADR-8)

### Analytics
- NumPy-based statistical anomaly detection (z-score, empirically justified
  threshold — ADR-1, ADR-2)
- Composite health and security scoring (weighted, ADR-3)
- Offline evaluation harness (`analytics/evaluation/`): precision/recall/F1,
  threshold and baseline studies

### Generative AI
- Groq-hosted Llama 3 via the `groq` SDK (ADR-5)
- JSON mode with Pydantic-validated response schemas; explanation and
  summarization only, never detection (ADR-4)

### Data Layer
- PostgreSQL (metadata and results)
- Redis (caching of LLM responses)

### Frontend
- Streamlit dashboard
- Plotly visualizations, Pandas data handling

### Infrastructure
- Docker Compose — single-command (`docker compose up`) deployment of API,
  frontend, PostgreSQL, and Redis

### Observability
- Structured JSON logging (python-json-logger)
- Operations runbook and handover documentation (`docs/`)

### Quality & CI
- pytest unit, integration, and smoke suites
- GitHub Actions CI running the full suite on push/PR

---

## Original Sketch (January 2026) and Why It Diverged

The following was the early, pre-implementation stack sketch. It is retained
for traceability; it does **not** describe the delivered system.

| Sketched (Jan 2026) | Delivered (v1.1.1) | Reason for divergence |
|---------------------|--------------------|-----------------------|
| scikit-learn baseline models, PyTorch for future enhancements, optional GPU | NumPy z-score detection | A transparent statistical detector outperformed the explainability and reproducibility needs of the MVP; ML training infrastructure was unjustified for the synthetic fleet (ADR-1) |
| Self-hosted open-source LLMs (Mistral / Llama) | Groq-hosted Llama 3 via API | Self-hosting an LLM was out of scope for a single-container deployment; a hosted inference API removed the GPU and serving burden (ADR-5) |
| Kubernetes-ready deployment | Docker Compose, single command | Kubernetes was disproportionate to a standalone capstone deployment; Compose satisfied the "standalone, containerized" goal (Sprint 9) |
| Prometheus metrics + Grafana | Structured JSON logging | A full metrics/visualization stack was not warranted; structured logs met the observability requirement for the project's scale (Sprint 10) |

Authentication, RBAC, the audit trail, and the evaluation harness were not
part of the original sketch at all; they entered scope later and are recorded
in `docs/scope-definition.md` and the corresponding ADRs.
