# Sprint 6: AI Insights — LLM-Powered Infrastructure Intelligence

**Duration:** 2 weeks  
**Goal:** Integrate Groq-hosted LLM (Llama 3) into the backend to deliver on-demand intelligent analysis, anomaly explanations, and predictive trend narratives. Surface results through a dedicated AI Insights page and a summary card on the home dashboard.

---

## Sprint Deliverables

1. **Groq LLM Backend Integration** — FastAPI service that constructs a structured prompt from live VM data and queries Groq's API.
2. **`/api/v1/ai/insights` Endpoint** — On-demand endpoint returning fleet-wide analysis, per-VM anomaly explanations, and trend predictions. Redis-cached to avoid redundant LLM calls.
3. **`/api/v1/ai/vm-analysis/{vm_id}` Endpoint** — Single-VM deep-dive analysis on demand.
4. **`ai_insights.py` Streamlit Page** — Dedicated AI Insights page with on-demand analysis trigger, structured output sections, and per-VM drill-down.
5. **Home Dashboard AI Card** — Condensed "latest insight" summary card on `home.py` linking to the full AI Insights page.
6. **Prompt Engineering** — Structured system prompt that instructs the LLM to act as an infrastructure analyst, with clear output schema for reliable parsing.

---

## Week 1: Backend — Groq Integration & Endpoints

### Days 1–2: Groq Client & Prompt Design

- [ ] Install `groq` Python SDK: `pip install groq`
- [ ] Add `GROQ_API_KEY` to environment variables and `settings.py`
- [ ] Create `api/app/utils/groq_client.py`:
  - `get_groq_client()` singleton
  - `query_llm(prompt, system_prompt, model="llama3-8b-8192")` function
  - Error handling — graceful fallback if Groq is unavailable
- [ ] Design system prompt: instructs model to act as an infrastructure reliability engineer, respond in structured JSON with keys: `fleet_summary`, `anomalies`, `recommendations`, `predictions`
- [ ] Test prompt manually against Groq playground

**Checkpoint:** Groq client returns structured JSON from a test VM dataset.

### Days 3–4: Fleet Insights Endpoint

- [ ] Create `api/app/routers/ai.py`
- [ ] `GET /api/v1/ai/insights` endpoint:
  - Fetches all VM data from DB
  - Builds a structured context payload (vm_id, name, health_score, security_score, cpu, memory, disk, alert_count, anomaly_detected, avg_cpu_24h, trend direction)
  - Calls Groq LLM with context + system prompt
  - Parses and validates JSON response
  - Returns structured insights object
  - Redis cache: 300s TTL (5 minutes) — LLM calls are expensive
- [ ] `GET /api/v1/ai/vm-analysis/{vm_id}` endpoint:
  - Single VM context — includes 24h CPU metrics history for richer analysis
  - Returns: health_explanation, anomaly_explanation, risk_level, recommended_actions, prediction
  - Redis cache: 120s TTL per vm_id
- [ ] Register both routes in `main.py`, bump version to `0.5.0`

**Checkpoint:** Both endpoints return valid structured responses from Groq.

### Day 5: Prompt Hardening & Fallbacks

- [ ] Add JSON validation — if LLM returns malformed response, retry once then return graceful fallback
- [ ] Add `analysis_timestamp` and `model_used` fields to response for transparency
- [ ] Test with edge cases: all VMs healthy, all VMs critical, mixed fleet
- [ ] Verify Redis caching works correctly — second call within TTL returns cached result

**Checkpoint:** Endpoints are reliable, cached, and fail gracefully.

---

## Week 2: Frontend — AI Insights Page & Home Integration

### Days 6–7: AI Insights Page

- [ ] Create `frontend/dashboard/pages/ai_insights.py`
- [ ] Page structure:
  - **Header** — consistent with other pages
  - **Analyse button** — triggers `GET /api/v1/ai/insights`, clears cache on click
  - **Fleet Summary section** — LLM's natural language fleet health narrative
  - **Anomalies section** — per-VM anomaly explanations rendered as cards
  - **Recommendations section** — LLM-generated recommendations (replaces rule-based logic visually)
  - **Predictions section** — trend narrative: "if current patterns continue..."
  - **Last analysed timestamp** — shows when the cached result was generated
- [ ] Add `get_ai_insights()` method to `api_client.py`
- [ ] Add `get_vm_analysis(vm_id)` method to `api_client.py`

**Checkpoint:** Page loads, button triggers analysis, all four sections render correctly.

### Days 8–9: VM Health Page Integration & Home Card

- [ ] Add "AI Analysis" expander to `vm_health_monitor.py`:
  - On expand, calls `/api/v1/ai/vm-analysis/{vm_id}`
  - Shows: health explanation, anomaly explanation, recommended actions, prediction
  - Cached per VM so repeated opens don't re-call Groq
- [ ] Add AI summary card to `home.py`:
  - Shows last generated fleet summary (one paragraph)
  - "Last analysed: HH:MM" timestamp
  - "View full analysis →" link to AI Insights page
  - If no analysis run yet: "Run your first analysis" prompt

**Checkpoint:** VM health page has AI drill-down, home page shows AI summary card.

### Day 10: Polish & Testing

- [ ] Verify Groq responses are consistent across multiple runs
- [ ] Test rate limit handling — Groq free tier limits apply
- [ ] Ensure Redis cache correctly prevents redundant API calls
- [ ] Update `commands.md` with `GROQ_API_KEY` setup instructions
- [ ] End-to-end test: full flow from button click to rendered insights

**Checkpoint:** Sprint ready for faculty demo.

---

## Technical Implementation Details

### Groq Model Selection

| Model | Speed | Context | Best for |
|---|---|---|---|
| `llama3-8b-8192` | Fastest | 8k tokens | Fleet summary, recommendations |
| `llama3-70b-8192` | Slower | 8k tokens | Deeper per-VM analysis |
| `mixtral-8x7b-32768` | Medium | 32k tokens | Large fleet context |

**Recommendation:** Use `llama3-8b-8192` for fleet insights (speed matters for demo), `llama3-70b-8192` for single-VM deep analysis.

### Context Payload Structure

```python
# What we feed to the LLM per VM
{
    "vm_id": "vm-001",
    "name": "web-server-prod-95",
    "status": "online",
    "health_score": 74,
    "security_score": 68,
    "current_cpu": 48.9,
    "current_memory": 58.2,
    "current_disk": 38.7,
    "avg_cpu_24h": 42.3,
    "peak_cpu_24h": 89.1,
    "alert_count": 2,
    "anomaly_detected": False,
    "open_vulnerabilities": 4,
    "critical_vulnerabilities": 1,
    "days_since_patch": 45,
    "firewall_enabled": True,
    "trend": "increasing"  # derived: avg_cpu_24h vs current_cpu
}
```

### System Prompt Design

```
You are an expert infrastructure reliability engineer analysing a fleet of virtual machines.
You will be given a JSON array of VM metrics. Respond ONLY with valid JSON in this exact structure:

{
  "fleet_summary": "string — 2-3 sentence plain English summary of overall fleet health",
  "anomalies": [
    {
      "vm_id": "string",
      "vm_name": "string",
      "explanation": "string — why this VM is flagged",
      "severity": "critical|warning|info"
    }
  ],
  "recommendations": [
    {
      "priority": "high|medium|low",
      "title": "string",
      "description": "string",
      "affected_vms": ["vm_id", ...]
    }
  ],
  "predictions": [
    {
      "vm_id": "string",
      "vm_name": "string",
      "prediction": "string — what may happen if current trend continues",
      "timeframe": "string — e.g. within 24 hours, within 7 days"
    }
  ]
}

Do not include any text outside the JSON object.
```

### New Files

```
api/app/utils/groq_client.py
api/app/routers/ai.py
frontend/dashboard/pages/ai_insights.py
```

### Modified Files

```
api/app/main.py              — register ai router, bump to v0.5.0
api/requirements.txt         — add groq
frontend/dashboard/utils/api_client.py   — add get_ai_insights(), get_vm_analysis()
frontend/dashboard/pages/home.py         — add AI summary card
frontend/dashboard/pages/vm_health_monitor.py  — add AI analysis expander
.env                         — add GROQ_API_KEY
```

---

## Success Criteria

- [ ] `GET /api/v1/ai/insights` returns structured JSON from Groq in under 10 seconds
- [ ] `GET /api/v1/ai/vm-analysis/{vm_id}` returns per-VM analysis
- [ ] Redis caching prevents redundant Groq calls within TTL window
- [ ] AI Insights page renders all four sections (summary, anomalies, recommendations, predictions)
- [ ] Home page shows condensed AI summary card
- [ ] VM Health page has working AI analysis expander
- [ ] Graceful fallback when Groq is unavailable or rate-limited
- [ ] `GROQ_API_KEY` documented in `commands.md`

---

## Risks & Mitigation

| Risk | Mitigation |
|---|---|
| Groq rate limits on free tier | Redis cache with 5-min TTL, manual trigger only |
| LLM returns malformed JSON | Retry once, then return structured fallback response |
| Inconsistent LLM output across runs | Strict system prompt with exact JSON schema, low temperature (0.2) |
| Groq API unavailable during demo | Cache last successful response, show "last analysed" timestamp |
| Context too large for token limit | Cap fleet context at 20 VMs × ~150 tokens each = ~3k tokens, well within 8k limit |

---

## Definition of Done

- [ ] Groq integration live and tested
- [ ] Both AI endpoints registered and returning valid responses
- [ ] AI Insights page fully built and navigable
- [ ] Home and VM health pages updated
- [ ] `commands.md` updated with Groq setup
- [ ] Code committed with meaningful commit messages
- [ ] Manually tested end-to-end with simulator running