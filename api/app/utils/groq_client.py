"""
Groq LLM client for Project Fortify.
Provides a singleton client and query_llm() wrapper with error handling and fallback.

Place at: api/app/utils/groq_client.py
"""
import json
import logging
from typing import Optional, Type

from groq import Groq
from pydantic import BaseModel, ValidationError

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_groq_client: Optional[Groq] = None


def get_groq_client() -> Optional[Groq]:
    """
    Return the shared Groq client, initialising it on first call.
    Returns None if GROQ_API_KEY is not configured — callers must handle this.
    """
    global _groq_client
    if _groq_client is None:
        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY is not set — LLM features will be unavailable.")
            return None
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
FLEET_SYSTEM_PROMPT = """You are an expert infrastructure reliability engineer analysing a fleet of virtual machines.
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
      "affected_vms": ["vm_id"]
    }
  ],
  "predictions": [
    {
      "vm_id": "string",
      "vm_name": "string",
      "prediction": "string — a risk outlook grounded in the observed trend, e.g. 'CPU usage is trending upward; review capacity'. Describe the risk and what to monitor — do not assert specific future values or outcomes as certain",
      "timeframe": "string — e.g. within 24 hours, within 7 days"
    }
  ]
}

Base every statement strictly on the metrics provided. Frame predictions as
risk outlooks derived from current trends, not as forecasts of specific values.
Do not include any text outside the JSON object. Do not wrap the JSON in markdown code blocks."""

VM_SYSTEM_PROMPT = """You are an infrastructure reliability engineer analysing a single virtual machine.
You will be given a JSON object of VM metrics. Respond ONLY with valid JSON in this exact structure:

{
  "health_explanation": "string — 1-2 sentences explaining the VM health score",
  "anomaly_explanation": "string — 1-2 sentences on anomalies detected, or state the VM looks normal",
  "risk_level": "critical|high|medium|low",
  "recommended_actions": [
    {
      "priority": "high|medium|low",
      "action": "string — one specific actionable step, max 20 words"
    }
  ],
  "prediction": "string — 1-2 sentence risk outlook for the next 24-48 hours, grounded in the observed trend; state the risk and what to monitor, do not assert specific future values or outcomes as certain"
}

Keep all string values brief. Maximum 3 items in recommended_actions.
Base every statement strictly on the metrics provided.
Do not include any text outside the JSON object. Do not wrap the JSON in markdown code blocks."""


# ---------------------------------------------------------------------------
# Response schemas — mirror the JSON structures demanded by the prompts above.
# Enum-like fields (severity, priority, risk_level) are plain strings on
# purpose: an off-vocabulary value should not discard an otherwise-good
# analysis. The frontend already defaults unknown values when rendering.
# ---------------------------------------------------------------------------
class FleetAnomaly(BaseModel):
    vm_id: str
    vm_name: str
    explanation: str
    severity: str


class FleetRecommendation(BaseModel):
    priority: str
    title: str
    description: str
    affected_vms: list[str] = []


class FleetPrediction(BaseModel):
    vm_id: str
    vm_name: str
    prediction: str
    timeframe: str


class FleetInsightsResponse(BaseModel):
    fleet_summary: str
    anomalies: list[FleetAnomaly] = []
    recommendations: list[FleetRecommendation] = []
    predictions: list[FleetPrediction] = []


class VMRecommendedAction(BaseModel):
    priority: str
    action: str


class VMAnalysisResponse(BaseModel):
    health_explanation: str
    anomaly_explanation: str
    risk_level: str
    recommended_actions: list[VMRecommendedAction] = []
    prediction: str


# ---------------------------------------------------------------------------
# Fallback responses (returned when Groq is unavailable or returns bad JSON)
# ---------------------------------------------------------------------------
FLEET_FALLBACK = {
    "fleet_summary": "AI analysis is temporarily unavailable. Please check your Groq API key and connectivity, then try again.",
    "anomalies": [],
    "recommendations": [
        {
            "priority": "high",
            "title": "AI Service Unavailable",
            "description": "Could not reach the Groq LLM service. Verify GROQ_API_KEY is set and the service is reachable.",
            "affected_vms": []
        }
    ],
    "predictions": []
}

VM_FALLBACK = {
    "health_explanation": "AI analysis is temporarily unavailable.",
    "anomaly_explanation": "AI analysis is temporarily unavailable.",
    "risk_level": "medium",
    "recommended_actions": [
        {"priority": "high", "action": "Verify GROQ_API_KEY is set and retry."}
    ],
    "prediction": "Unable to generate a risk outlook — AI service is unavailable."
}


# ---------------------------------------------------------------------------
# Core query function
# ---------------------------------------------------------------------------
def query_llm(
    user_prompt: str,
    system_prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    retries: int = 1,
    schema: Optional[Type[BaseModel]] = None,
) -> Optional[dict]:
    """
    Send a prompt to Groq and return the parsed JSON response.

    Uses Groq's JSON mode (response_format=json_object) so the completion is
    guaranteed to be syntactically valid JSON; `schema` additionally validates
    the *structure* so a wrong-shaped response is never returned to callers
    (or cached).

    Args:
        user_prompt:   The user-turn content (VM data as a JSON string).
        system_prompt: The system instructions (must mention JSON — required by JSON mode).
        model:         Groq model ID; defaults to settings.GROQ_MODEL.
        temperature:   Sampling temperature — keep low (0.2) for consistent JSON output.
        max_tokens:    Maximum tokens in the completion.
        retries:       How many times to retry on malformed/invalid JSON before returning None.
        schema:        Optional Pydantic model the parsed response must conform to.

    Returns:
        Parsed (and schema-validated, if given) dict on success,
        None on failure (caller should use fallback).
    """
    client = get_groq_client()
    if client is None:
        logger.error("Groq client is not initialised — GROQ_API_KEY missing.")
        return None

    model = model or settings.GROQ_MODEL

    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            )

            parsed = json.loads(response.choices[0].message.content)
            if schema is not None:
                # model_dump() also drops any extra keys the LLM invented,
                # so only the documented fields ever reach callers.
                parsed = schema.model_validate(parsed).model_dump()
            return parsed

        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(
                "Groq response failed %s (attempt %d/%d): %s",
                "schema validation" if isinstance(e, ValidationError) else "JSON parsing",
                attempt + 1, retries + 1, e
            )
            if attempt < retries:
                logger.info("Retrying LLM call...")
                continue
            logger.error("All retry attempts exhausted — returning None.")
            return None

        except Exception as e:
            logger.error("Groq API call failed: %s", e)
            return None

    return None