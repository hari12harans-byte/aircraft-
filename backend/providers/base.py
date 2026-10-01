from __future__ import annotations
from enum import Enum
from typing import Any, Optional

class ProviderStatus(str, Enum):
    LIVE = "LIVE"
    DEMO = "DEMO"
    UNAVAILABLE = "UNAVAILABLE"

class BaseProvider:
    """Base class for all YatraFlow external provider abstractions."""
    def __init__(self, name: str, is_configured: bool = False):
        self.name = name
        self.is_configured = is_configured

    @property
    def status(self) -> ProviderStatus:
        return ProviderStatus.LIVE if self.is_configured else ProviderStatus.DEMO

    def get_metadata(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "status": self.status.value,
            "is_live": self.status == ProviderStatus.LIVE,
            "is_demo": self.status == ProviderStatus.DEMO
        }
