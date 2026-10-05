"""MINISTRAL_TASK_COMPILER_V1.

PERSIST_MINISTRAL_BOUNDED_OUTPUT_V1 (2026-10-05): the gate passed (2/3 real
smoke runs COMPLETED with verifier PASS) proved Ministral can do bounded
work on this hardware - but a verified summary/findings/risks that
disappears after verify() has near-zero practical value. No new storage is
introduced: the validated parsed_output is encoded as ONE string inside
RESULT_PACKET_V1.artifacts_created (already a plain array of strings per
contracts/result-packet.schema.json - the exact field _run_local already
populates from ApplyResult.artifacts_created, see
local_bounded_task_handler.py's apply()). encode_bounded_output/
decode_bounded_output below are the only new "mechanism", and it is pure
encode/decode over data that was always going to be in the Result Packet.

Claude (in sessions like this one) authors and refines bounded task
templates OFFLINE; NEXUS then delegates to Ministral through them
deterministically - zero live Claude API call anywhere in this path, now
or later, unless a separate explicit decision adds one. Every template
compiles into the EXACT same TASK_MANIFEST_V1 shape every other task-
creation path already produces - no new manifest schema, no second
routing policy. The local-vs-escalation decision is NOT made here: it is
core/router.py's existing route() function, driven entirely by the
required_capabilities/task_type/risk_level a template sets below. This
module only decides HOW to ask Ministral, never WHETHER to.

Prompt style is informed directly by JARVIS_MINISTRAL_ROUTER_V1's local
benchmark (2026-10-05, ministral-3:3b, i5-7200U, no GPU): a small model
only reliably respects an output schema when every enum/field is spelled
out explicitly and instructions stay short and imperative - see
build_prompt() below.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class MinistralTaskTemplate:
    template_id: str
    title: str
    task_type: str   # MUST be in the executing agent's allowed_task_types
                     # (agent_capability_registry_v1.json) - route()/find_capable_agents()
                     # already enforce this, nothing here bypasses it.
    work_type: str   # MUST be an existing review_matrix.py work_type - reused, not new.
    instructions: str
    output_contract: dict
    required_capabilities: tuple[str, ...]
    read_only: bool  # True => apply() never sets touches_real_repo_files - Orchestrator
                     # ._run_local then completes directly, no approval gate (nothing to approve).
    max_files: int = 6
    max_file_bytes: int = 20_000


TEMPLATES: dict[str, MinistralTaskTemplate] = {}


def register_template(template: MinistralTaskTemplate) -> None:
    TEMPLATES[template.template_id] = template


# repo_inspection_v1: deliberately the safest possible first template -
# read-only by construction (its own output_contract has no field capable
# of carrying a file write), no shell, no TaskQueue/SharedState mutation.
# work_type="routine_summary" already has review_required=False and
# producer_default="LOCAL_GENERALIST" in review_matrix.py - matches
# LOCAL_FAST_MINISTRAL3B's specialist_role exactly, confirmed before writing
# this, not assumed.
#
# REAL-SMOKE FIX (2026-10-05): the first version of this prompt embedded a
# JSON output_contract with a verbose, hand-written description as the
# VALUE of every field ("string - sintesi in italiano di cosa fanno questi
# file..."). Against the live local Ministral (ministral-3:3b, CPU-only,
# ~4 tok/s) every one of 3 real smoke runs exceeded the 180s budget
# core/orchestrator.py::_run_local already uses - never touched here, per
# explicit instruction not to change shared runtime for this fix. The
# contract below is deliberately minimal: a flat list of short strings
# instead of nested {path, note} objects (one less structural concept for a
# 3B model to track), explicit numeric caps instead of prose, and the
# prompt (build_prompt below) states the shape ONCE as a literal JSON
# skeleton instead of a described contract - no reasoning, no explanation,
# one objective per call.
REPO_INSPECTION_V1 = MinistralTaskTemplate(
    template_id="repo_inspection_v1",
    title="Repo inspection (read-only)",
    task_type="DOCUMENTATION",
    work_type="routine_summary",
    instructions=(
        "Leggi SOLO i file sotto. Non scrivere codice, non eseguire comandi, non spiegare "
        "il ragionamento.\n"
        "Rispondi SOLO con questo JSON, nessun altro testo prima o dopo:\n"
        '{"summary": "massimo 3 frasi", "findings": ["massimo 5 frasi brevi"], '
        '"risks": ["massimo 3 frasi brevi, puo essere vuoto []"]}'
    ),
    output_contract={"summary": "string", "findings": "array[string]", "risks": "array[string]"},
    required_capabilities=("summaries", "json_structured_output"),
    read_only=True,
    max_files=3,
    max_file_bytes=6_000,
)
register_template(REPO_INSPECTION_V1)


def compile_task(template_id, *, goal, relevant_paths, created_by, conversation_id=None,
                 constraints=None, prior_failures=None, verifier_feedback=None):
    """Builds a TASK_MANIFEST_V1 dict + (action, action_params) ready for
    Orchestrator.submit() - the exact same shape every other task-creation
    path in this codebase already produces. Returns data only; never
    touches TaskQueue/Ledger/filesystem itself."""
    template = TEMPLATES[template_id]
    task_id = f"TASK_{uuid.uuid4().hex[:12].upper()}"
    manifest = {
        "task_id": task_id, "title": template.title, "objective": goal,
        "task_type": template.task_type, "work_type": template.work_type,
        "priority": "NORMAL", "risk_level": "A1", "scientific_risk": "NONE",
        "code_risk": "NONE", "financial_risk": "NONE",
        "required_capabilities": list(template.required_capabilities),
        "deterministic_tools_available": False, "repo_scope": "task-scoped",
        "files_allowed": list(relevant_paths), "files_forbidden": [".env", "MQL5/**"],
        "dependencies": [], "blockers": [],
        "expected_artifacts": ["RESULT_PACKET_V1"],
        "success_criteria": [f"output conforme a {template_id} output_contract"],
        "verifier": f"ministral_task_compiler:{template_id}",
        "estimated_complexity": "SMALL", "estimated_runtime": "2m",
        "premium_allowed": False, "preferred_executor": "TIER1_LOCAL_CHEAP",
        "fallback_executors": [], "approval_required": "REVIEW_REQUIRED",
        "created_by": created_by, "created_at": _now_iso(),
        "tenant_id": "tenant-1", "account_scope_id": None,
    }
    action_params = {"template_id": template_id}
    if conversation_id:
        action_params["conversation_id"] = conversation_id
    if constraints:
        action_params["constraints"] = constraints
    if prior_failures:
        action_params["prior_failures"] = prior_failures
    if verifier_feedback:
        action_params["rework_instructions"] = verifier_feedback
    return manifest, template_id, action_params


def build_prompt(template_id, task_record, *, project_root):
    """The actual text sent to Ministral. REAL-SMOKE FIX (2026-10-05): no
    longer embeds a verbosely-described JSON output_contract - the required
    shape is stated ONCE, as a literal compact JSON skeleton, inside
    template.instructions. Files are plain delimited text, not JSON-escaped,
    to avoid spending tokens on escape noise. _run_local() calls
    ollama_worker.call_local_model() WITHOUT json_mode=True (see
    core/orchestrator.py, not touched here) - the model is relied on to
    follow 'Rispondi SOLO con questo JSON', same as every existing local
    task."""
    template = TEMPLATES[template_id]
    manifest = task_record["manifest"]
    root = Path(project_root).resolve()
    blocks = []
    for rel in manifest.get("files_allowed", [])[:template.max_files]:
        try:
            full = (root / rel).resolve()
            if full.is_file() and root in full.parents and not full.is_symlink():
                content = full.read_text(encoding="utf-8")[:template.max_file_bytes]
                blocks.append(f"--- {rel} ---\n{content}")
        except (OSError, UnicodeDecodeError):
            continue
    rework = (task_record.get("action_params") or {}).get("rework_instructions")
    prefix = f"{rework}\n\n" if rework else ""
    return (prefix + template.instructions +
           f"\n\nOBIETTIVO: {manifest['objective']}\n\n" +
           "\n\n".join(blocks))


BOUNDED_OUTPUT_PREFIX = "ministral_bounded_output_v1:"


def encode_bounded_output(template_id, task_id, parsed_output):
    """The only new persistence mechanism this feature adds: one string,
    placed in RESULT_PACKET_V1.artifacts_created (see apply() in
    local_bounded_task_handler.py) - never a second storage, never a schema
    change. template_id/task_id are included so a consumer never needs the
    TaskQueue record just to know what it's looking at."""
    payload = {"template_id": template_id, "task_id": task_id, **parsed_output}
    return BOUNDED_OUTPUT_PREFIX + json.dumps(payload, ensure_ascii=False)


def decode_bounded_output(artifacts_created):
    """Scans a RESULT_PACKET_V1.artifacts_created list for an
    encode_bounded_output() entry and returns the decoded dict, or None if
    none is present (every other task type's artifacts_created - file
    paths, workspace dirs - never starts with BOUNDED_OUTPUT_PREFIX)."""
    for item in artifacts_created or []:
        if isinstance(item, str) and item.startswith(BOUNDED_OUTPUT_PREFIX):
            try:
                return json.loads(item[len(BOUNDED_OUTPUT_PREFIX):])
            except json.JSONDecodeError:
                return None
    return None
