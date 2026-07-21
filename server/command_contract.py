"""Canonical command identifiers, states and validation for PR8."""
from __future__ import annotations

from datetime import datetime, timezone

SCHEMA_VERSION = 1
COMMAND_TYPES = {"PING", "COMPILE_EA", "RESTART_MT5", "DEPLOY_FILES", "OPEN_CHART", "APPLY_TEMPLATE", "SHELL"}
STATUSES = {"PENDING", "LEASED", "RUNNING", "SUCCEEDED", "FAILED_RETRYABLE", "FAILED_FINAL", "EXPIRED", "CANCELLED"}
ACTION_TO_TYPE = {name.lower(): name for name in COMMAND_TYPES}
TYPE_TO_ACTION = {value: key for key, value in ACTION_TO_TYPE.items()}
MAX_ATTEMPTS = 3
LEASE_SECONDS = 45


class CommandValidationError(ValueError):
    pass


def command_type(value):
    normalized = str(value or "").strip().upper()
    if normalized not in COMMAND_TYPES:
        raise CommandValidationError(f"unknown command_type: {value!r}")
    return normalized


def iso_timestamp(epoch=None):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat() if epoch is not None else datetime.now(timezone.utc).isoformat()


def validate_target(target, *, require_host=False):
    if not isinstance(target, dict):
        raise CommandValidationError("target must be an object")
    allowed = {"instance_id", "host_id", "account_id", "symbol"}
    unknown = set(target) - allowed
    if unknown:
        raise CommandValidationError(f"unknown target fields: {sorted(unknown)}")
    if require_host and not target.get("host_id"):
        raise CommandValidationError("target.host_id is required")
    return {key: str(value) for key, value in target.items() if value not in (None, "")}
