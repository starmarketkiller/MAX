#!/usr/bin/env python3
"""NEXUS Orchestrator V1 Core - RESULT_PACKET_V1 builder (Fase 9 del task).

Il confidence model (§8 dell'architettura) e' implementato qui per davvero,
non lasciato all'autovalutazione del worker: HIGH richiede TUTTI e 6 i
segnali positivi (verifier PASS, test PASS, artifact attesi tutti presenti,
schema valido, provenance coerente, nessuna contraddizione con un artifact
canonico gia' esistente) - un singolo 'sembra corretto' non basta mai."""
import json
import os
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

with open(os.path.join(CONTRACTS_DIR, "result-packet.schema.json"), encoding="utf-8") as f:
    RESULT_PACKET_SCHEMA = json.load(f)


def compute_confidence(*, verifier_ran, verifier_passed, tests_ran, tests_passed, tests_failed,
                       expected_artifacts, artifacts_created, schema_valid, provenance_ok,
                       contradicts_canonical):
    """Ritorna (confidence, signals_dict) - i 6 segnali sono sempre riportati
    esplicitamente, mai nascosti dentro un singolo verdetto opaco."""
    signals = {
        "verifier_pass": bool(verifier_ran and verifier_passed),
        "tests_pass": bool(tests_ran and tests_failed == 0 and tests_passed > 0),
        "artifacts_complete": all(a in artifacts_created for a in expected_artifacts),
        "schema_valid": bool(schema_valid),
        "provenance_ok": bool(provenance_ok),
        "no_contradiction": not contradicts_canonical,
    }
    if not verifier_ran:
        return "UNKNOWN", signals
    if all(signals.values()):
        return "HIGH", signals
    if signals["verifier_pass"] or signals["tests_pass"]:
        return "MEDIUM", signals
    return "LOW", signals


def build_result_packet(*, task_id, executor, start_time, end_time, files_read, files_changed,
                        tools_or_commands, artifacts_created, tests_ran, tests_passed,
                        tests_failed, verifier_ran, verifier_passed, verifier_errors,
                        commit, push_status, decision, confidence, limitations,
                        unresolved_issues, suggested_next_tasks, escalation_needed,
                        escalation_reason=None, escalation_target_tier=None):
    packet = {
        "task_id": task_id, "executor": executor, "start_time": start_time, "end_time": end_time,
        "files_read": files_read, "files_changed": files_changed,
        "tools_or_commands": tools_or_commands, "artifacts_created": artifacts_created,
        "tests": {"ran": tests_ran, "passed": tests_passed, "failed": tests_failed},
        "verifier": {"ran": verifier_ran, "passed": verifier_passed, "errors": verifier_errors},
        "commit": commit, "push_status": push_status, "decision": decision,
        "confidence": confidence, "limitations": limitations,
        "unresolved_issues": unresolved_issues, "suggested_next_tasks": suggested_next_tasks,
        "escalation_needed": {"needed": escalation_needed, "reason": escalation_reason,
                             "target_tier": escalation_target_tier},
    }
    errors = validate(packet, RESULT_PACKET_SCHEMA)
    if errors:
        raise AssertionError(f"RESULT_PACKET_V1 non valido: {errors}")
    return packet


def now_iso():
    return datetime.now(timezone.utc).isoformat()
