#!/usr/bin/env python3
"""NEXUS Orchestrator V1 Core - CONTEXT_PACKET_V1 builder automatico
(Fase 10 del task).

Costruito SOLO quando il Router/retry_escalation decide un'escalation - mai
manualmente da Claude. Obiettivo pratico dichiarato dal task: quando Codex
torna disponibile, NEXUS gli consegna gia' problem/attempt/diff/tests/error/
artifact rilevanti/azione richiesta - non serve scrivere una task enorme da
zero."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
ORCH_DIR = os.path.dirname(CORE_DIR)
SERVER_DIR = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, SERVER_DIR)
from path_resolver import resolve_contracts_dir, resolve_project_root  # noqa: E402

ROOT = str(resolve_project_root(__file__))
CONTRACTS_DIR = str(resolve_contracts_dir(__file__))

sys.path.insert(0, ORCH_DIR)
from nxs_schema_validator import validate  # noqa: E402

with open(os.path.join(CONTRACTS_DIR, "context-packet.schema.json"), encoding="utf-8") as f:
    CONTEXT_PACKET_SCHEMA = json.load(f)


def _current_head():
    # Production images intentionally do not need a Git binary or .git tree.
    # Render/NEXUS build identity is the primary authority there.
    for name in ("RENDER_GIT_COMMIT", "NEXUS_GIT_SHA"):
        value = os.environ.get(name, "").strip().lower()
        if 7 <= len(value) <= 40 and all(char in "0123456789abcdef" for char in value):
            return value
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, cwd=ROOT, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return "0000000"
    value = proc.stdout.strip().lower()[:40]
    return value if proc.returncode == 0 and 7 <= len(value) <= 40 and all(
        char in "0123456789abcdef" for char in value) else "0000000"


def build_context_packet(*, objective, relevant_findings, canonical_artifacts, allowed_files,
                        exact_question, previous_attempts, failures, tests, constraints,
                        forbidden_actions, output_required, current_head=None):
    packet = {
        "objective": objective, "relevant_findings": relevant_findings,
        "canonical_artifacts": canonical_artifacts,
        "current_head": current_head or _current_head(), "allowed_files": allowed_files,
        "exact_question": exact_question, "previous_attempts": previous_attempts,
        "failures": failures, "tests": tests, "constraints": constraints,
        "forbidden_actions": forbidden_actions, "output_required": output_required,
    }
    errors = validate(packet, CONTEXT_PACKET_SCHEMA)
    if errors:
        raise AssertionError(f"CONTEXT_PACKET_V1 non valido: {errors}")
    return packet


def build_from_task_record(task_record, attempts_log, classification, target_tier):
    """Costruisce automaticamente un CONTEXT_PACKET_V1 a partire da un record
    del TaskQueue + dal log dei tentativi gia' fatti - questo E' il pattern
    'quando Codex torna, non riscriviamo la task da zero' richiesto dal
    task."""
    manifest = task_record["manifest"]
    previous_attempts = [f"Tentativo {i+1} (executor={a.get('executor')}): "
                        f"{a.get('summary', 'nessun sommario')}"
                        for i, a in enumerate(attempts_log)]
    failures = [str(e) for a in attempts_log for e in a.get("errors", [])]
    return build_context_packet(
        objective=manifest["objective"],
        relevant_findings=[f"Classificazione fallimento: {classification}",
                          f"Task originale: {manifest['title']}"],
        canonical_artifacts=[],
        allowed_files=manifest["files_allowed"],
        exact_question=f"[{classification}] {manifest['objective']} - i tentativi locali "
                      f"({len(attempts_log)}) sono falliti, serve intervento {target_tier}.",
        previous_attempts=previous_attempts, failures=failures,
        tests=[manifest.get("verifier", "")],
        constraints=[f"files_allowed={manifest['files_allowed']}",
                    f"files_forbidden={manifest['files_forbidden']}",
                    f"risk_level={manifest['risk_level']}"],
        forbidden_actions=["push automatico", "deploy", "modifiche strategie di trading",
                          "trading reale"],
        output_required=f"Risolvere: {manifest['objective']} rispettando success_criteria: "
                       f"{manifest['success_criteria']}",
    )


def build_review_packet(task_record, reject_reason):
    """CONTEXT_PACKET_V1 for the NEXUS Dynamic Specialist Review (a human
    REJECTed a proposed patch - a specialist must review it, never rewrite it
    from scratch). Reuses the exact same schema-validated contract as a
    normal escalation - canonical_artifacts stays a reference descriptor
    array by contract, so the proposed patch content itself (never lost -
    persisted on the record as `proposed_patch` when the patch first reached
    WAITING_APPROVAL) travels as a formatted previous_attempts entry, same as
    how a normal escalation already carries prior attempts as strings."""
    manifest = task_record["manifest"]
    proposed = task_record.get("proposed_patch") or {}
    changes = proposed.get("changes") or []
    patch_summary = "\n".join(
        f"--- {item['path']} ---\n{item['content']}" for item in changes) or "(nessuna patch disponibile)"
    test_results = proposed.get("test_results") or []
    test_summary = [f"{item.get('argv')}: returncode={item.get('returncode')}" for item in test_results]
    return build_context_packet(
        objective=manifest["objective"],
        relevant_findings=[f"Un umano ha rifiutato la patch proposta. Motivo: {reject_reason}",
                          f"Task originale: {manifest['title']}",
                          f"task_id (lineage): {task_record['task_id']}"],
        canonical_artifacts=[],
        allowed_files=manifest["files_allowed"],
        exact_question=f"La patch proposta per \"{manifest['objective']}\" e' stata rifiutata "
                      f"({reject_reason}). Rivedila e produci istruzioni correttive precise per "
                      "il worker locale - non riscriverla tu stesso, non eseguire nulla.",
        previous_attempts=[f"Patch rifiutata:\n{patch_summary}"],
        failures=[f"Reject: {reject_reason}"],
        tests=test_summary or [manifest.get("verifier", "")],
        constraints=[f"files_allowed={manifest['files_allowed']}",
                    f"files_forbidden={manifest['files_forbidden']}",
                    f"policy_flags={(task_record.get('action_params') or {}).get('execution_plan', {}).get('policy_flags', [])}",
                    f"risk_level={manifest['risk_level']}",
                    f"attempts_used={task_record.get('retry_count', 0)}"],
        forbidden_actions=["scrivere la patch tu stesso", "eseguire comandi", "push automatico",
                          "deploy", "modifiche strategie di trading", "trading reale"],
        output_required="Restituisci SOLO: problems_found (array), rework_instructions "
                       "(stringa), allowed_paths (array), required_tests (array), risks "
                       "(array). Il worker locale applichera' le tue istruzioni.",
    )
