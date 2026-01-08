# Project Fortify

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