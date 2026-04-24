"""
Groq LLM client for Project Fortify.
Provides a singleton client and query_llm() wrapper with error handling and fallback.

Place at: api/app/utils/groq_client.py
"""
import json
import logging
from typing import Optional

from groq import Groq
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
      "prediction": "string — what may happen if current trend continues",
      "timeframe": "string — e.g. within 24 hours, within 7 days"
    }
  ]
}

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
  "prediction": "string — 1-2 sentences on what may happen in the next 24-48 hours"
}

Keep all string values brief. Maximum 3 items in recommended_actions.
Do not include any text outside the JSON object. Do not wrap the JSON in markdown code blocks."""


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
    "prediction": "Unable to generate prediction — AI service is unavailable."
}


# ---------------------------------------------------------------------------
# Core query function
# ---------------------------------------------------------------------------
def query_llm(
    user_prompt: str,
    system_prompt: str,
    model: str = "llama-3.1-8b-instant",
    temperature: float = 0.2,
    max_tokens: int = 2048,
    retries: int = 1,
) -> Optional[dict]:
    """
    Send a prompt to Groq and return the parsed JSON response.

    Args:
        user_prompt:   The user-turn content (VM data as a JSON string).
        system_prompt: The system instructions.
        model:         Groq model ID.
        temperature:   Sampling temperature — keep low (0.2) for consistent JSON output.
        max_tokens:    Maximum tokens in the completion.
        retries:       How many times to retry on malformed JSON before returning None.

    Returns:
        Parsed dict on success, None on failure (caller should use fallback).
    """
    client = get_groq_client()
    if client is None:
        logger.error("Groq client is not initialised — GROQ_API_KEY missing.")
        return None

    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            )

            raw = response.choices[0].message.content.strip()

            # Strip accidental markdown fences if the model ignores instructions
            if raw.startswith("```"):
                lines = raw.split("\n")
                # Remove first and last fence lines
                raw = "\n".join(
                    line for line in lines
                    if not line.strip().startswith("```")
                )

            parsed = json.loads(raw)
            return parsed

        except json.JSONDecodeError as e:
            logger.warning(
                "Groq returned malformed JSON (attempt %d/%d): %s",
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