"""
API client for Fortify backend integration.
"""
import os
import requests
import streamlit as st
from typing import Optional, Dict, List
import time
from session import clear_token


class FortifyAPIClient:
    """Client for interacting with Fortify API."""

    def __init__(self, base_url: str = os.getenv("API_BASE_URL", "http://localhost:8000")):
        self.base_url = base_url
    
    def _make_request(self, endpoint: str, method: str = "GET", token: str | None = None, retries: int = 3, **kwargs) -> Optional[Dict]:
        """
        Make HTTP request to API with error handling and retry logic.

        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            token: Bearer token for Authorization header
            retries: Number of retry attempts
            **kwargs: Additional arguments for requests

        Returns:
            Response JSON or None if error
        """
        url = f"{self.base_url}{endpoint}"
        if token:
            headers = kwargs.pop("headers", {})
            headers["Authorization"] = f"Bearer {token}"
            kwargs["headers"] = headers

        for attempt in range(retries):
            try:
                response = requests.request(method, url, timeout=15, **kwargs)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.ConnectionError:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                st.error("Cannot reach the API. Check that the stack is running.")
                return None
            except requests.exceptions.Timeout:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                st.error("Request timed out. API is taking too long to respond.")
                return None
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code
                if status == 401:
                    clear_token()
                    st.warning("Session expired. Please log in again.")
                    st.switch_page("views/login.py")
                    return None
                elif status == 429:
                    st.error("Too many requests. Please wait a moment and try again.")
                elif status >= 500:
                    st.error("The server encountered an error. Please contact support.")
                else:
                    st.error(f"❌ API Error {status}: {e.response.text}")
                return None
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
                return None
        
        return None
    
    @st.cache_data(ttl=300)
    def get_system_status(_self, token: str | None = None) -> Optional[Dict]:
        """Get system status."""
        return _self._make_request("/api/v1/status", token=token)

    @st.cache_data(ttl=180)
    def get_all_vms(_self, token: str | None = None) -> Optional[List[Dict]]:
        """Get all VMs from database."""
        result = _self._make_request("/api/v1/vms", token=token)
        if result:
            return result.get("vms", [])
        return None

    @st.cache_data(ttl=180)
    def get_vms_summary(_self, token: str | None = None) -> Optional[Dict]:
        """Get all VMs with their health metrics and status in one call."""
        return _self._make_request("/api/v1/vms/summary", token=token)

    @st.cache_data(ttl=120)
    def get_health_score(_self, vm_id: str, token: str | None = None) -> Optional[Dict]:
        """Get health score for a specific VM."""
        return _self._make_request(f"/api/v1/health/{vm_id}", token=token)

    @st.cache_data(ttl=120)
    def get_cpu_metrics(_self, vm_id: str, limit: int = 1440, token: str | None = None) -> Optional[Dict]:
        """Get CPU metrics for a specific VM."""
        return _self._make_request(f"/api/v1/metrics/cpu/{vm_id}?limit={limit}", token=token)

    @st.cache_data(ttl=60)
    def get_security_summary(_self, token: str | None = None) -> Optional[Dict]:
        """Get fleet-wide security aggregates."""
        return _self._make_request("/api/v1/security/summary", token=token)

    @st.cache_data(ttl=120)
    def get_optimization_recommendations(_self, token: str | None = None) -> Optional[Dict]:
        """Get rule-based VM optimization recommendations."""
        return _self._make_request("/api/v1/optimization/recommendations", token=token)

    def get_ai_insights(_self, token: str | None = None) -> Optional[Dict]:
        """
        Get AI-generated fleet-wide insights from Groq LLM.
        No @st.cache_data — caching is handled server-side in Redis (300s TTL).
        The frontend Analyse button busts the cache via DELETE /api/v1/ai/cache
        before calling this, so we always want a fresh HTTP call here.
        """
        return _self._make_request("/api/v1/ai/insights", token=token)

    def get_vm_analysis(_self, vm_id: str, token: str | None = None) -> Optional[Dict]:
        """
        Get AI-generated deep-dive analysis for a single VM.
        No @st.cache_data — caching handled server-side in Redis (120s TTL per vm_id).
        """
        return _self._make_request(f"/api/v1/ai/vm-analysis/{vm_id}", token=token)

    def clear_ai_cache(_self, token: str | None = None) -> Optional[Dict]:
        """Bust all server-side AI cache keys."""
        return _self._make_request("/api/v1/ai/cache", method="DELETE", token=token)

    def get_current_user(_self, token: str | None = None) -> Optional[Dict]:
        """Return the authenticated user's identity and role (/auth/me)."""
        return _self._make_request("/auth/me", token=token)

    def get_audit_events(
        _self,
        token: str | None = None,
        limit: int = 25,
        offset: int = 0,
        event: str | None = None,
        actor: str | None = None,
    ) -> Optional[Dict]:
        """
        Fetch a page of the persisted audit trail (operator/admin only).
        Not cached — the audit view is expected to reflect current activity.
        """
        params: Dict = {"limit": limit, "offset": offset}
        if event:
            params["event"] = event
        if actor:
            params["actor"] = actor
        return _self._make_request("/api/v1/audit", token=token, params=params)