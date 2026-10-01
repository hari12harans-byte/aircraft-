from __future__ import annotations
import os, time, json, urllib.request, urllib.parse
from typing import Any, Optional
from .base import BaseProvider, ProviderStatus

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

class SupabaseProvider(BaseProvider):
    def __init__(self):
        self.url = SUPABASE_URL
        self.anon_key = SUPABASE_ANON_KEY
        self.service_key = SUPABASE_SERVICE_ROLE_KEY
        is_ready = bool(self.url and (self.anon_key or self.service_key))
        super().__init__("Supabase PostgreSQL & Realtime", is_configured=is_ready)

    def ping(self) -> dict[str, Any]:
        """Tests live connectivity to the configured Supabase project."""
        if not self.is_configured:
            return {
                "success": False,
                "provider": self.name,
                "status": ProviderStatus.DEMO.value,
                "connected": False,
                "message": "Supabase credentials not configured in environment. Operating in local SQLite mode."
            }

        key = self.service_key or self.anon_key
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "User-Agent": "YatraFlow-Supabase/2.2"
        }
        test_url = f"{self.url}/rest/v1/"

        try:
            req = urllib.request.Request(test_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                status_code = resp.status
            return {
                "success": True,
                "provider": self.name,
                "status": ProviderStatus.LIVE.value,
                "connected": True,
                "project_url": self.url,
                "http_status": status_code,
                "message": "Connected to Supabase PostgreSQL REST gateway successfully."
            }
        except Exception as ex:
            return {
                "success": False,
                "provider": self.name,
                "status": ProviderStatus.UNAVAILABLE.value,
                "connected": False,
                "project_url": self.url,
                "error": str(ex),
                "message": f"Could not reach Supabase endpoint: {str(ex)}"
            }

    def sync_record(self, table: str, record: dict[str, Any]) -> dict[str, Any]:
        """Inserts or updates a record into a Supabase table."""
        if not self.is_configured:
            return {"ok": False, "reason": "SUPABASE_NOT_CONFIGURED"}

        key = self.service_key or self.anon_key
        endpoint = f"{self.url}/rest/v1/{table}"
        data_bytes = json.dumps(record).encode("utf-8")
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
            "User-Agent": "YatraFlow-Supabase/2.2"
        }

        try:
            req = urllib.request.Request(endpoint, data=data_bytes, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return {"ok": True, "status": resp.status}
        except Exception as ex:
            return {"ok": False, "error": str(ex)}
