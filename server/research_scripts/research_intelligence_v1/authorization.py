"""Authorization for research-loop actions: AUTO_SAFE, APPROVAL_REQUIRED, PROHIBITED.

Enforced in code, fail-closed:
- an action kind not in CATALOG is PROHIBITED;
- dynamic checks can only make an action stricter, never looser;
- the loop executes only kinds that have a registered AUTO_SAFE runner
  (loop.AUTO_RUNNERS); APPROVAL_REQUIRED actions can only become an
  ACCEPT_ONLY proposal in the orchestrator queue (approval_bridge), which the
  dispatcher never claims; PROHIBITED actions are recorded as REFUSED.
"""
from __future__ import annotations

import re

from . import gates

AUTO_SAFE, APPROVAL_REQUIRED, PROHIBITED = "AUTO_SAFE", "APPROVAL_REQUIRED", "PROHIBITED"
ORDER = [AUTO_SAFE, APPROVAL_REQUIRED, PROHIBITED]

CATALOG = {
    # AUTO_SAFE: read what exists, check it, deduplicate, propose, small synthetic tests.
    "INGEST_AVAILABLE_REPORT": AUTO_SAFE,
    "REVIEW_EXPERIMENT": AUTO_SAFE,
    "INTEGRITY_CHECK": AUTO_SAFE,
    "DEDUP_CHECK": AUTO_SAFE,
    "GENERATE_PROPOSALS": AUTO_SAFE,
    "SYNTHETIC_DRY_RUN": AUTO_SAFE,
    # APPROVAL_REQUIRED: anything that spends real data, real compute or changes method.
    "RUN_EXPERIMENT_REAL_DATA": APPROVAL_REQUIRED,
    "EXPENSIVE_COMPUTE": APPROVAL_REQUIRED,
    "NEW_VARIANT": APPROVAL_REQUIRED,
    "METHOD_CHANGE": APPROVAL_REQUIRED,
    "RESTRICTED_DATASET_ACCESS": APPROVAL_REQUIRED,
    "EXTEND_FAMILY_BUDGET": APPROVAL_REQUIRED,
    # PROHIBITED: never executed, never even proposed for execution by the loop.
    "READ_PROTECTED_SPLIT": PROHIBITED,
    "MODIFY_PREREGISTERED_PARAMS": PROHIBITED,
    "LIVE_TRADING": PROHIBITED,
    "CHANGE_OPERATIONAL_RISK": PROHIBITED,
    "PROMOTE_STRATEGY": PROHIBITED,
    "MODIFY_SAFETY_COMPONENT": PROHIBITED,
}

SYNTHETIC_MAX_SECONDS = 60
SYNTHETIC_MAX_ROWS = 100_000
EXPENSIVE_SECONDS = 1800
SAFETY_FILES = re.compile(r"research_intelligence_v1/(gates|authorization|memory|approval_bridge)\.py|"
                          r"contracts/research-memory-v1|validation_access_policy|nexus_policy\.py")
LIVE = re.compile(r"MQL5/|NEXUS_EA|\.mq5|\.mqh|order_send|OrderSend|risk_percent|RiskPercent|live_account")


class Prohibited(Exception):
    pass


def _stricter(a, b):
    return a if ORDER.index(a) >= ORDER.index(b) else b


def classify(kind, params):
    """Return (mode, reasons). Pure function of the action."""
    params = params or {}
    reasons = []
    mode = CATALOG.get(kind)
    if mode is None:
        return PROHIBITED, [f"unknown action kind {kind!r}: fail-closed"]
    reasons.append(f"catalog: {kind} -> {mode}")

    split = (params.get("dataset") or {}).get("split") or params.get("split")
    if split in gates.protected_splits():
        mode = _stricter(mode, PROHIBITED)
        reasons.append(f"split {split} is one-shot: never read by the loop")
    if params.get("params_sha256") and params.get("preregistered_params_sha256") \
            and params["params_sha256"] != params["preregistered_params_sha256"]:
        mode = _stricter(mode, PROHIBITED)
        reasons.append("parameters differ from the preregistered ones")
    if params.get("target_lifecycle") == "SUPPORTED" or params.get("promote"):
        mode = _stricter(mode, PROHIBITED)
        reasons.append("promotion to confirmed evidence is a human decision")
    text = " ".join(str(v) for v in params.get("paths", []) + [params.get("description", "")])
    if SAFETY_FILES.search(text):
        mode = _stricter(mode, PROHIBITED)
        reasons.append("touches a safety component")
    if LIVE.search(text):
        mode = _stricter(mode, PROHIBITED)
        reasons.append("touches live trading or operational risk")

    if params.get("real_data"):
        mode = _stricter(mode, APPROVAL_REQUIRED)
        reasons.append("uses real market data")
    if (params.get("estimated_seconds") or 0) > (SYNTHETIC_MAX_SECONDS if kind == "SYNTHETIC_DRY_RUN"
                                                 else EXPENSIVE_SECONDS):
        mode = _stricter(mode, APPROVAL_REQUIRED)
        reasons.append(f"estimated {params['estimated_seconds']}s exceeds the automatic limit")
    if kind == "SYNTHETIC_DRY_RUN" and (params.get("rows") or 0) > SYNTHETIC_MAX_ROWS:
        mode = _stricter(mode, APPROVAL_REQUIRED)
        reasons.append("synthetic test larger than the automatic limit")
    if params.get("requires_authorization"):
        mode = _stricter(mode, APPROVAL_REQUIRED)
        reasons.append("dataset requires authorization")
    return mode, reasons


def require_auto_safe(kind, params):
    mode, reasons = classify(kind, params)
    if mode != AUTO_SAFE:
        raise Prohibited(f"{kind} is {mode}: {reasons}")
    return reasons
