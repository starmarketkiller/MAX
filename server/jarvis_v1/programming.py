"""Deterministic, fail-closed planning core for conversational repo work.

This module plans capabilities; it does not run shell commands, call providers,
push, or deploy. Execution remains owned by Queue/Router/Provider Connector and
Safe Auto Deploy.
"""
from __future__ import annotations

import json
import re

from orchestrator_v1.nxs_schema_validator import validate
from path_resolver import resolve_contracts_dir

PLAN_SCHEMA = json.loads((resolve_contracts_dir(__file__) /
                          "jarvis-programming-plan.schema.json").read_text(encoding="utf-8"))

_PROGRAMMING_WORDS = re.compile(
    r"\b(repo|codice|code|bug|fix|patch|test|commit|committalo|push|pushalo|ci|github|implementa|modifica|riprendi)\b", re.I)
_REFERENCE_WORDS = re.compile(r"\b(quello|quella|pushalo|committalo|riprendi|continua)\b", re.I)


def is_programming_request(text: str) -> bool:
    return bool(_PROGRAMMING_WORDS.search(text or ""))


def extract_repo_paths(text: str) -> list[str]:
    """Extract only explicit repo-like paths; ambiguity remains fail-closed."""
    matches = re.findall(r"(?<![\w.-])((?:server|frontend|contracts|scripts|docs)/[\w./*-]+)",
                         (text or "").replace("\\", "/"))
    return list(dict.fromkeys(match.rstrip(".,:;") for match in matches))


def _intent(text: str) -> str:
    value = (text or "").lower()
    if re.search(r"\b(push|pushalo)\b", value): return "PUSH"
    if re.search(r"\b(commit|committalo)\b", value): return "COMMIT"
    if re.search(r"\b(test|verifica)\b", value) and not re.search(
            r"\b(fix|patch|modifica|implementa|sistema|correggi)\b", value): return "TEST"
    if re.search(r"\b(riprendi|continua)\b", value): return "RESUME"
    if re.search(r"\b(fix|patch|modifica|implementa|sistema|correggi)\b", value): return "PATCH"
    return "INSPECT"


def _flags(text: str, intent: str) -> list[str]:
    value = (text or "").lower()
    flags = ["NO_DEPLOY"]
    if re.search(r"\b(solo test|test only)\b", value):
        flags += ["TEST_ONLY", "NO_PUSH"]
    elif re.search(r"\b(solo commit|commit only|non pushare|senza push)\b", value):
        flags += ["COMMIT_ONLY", "NO_PUSH"]
    elif intent != "PUSH":
        flags.append("NO_PUSH")
    return list(dict.fromkeys(flags))


def build_plan(text: str, *, last_task_id: str | None = None,
               allowed_paths: list[str] | None = None) -> dict:
    intent = _intent(text)
    explicit = re.search(r"\bTASK_[A-Z0-9_]+\b", text or "", re.I)
    task_id = explicit.group(0).upper() if explicit else (last_task_id if _REFERENCE_WORDS.search(text or "") else None)
    resolution = "EXPLICIT" if explicit else ("CONVERSATION_CONTEXT" if task_id else "NONE")
    flags = _flags(text, intent)
    push_enabled = intent == "PUSH" and "NO_PUSH" not in flags
    commit_enabled = intent in {"COMMIT", "PUSH"} and "TEST_ONLY" not in flags
    patch_enabled = intent in {"PATCH", "COMMIT", "PUSH", "RESUME"} and "TEST_ONLY" not in flags
    operations = ["READ", "INSPECT_CI"]
    if patch_enabled: operations.append("PATCH_WORKSPACE")
    operations.append("TEST")
    if commit_enabled: operations.append("COMMIT")
    if push_enabled: operations.append("PUSH")
    denied = [name for name in ("PUSH", "DEPLOY", "TRADING", "SECRETS")
              if name not in operations]
    stages = []
    for name, enabled, approval, boundary in (
        ("READ", True, False, "READ_ONLY_REPO"),
        ("INSPECT_CI", True, False, "READ_ONLY_GITHUB"),
        ("PATCH_WORKSPACE", patch_enabled, False, "WORKSPACE_ONLY"),
        ("TEST", True, False, "DECLARED_TEST_COMMANDS"),
        ("COMMIT", commit_enabled, False, "TASK_SCOPED_FILES"),
        ("PUSH", push_enabled, True, "APPROVAL_GATE"),
        ("DEPLOY_VIA_SAFE_AUTO_DEPLOY", False, True, "SAFE_AUTO_DEPLOY_ONLY"),
    ):
        stages.append({"name": name, "enabled": enabled, "requires_approval": approval,
                       "executor_boundary": boundary})
    plan = {
        "schema_version": 1, "intent": intent, "objective": (text or "").strip(),
        "reference": {"task_id": task_id, "resolution": resolution},
        "policy_flags": flags,
        "capability_scope": {"repository": "starmarketkiller/MAX",
                             "allowed_operations": operations,
                             "denied_operations": denied,
                             "allowed_paths": allowed_paths or []},
        "stages": stages,
        "routing_order": ["DETERMINISTIC", "LOCAL", "FREE_ONLINE", "CODEX"],
        "approval_required": "EXPLICIT_USER_APPROVAL" if push_enabled else "REVIEW_REQUIRED",
        "provenance": {"source": "JARVIS_MESSAGE_V1", "derived": True},
    }
    errors = validate(plan, PLAN_SCHEMA)
    if errors:
        raise ValueError(f"JARVIS_PROGRAMMING_PLAN_V1 invalid: {errors}")
    return plan
