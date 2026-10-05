"""Generic LocalTaskHandler for MINISTRAL_TASK_COMPILER_V1 templates.

ONE handler instance is shared across every bounded template registered in
ministral_task_compiler.TEMPLATES - looked up by task_record["action"]
(== template_id by convention, see service.py's registration loop). Adding
a future template (log_analysis_v1, test_failure_triage_v1, ...) never
requires a new handler class, only a new MinistralTaskTemplate.

For a read_only template (repo_inspection_v1 today - the only kind this
handler supports, see the guard in verify()) this handler NEVER writes to
disk, runs no shell command, and apply() always reports
touches_real_repo_files=False - core/orchestrator.py's _run_local already
skips the approval gate entirely in that case (nothing was mutated to
approve) and completes the task directly once verify() passes.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
ORCH = SERVER / "orchestrator_v1"
if str(ORCH) not in sys.path:
    sys.path.insert(0, str(ORCH))

from core.orchestrator import ApplyResult, LocalTaskHandler, VerifyResult  # noqa: E402
from path_resolver import resolve_project_root  # noqa: E402

from . import ministral_task_compiler as compiler


def _json_object(text):
    value = (text or "").strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.I)
        value = re.sub(r"\s*```$", "", value)
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("worker output must be a JSON object")
    return parsed


class BoundedLocalTaskHandler(LocalTaskHandler):
    def __init__(self, *, project_root=None):
        self.project_root = Path(project_root or resolve_project_root(__file__)).resolve()

    def _template_id(self, task_record):
        return (task_record.get("action_params") or {}).get("template_id") or task_record["action"]

    def build_prompt(self, task_record) -> str:
        return compiler.build_prompt(self._template_id(task_record), task_record,
                                     project_root=self.project_root)

    def verify(self, task_record, response_text) -> VerifyResult:
        template = compiler.TEMPLATES[self._template_id(task_record)]
        if not template.read_only:
            # Deliberately unimplemented: a write-capable template needs a
            # handler that copies to a sandbox workspace and bounds file
            # writes the way FreeCodingWorkerHandler does - never silently
            # treat it as read-only just because this is the generic path.
            return VerifyResult(False, errors=["BoundedLocalTaskHandler only supports "
                                               "read_only templates today"], is_logic_error=True)
        try:
            parsed = _json_object(response_text)
        except (ValueError, json.JSONDecodeError) as exc:
            return VerifyResult(False, errors=[f"{type(exc).__name__}: {exc}"], is_logic_error=True)
        errors = self._validate_output(template, task_record, parsed)
        if errors:
            return VerifyResult(False, errors=errors, is_logic_error=True)
        return VerifyResult(True, parsed_output=parsed)

    # REAL-SMOKE FIX (2026-10-05): bounds matched to the minimal prompt in
    # ministral_task_compiler.REPO_INSPECTION_V1 ("massimo 3 frasi"/"massimo
    # 5"/"massimo 3") - generous enough that a reasonable real answer always
    # passes, tight enough to reject a model that ignored the limit and
    # rambled (which is itself a useful verifier_result=FAILED signal for
    # delegation_report, not just a latency fix).
    MAX_SUMMARY_CHARS = 600
    MAX_FINDINGS = 5
    MAX_RISKS = 3
    MAX_ITEM_CHARS = 400

    @classmethod
    def _validate_output(cls, template, task_record, parsed):
        expected_keys = set(template.output_contract)
        if set(parsed) != expected_keys:
            return [f"output keys must be exactly {sorted(expected_keys)}, got {sorted(parsed)}"]
        errors = []
        summary = parsed.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            errors.append("summary missing or empty")
        elif len(summary) > cls.MAX_SUMMARY_CHARS:
            errors.append(f"summary exceeds {cls.MAX_SUMMARY_CHARS} chars")
        errors += cls._validate_string_list(parsed.get("findings"), "findings", cls.MAX_FINDINGS,
                                            cls.MAX_ITEM_CHARS)
        errors += cls._validate_string_list(parsed.get("risks"), "risks", cls.MAX_RISKS,
                                            cls.MAX_ITEM_CHARS)
        return errors

    @staticmethod
    def _validate_string_list(value, field_name, max_items, max_item_chars):
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            return [f"{field_name} must be a list of strings"]
        if len(value) > max_items:
            return [f"{field_name} exceeds {max_items} items"]
        if any(len(item) > max_item_chars for item in value):
            return [f"{field_name} has an item exceeding {max_item_chars} chars"]
        return []

    def apply(self, task_record, verify_result: VerifyResult) -> ApplyResult:
        # read_only templates never touch disk - no workspace, no write, no
        # shell command, no TaskQueue/SharedState mutation beyond the
        # ordinary state transition Orchestrator itself performs.
        # PERSIST_MINISTRAL_BOUNDED_OUTPUT_V1: the validated parsed_output
        # (verify() already checked it against the template's bounds) rides
        # in RESULT_PACKET_V1.artifacts_created, the one field _run_local
        # already carries through unmodified - no new storage.
        template_id = self._template_id(task_record)
        encoded = compiler.encode_bounded_output(template_id, task_record["task_id"],
                                                  verify_result.parsed_output)
        return ApplyResult(files_changed=[], artifacts_created=[encoded],
                           touches_real_repo_files=False, proposal_only=False)
