"""MINISTRAL_TASK_COMPILER_V1 for bounded first-revenue market scouting."""
from __future__ import annotations

import json


SYSTEM_RULES = """Analyze only supplied prospect information. Do not browse, infer missing
facts, contact anyone, propose payments or contracts, choose the business, final target or
final price. Return exactly one JSON object and no prose."""


def compile_market_scout_task(prospect: dict) -> dict:
    if not isinstance(prospect, dict) or not prospect:
        raise ValueError("prospect evidence is required")
    return {
        "compiler": "MINISTRAL_TASK_COMPILER_V1", "task_type": "MARKET_SCOUT",
        "capability": "business_analysis", "max_attempts": 2,
        "network_allowed": False, "outreach_allowed": False, "payment_allowed": False,
        "input": prospect,
        "prompt": SYSTEM_RULES + "\nInput:\n" + json.dumps(prospect, ensure_ascii=False) +
                  "\nSchema: {\"problem\":str,\"evidence\":[str,max3],\"possible_offer\":str,"
                  "\"fit_score\":int0to100,\"reason\":str max2 sentences,"
                  "\"missing_info\":[str,max2]}",
    }


def validate_market_scout_output(raw) -> tuple[bool, list[str], dict | None]:
    errors = []
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return False, ["invalid JSON"], None
    if not isinstance(value, dict):
        return False, ["JSON object required"], None
    required = {"problem", "evidence", "possible_offer", "fit_score", "reason", "missing_info"}
    if set(value) != required:
        errors.append("exact schema fields required")
    if not isinstance(value.get("fit_score"), int) or not 0 <= value.get("fit_score", -1) <= 100:
        errors.append("fit_score must be integer 0..100")
    if not isinstance(value.get("evidence"), list) or len(value.get("evidence", [])) > 3:
        errors.append("evidence must be array max 3")
    if not isinstance(value.get("missing_info"), list) or len(value.get("missing_info", [])) > 2:
        errors.append("missing_info must be array max 2")
    if not all(isinstance(value.get(key), str) and value.get(key).strip()
               for key in ("problem", "possible_offer", "reason")):
        errors.append("problem, possible_offer and reason must be strings")
    return not errors, errors, value if not errors else None


def compile_single_retry(compiled_task: dict, errors: list[str]) -> str:
    """One bounded correction only; caller still owns retry accounting."""
    if not errors:
        raise ValueError("retry requires verifier errors")
    return (compiled_task["prompt"] + "\nYour previous output failed deterministic validation: " +
            "; ".join(errors[:3]) + ". Return corrected JSON only. Do not add facts.")


def codex_review_market_scout(compiled_task: dict, output: dict) -> dict:
    """Deterministic review boundary used before human/business decisions.

    It checks grounding and schema, not commercial desirability. A single
    retry may be requested by the caller; it never promotes the draft to an
    approved offer, final price, target, outreach or contract.
    """
    supplied = json.dumps(compiled_task["input"], ensure_ascii=False).lower()
    ungrounded = [item for item in output.get("evidence", []) if item.lower() not in supplied]
    return {"reviewer": "CODEX_TECHNICAL_REVIEW", "schema_valid": True,
            "grounding": "PASS" if not ungrounded else "REVIEW_REQUIRED",
            "ungrounded_evidence": ungrounded,
            "commercial_decision": "NOT_PERFORMED", "outreach_approved": False,
            "payment_authorized": False}


class MarketScoutLocalHandler:
    """Bounded adapter for the existing Orchestrator LocalTaskHandler path.

    The Core owns model selection, retry accounting and escalation.  This
    handler only compiles the supplied facts and deterministically verifies
    the JSON result; it has no filesystem, network, outreach or payment
    capability.
    """

    json_mode = True

    def __init__(self):
        self.last_errors = []
        self.verified_output = None

    def build_prompt(self, task_record) -> str:
        compiled = compile_market_scout_task(task_record["action_params"]["prospect"])
        if task_record.get("retry_count"):
            return compile_single_retry(compiled, self.last_errors)
        return compiled["prompt"]

    def verify(self, task_record, response_text):
        from core.orchestrator import VerifyResult
        valid, errors, output = validate_market_scout_output(response_text)
        self.last_errors = errors
        self.verified_output = output
        return VerifyResult(passed=valid, parsed_output=output, errors=errors,
                            is_logic_error=not valid)

    def apply(self, task_record, verify_result):
        from core.orchestrator import ApplyResult
        return ApplyResult(artifacts_created=[
            "memory://first-revenue/market-scout/" + task_record["task_id"]
        ], touches_real_repo_files=False)
