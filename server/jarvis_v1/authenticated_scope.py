"""Trusted single-tenant scope for authenticated Jarvis operations.

The browser never supplies tenant or owner.  Until sessions carry a vetted
tenant claim, NEXUS remains explicitly single-tenant and resolves its tenant
from server configuration only.
"""
from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
from nexus_tenant import canonical_tenant_id


@dataclass(frozen=True)
class AuthenticatedScope:
    user_id: str
    owner: str
    tenant_id: str


def resolve_authenticated_scope(user_id: str) -> AuthenticatedScope:
    user = str(user_id or "").strip()
    if not _SAFE_ID.fullmatch(user):
        raise PermissionError("authenticated user identity is invalid")
    return AuthenticatedScope(user_id=user, owner=f"jarvis:{user}",
                              tenant_id=canonical_tenant_id())


class EndpointRateLimiter:
    """Small single-process limiter for an authenticated mutation endpoint."""
    def __init__(self, limit: int = 10, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, [])
            hits[:] = [value for value in hits if now - value < self.window_seconds]
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True
