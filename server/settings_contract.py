"""Compatibility facade for the canonical PR7 settings schema and profiles."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

import settings_schema

SCHEMA = settings_schema.schema()
SCHEMA_VERSION = settings_schema.schema_version()
DEFAULT_SETTINGS = settings_schema.default_settings()
PROPERTIES = {record["key"]: record for record in SCHEMA["settings"]}
SettingsValidationError = settings_schema.SettingsValidationError


def validate_settings(values, *, partial=True):
    if not isinstance(values, dict):
        return settings_schema.validate(values)
    values = dict(values)
    strategies = values.pop("strategies", None)
    clean = settings_schema.validate(values, allow_unknown=False)
    if strategies is not None:
        if not isinstance(strategies, dict) or any(
            not isinstance(key, str) or not isinstance(value, bool)
            for key, value in strategies.items()
        ):
            raise SettingsValidationError([{"key": "strategies", "error": "attesa mappa stringa->boolean"}])
        clean["strategies"] = strategies
    return clean


def canonical_checksum(settings):
    payload = json.dumps(settings, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def version_profile(profile, previous=None, *, created_by="operator"):
    settings = profile.get("params") or profile.get("settings") or {}
    out = dict(profile)
    out.update({
        "profile_id": (previous or {}).get("profile_id") or profile.get("profile_id") or str(uuid4()),
        "version": int((previous or {}).get("version", 0)) + 1,
        "schema_version": SCHEMA_VERSION,
        "created_at": profile.get("created_at") or profile.get("saved_at") or datetime.now(timezone.utc).isoformat(),
        "created_by": created_by,
        "status": "ACTIVE",
        "checksum": canonical_checksum(settings),
    })
    return out
