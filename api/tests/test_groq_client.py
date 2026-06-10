"""
Unit tests for the Groq client wrapper (app/utils/groq_client.py).

The Groq SDK is mocked at get_groq_client(), so no network calls are made.
These tests pin the contract added with JSON mode + schema validation:
a response is returned to callers only if it is valid JSON AND matches the
declared Pydantic schema; anything else yields None (-> caller fallback).
"""
import json
from unittest.mock import MagicMock, patch

from app.utils.groq_client import (
    FleetInsightsResponse,
    VMAnalysisResponse,
    query_llm,
)


def _mock_client_returning(content: str) -> MagicMock:
    """Build a fake Groq client whose completion returns `content`."""
    client = MagicMock()
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(content=content))]
    client.chat.completions.create.return_value = completion
    return client


VALID_FLEET_JSON = json.dumps({
    "fleet_summary": "All systems nominal.",
    "anomalies": [],
    "recommendations": [],
    "predictions": [],
})

VALID_VM_JSON = json.dumps({
    "health_explanation": "Healthy.",
    "anomaly_explanation": "No anomalies.",
    "risk_level": "low",
    "recommended_actions": [{"priority": "low", "action": "No action needed."}],
    "prediction": "Stable over the next 24-48 hours.",
})


class TestQueryLLM:
    def test_valid_response_passes_schema(self):
        client = _mock_client_returning(VALID_FLEET_JSON)
        with patch("app.utils.groq_client.get_groq_client", return_value=client):
            result = query_llm("data", "prompt", schema=FleetInsightsResponse)
        assert result is not None
        assert result["fleet_summary"] == "All systems nominal."

    def test_requests_json_mode(self):
        client = _mock_client_returning(VALID_FLEET_JSON)
        with patch("app.utils.groq_client.get_groq_client", return_value=client):
            query_llm("data", "prompt", schema=FleetInsightsResponse)
        kwargs = client.chat.completions.create.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}

    def test_wrong_shape_returns_none_after_retries(self):
        # Valid JSON, but missing every required field of the schema.
        client = _mock_client_returning(json.dumps({"unexpected": "shape"}))
        with patch("app.utils.groq_client.get_groq_client", return_value=client):
            result = query_llm("data", "prompt", retries=1, schema=FleetInsightsResponse)
        assert result is None
        assert client.chat.completions.create.call_count == 2  # initial + 1 retry

    def test_malformed_json_returns_none(self):
        client = _mock_client_returning("not json at all")
        with patch("app.utils.groq_client.get_groq_client", return_value=client):
            result = query_llm("data", "prompt", retries=0, schema=FleetInsightsResponse)
        assert result is None

    def test_extra_keys_are_dropped(self):
        # The LLM must not be able to smuggle fields (e.g. is_fallback) into
        # the result the router spreads into its response.
        payload = json.loads(VALID_VM_JSON)
        payload["is_fallback"] = "injected"
        client = _mock_client_returning(json.dumps(payload))
        with patch("app.utils.groq_client.get_groq_client", return_value=client):
            result = query_llm("data", "prompt", schema=VMAnalysisResponse)
        assert result is not None
        assert "is_fallback" not in result

    def test_no_schema_returns_parsed_dict(self):
        client = _mock_client_returning(json.dumps({"anything": "goes"}))
        with patch("app.utils.groq_client.get_groq_client", return_value=client):
            result = query_llm("data", "prompt")
        assert result == {"anything": "goes"}

    def test_missing_api_key_returns_none(self):
        with patch("app.utils.groq_client.get_groq_client", return_value=None):
            result = query_llm("data", "prompt", schema=FleetInsightsResponse)
        assert result is None
