"""
Prometheus HTTP API client for querying instant and range vector metrics.
Uses standard library urllib for maximum portability and zero third-party dependencies.
"""

import json
import urllib.parse
import urllib.request
import urllib.error
from typing import Dict, List, Tuple, Any, Optional


class PrometheusClient:
    """Client for Prometheus v1 HTTP API."""

    def __init__(self, base_url: str = "http://localhost:9090", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _http_get(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Performs HTTP GET request against Prometheus API."""
        query_string = urllib.parse.urlencode(params)
        url = f"{self.base_url}{endpoint}?{query_string}"
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "Thesis-AnomalyDetector/1.0"}
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode("utf-8")
                payload = json.loads(error_body)
                error_msg = payload.get("error", str(e))
            except Exception:
                error_msg = str(e)
            raise ConnectionError(f"Prometheus API HTTP error {e.code}: {error_msg}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Failed to connect to Prometheus at {self.base_url}: {e.reason}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error querying Prometheus: {e}")

        if data.get("status") != "success":
            raise RuntimeError(f"Prometheus query failed: {data.get('error', 'unknown error')}")

        return data.get("data", {})

    def query_instant(self, query: str) -> List[Dict[str, Any]]:
        """
        Executes instant query (/api/v1/query).
        Returns raw list of metric results.
        """
        data = self._http_get("/api/v1/query", {"query": query})
        return data.get("result", [])

    def query_range(
        self,
        query: str,
        start_ts: float,
        end_ts: float,
        step: str = "15s"
    ) -> List[Tuple[float, float]]:
        """
        Executes range query (/api/v1/query_range).
        Returns a single flattened list of (timestamp, value) for the first series.
        """
        data = self._http_get(
            "/api/v1/query_range",
            {
                "query": query,
                "start": str(start_ts),
                "end": str(end_ts),
                "step": step
            }
        )
        results = data.get("result", [])
        if not results:
            return []

        # Extract values array from first series: [[unix_ts, "val_str"], ...]
        raw_values = results[0].get("values", [])
        series: List[Tuple[float, float]] = []
        for item in raw_values:
            try:
                ts = float(item[0])
                val = float(item[1])
                series.append((ts, val))
            except (ValueError, IndexError):
                continue

        return series
