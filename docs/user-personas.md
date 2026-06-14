# User Personas

## Persona 1: Infrastructure Operations Engineer
Responsibilities:
- Monitor VM performance
- Respond to alerts
- Prevent service outages

Pain Points:
- Alert fatigue
- Reactive troubleshooting
- Fragmented monitoring tools

Needs:
- Clear VM health indicators
- Early anomaly detection
- Actionable recommendations

Typical access role: **operator** (can ingest metrics and act on VM state)

---

## Persona 2: Security Operations Analyst
Responsibilities:
- Track compliance and patching
- Manage security alerts

Pain Points:
- Difficulty measuring security posture
- Manual reporting effort

Needs:
- Security hygiene scoring
- Visibility into response effectiveness
- Access to the audit trail for accountability

Typical access role: **operator** (reviews posture and the audit trail)

---

## Persona 3: Pre-Sales / Technical Consultant
Responsibilities:
- Demonstrate solutions to customers
- Explain technical value

Needs:
- Simple, visual demos
- Clear AI-driven narratives

Typical access role: **viewer** (read-only dashboards and reports)

---

> Access roles map to the three-tier RBAC model (viewer < operator < admin);
> see `docs/scope-definition.md` and ADR-7. Administrative user management is a
> distinct **admin** function not represented by these end-user personas.