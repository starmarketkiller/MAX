"""Versioned settings/profile contract shared by backend consumers."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "contracts" / "settings.schema.json").read_text(encoding="utf-8"))
DEFAULT_ARTIFACT = json.loads((ROOT / "contracts" / "default-settings.json").read_text(encoding="utf-8"))
SCHEMA_VERSION = DEFAULT_ARTIFACT["schema_version"]
DEFAULT_SETTINGS = DEFAULT_ARTIFACT["settings"]
PROPERTIES = SCHEMA["properties"]["settings"]["properties"]


class SettingsValidationError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("invalid settings")


def validate_settings(values, *, partial=True):
    if not isinstance(values, dict):
        raise SettingsValidationError([{"field": "$", "code": "type", "message": "expected object"}])
    errors = []
    clean = {}
    for key, value in values.items():
        rule = PROPERTIES.get(key)
        if rule is None:
            errors.append({"field": key, "code": "unknown", "message": "unknown setting"})
            continue
        expected = rule["type"]
        valid = (expected == "boolean" and isinstance(value, bool)) or \
                (expected == "object" and isinstance(value, dict)) or \
                (expected == "integer" and isinstance(value, int) and not isinstance(value, bool)) or \
                (expected == "number" and isinstance(value, (int, float)) and not isinstance(value, bool))
        if not valid or (expected in ("number", "integer") and not math.isfinite(float(value))):
            errors.append({"field": key, "code": "type", "message": f"expected finite {expected}"})
            continue
        if expected == "object":
            bad = [name for name, enabled in value.items() if not isinstance(name, str) or not isinstance(enabled, bool)]
            if bad:
                errors.append({"field": key, "code": "type", "message": "expected string-to-boolean map"})
                continue
        if expected in ("number", "integer"):
            if "minimum" in rule and value < rule["minimum"]:
                errors.append({"field": key, "code": "minimum", "message": f"minimum is {rule['minimum']}"})
            if "exclusiveMinimum" in rule and value <= rule["exclusiveMinimum"]:
                errors.append({"field": key, "code": "exclusiveMinimum", "message": f"must be greater than {rule['exclusiveMinimum']}"})
            if "maximum" in rule and value > rule["maximum"]:
                errors.append({"field": key, "code": "maximum", "message": f"maximum is {rule['maximum']}"})
        clean[key] = value
    if not partial:
        for key in DEFAULT_SETTINGS:
            if key not in clean:
                errors.append({"field": key, "code": "required", "message": "setting is required"})
    if errors:
        raise SettingsValidationError(errors)
    return clean


def canonical_checksum(settings):
    payload = json.dumps(settings, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def version_profile(profile, previous=None, *, created_by="operator"):
    settings = profile.get("params") or profile.get("settings") or {}
    version = int((previous or {}).get("version", 0)) + 1
    out = dict(profile)
    out.update({
        "profile_id": (previous or {}).get("profile_id") or profile.get("profile_id") or str(uuid4()),
        "version": version,
        "schema_version": SCHEMA_VERSION,
        "created_by": created_by,
        "status": "ACTIVE",
        "checksum": canonical_checksum(settings),
        "created_at": profile.get("created_at") or profile.get("saved_at") or datetime.now(timezone.utc).isoformat(),
    })
    return out
