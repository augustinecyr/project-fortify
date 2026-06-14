# User Flows

## Authentication & Access Flow
1. User authenticates via the login page (OAuth2 password flow, JWT issued)
2. The dashboard reads the user's role (viewer / operator / admin) once per session
3. Navigation and actions are gated by role: reads are available to viewers,
   ingest and state changes require operator, user management requires admin
4. Security and state-changing events are recorded in the audit trail

---

## Infrastructure Health Flow
1. CPU and VM metrics are ingested into Fortify (operator-gated endpoint)
2. Metrics are analysed for anomalies
3. Health score is computed
4. AI-generated explanation is produced
5. User views insights on dashboard

---

## Security Posture Flow
1. Security metadata is ingested
2. Compliance and patch statistics are analysed
3. Security score is generated
4. Trends are visualized over time
5. User reviews security posture

---

## Audit Review Flow
1. Operator or admin opens the Audit Trail page
2. Events are filtered by type and actor, with server-side pagination
3. User reviews the accountability record of access and state changes

---

## Demo / Executive View
1. User selects a VM (or the fleet view)
2. Combined health and security score is shown
3. AI explanation highlights risks and recommendations
4. Report is exported (CSV/JSON) with embedded AI analysis for stakeholders
