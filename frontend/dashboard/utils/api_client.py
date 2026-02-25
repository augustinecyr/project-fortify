"""
API client for Fortify backend integration.
"""
import requests
import streamlit as st
from typing import Optional, Dict, List
import time


class FortifyAPIClient:
    """Client for interacting with Fortify API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def _make_request(self, endpoint: str, method: str = "GET", retries: int = 3, **kwargs) -> Optional[Dict]:
        """
        Make HTTP request to API with error handling and retry logic.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            retries: Number of retry attempts
            **kwargs: Additional arguments for requests
        
        Returns:
            Response JSON or None if error
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(retries):
            try:
                response = requests.request(method, url, timeout=5, **kwargs)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.ConnectionError:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                st.error(f"❌ Cannot connect to API at {self.base_url}. Is the API running?")
                return None
            except requests.exceptions.Timeout:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                st.error("⏱️ Request timed out. API is taking too long to respond.")
                return None
            except requests.exceptions.HTTPError as e:
                st.error(f"❌ API Error: {e.response.status_code} - {e.response.text}")
                return None
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
                return None
        
        return None
    
    @st.cache_data(ttl=300)
    def get_system_status(_self) -> Optional[Dict]:
        """Get system status."""
        return _self._make_request("/api/v1/status")
    
    @st.cache_data(ttl=180)
    def get_all_vms(_self) -> Optional[List[Dict]]:
        """
        Get all VMs from database.
        Now uses the /vms endpoint which is much faster.
        """
        result = _self._make_request("/api/v1/vms")
        if result:
            return result.get("vms", [])
        return None
    
    @st.cache_data(ttl=180)
    def get_vms_summary(_self) -> Optional[Dict]:
        """
        Get all VMs with their health metrics and status in one call.
        This is optimized for dashboard performance.
        """
        return _self._make_request("/api/v1/vms/summary")
    
    @st.cache_data(ttl=120)
    def get_health_score(_self, vm_id: str) -> Optional[Dict]:
        """Get health score for a specific VM."""
        return _self._make_request(f"/api/v1/health/{vm_id}")
    
    @st.cache_data(ttl=120)
    def get_cpu_metrics(_self, vm_id: str, limit: int = 1440) -> Optional[Dict]:
        """
        Get CPU metrics for a specific VM.
        Default limit of 1440 = 24 hours at 1-minute intervals.
        """
        return _self._make_request(f"/api/v1/metrics/cpu/{vm_id}?limit={limit}")
    
    @st.cache_data(ttl=120)
    def get_memory_metrics(self, vm_id: str, limit: int = 1440) -> Optional[Dict]:
        """Fetch memory metrics for a VM (percentage usage over time)."""
        return self._make_request(f"/api/v1/metrics/memory/{vm_id}?limit={limit}")