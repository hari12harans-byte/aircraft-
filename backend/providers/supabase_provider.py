import os, time, json, urllib.request, urllib.parse
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv
from .base import BaseProvider, ProviderStatus

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / '.env')

class SupabaseProvider(BaseProvider):
    def __init__(self):
        super().__init__("Supabase PostgreSQL & Realtime", is_configured=self._check_configured())

    def _get_credentials(self) -> tuple[str, str, str]:
        url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
        anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        return url, anon_key, service_key

    def _check_configured(self) -> bool:
        url, anon_key, service_key = self._get_credentials()
        return bool(url and (anon_key or service_key))

    @property
    def url(self) -> str:
        return self._get_credentials()[0]

    @property
    def anon_key(self) -> str:
        return self._get_credentials()[1]

    @property
    def service_key(self) -> str:
        return self._get_credentials()[2]

    def ping(self) -> dict[str, Any]:
        """Tests live connectivity to the configured Supabase project."""
        url, anon_key, service_key = self._get_credentials()
        if not (url and (anon_key or service_key)):
            return {
                "success": False,
                "provider": self.name,
                "status": ProviderStatus.DEMO.value,
                "connected": False,
                "message": "Supabase credentials not configured in environment. Operating in local SQLite mode."
            }

        key = service_key or anon_key
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "User-Agent": "YatraFlow-Supabase/2.2"
        }

        # Step 1: Check Supabase Auth/Gateway health (accessible by both publishable and secret keys)
        connected = False
        gateway_version = "v2"
        auth_url = f"{url}/auth/v1/health"

        try:
            req = urllib.request.Request(auth_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    connected = True
                    try:
                        info = json.loads(resp.read().decode())
                        gateway_version = info.get("version", "v2")
                    except Exception:
                        pass
        except Exception:
            # Fallback test via REST root if auth health was unreachable
            try:
                rest_url = f"{url}/rest/v1/"
                req = urllib.request.Request(rest_url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=6) as resp:
                    if resp.status in (200, 204):
                        connected = True
            except Exception:
                connected = False

        if not connected:
            return {
                "success": False,
                "provider": self.name,
                "status": ProviderStatus.UNAVAILABLE.value,
                "connected": False,
                "project_url": url,
                "message": f"Could not reach Supabase endpoint at {url}. Please check project URL or network."
            }

        # Step 2: Check database schema status (PostgREST table availability)
        schema_ready = False
        tables_msg = "Local SQLite active."
        try:
            table_check_url = f"{url}/rest/v1/trips?select=id&limit=1"
            req = urllib.request.Request(table_check_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    schema_ready = True
                    tables_msg = "Remote PostgreSQL tables initialized and ready."
        except urllib.error.HTTPError as ex:
            if ex.code == 404 and "PGRST205" in ex.read().decode():
                schema_ready = False
                tables_msg = "Supabase connected. Remote tables pending initialization (run data/schema.sql in Supabase SQL Editor)."
            else:
                schema_ready = False
        except Exception:
            schema_ready = False

        return {
            "success": True,
            "provider": self.name,
            "status": ProviderStatus.LIVE.value,
            "connected": True,
            "project_url": url,
            "gateway_version": gateway_version,
            "schema_ready": schema_ready,
            "message": f"Connected to Supabase project ({url}). {tables_msg}"
        }

    def sync_record(self, table: str, record: dict[str, Any]) -> dict[str, Any]:
        """Inserts or updates a record into a Supabase table."""
        url, anon_key, service_key = self._get_credentials()
        if not (url and (anon_key or service_key)):
            return {"ok": False, "reason": "SUPABASE_NOT_CONFIGURED"}

        key = service_key or anon_key
        endpoint = f"{url}/rest/v1/{table}"
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
