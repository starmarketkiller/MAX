"""Canonical server-side tenant resolution for the current single-tenant runtime."""
import os
import re

_SAFE_TENANT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def canonical_tenant_id() -> str:
    value = os.environ.get("NEXUS_CANONICAL_TENANT_ID", "tenant-1").strip()
    if not _SAFE_TENANT.fullmatch(value):
        raise RuntimeError("NEXUS_CANONICAL_TENANT_ID is invalid")
    return value
