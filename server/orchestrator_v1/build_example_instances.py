#!/usr/bin/env python3
"""Orchestrator V1 - un esempio concreto per ognuno dei 6 schemi
contracts/*.schema.json, validato contro lo schema stesso con
nxs_schema_validator (fail-closed: se un esempio non valida, il
builder solleva)."""
import json
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
CONTRACTS_DIR = os.path.join(ROOT, "contracts")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, ORCH_DIR)
from nxs_schema_validator import validate_or_raise  # noqa: E402


def _load_schema(fname):
    with open(os.path.join(CONTRACTS_DIR, fname), encoding="utf-8") as f:
        return json.load(f)


def build():
    task_manifest = {
        "task_id": "TASK_PILOT_BACKFILL_TEMPORAL_EXIT_EFFICIENCY", "title": "Backfill demo",
        "objective": "Esempio di TASK_MANIFEST_V1 valido.", "task_type": "BACKFILL",
        "priority": "NORMAL", "risk_level": "A1", "scientific_risk": "LOW", "code_risk": "MEDIUM",
        "financial_risk": "NONE", "required_capabilities": ["python"],
        "deterministic_tools_available": True, "repo_scope": "server/research_scripts/phase7/phase7_28/",
        "files_allowed": ["server/research_scripts/phase7/phase7_28/**"], "files_forbidden": ["MQL5/**"],
        "dependencies": [], "blockers": [], "expected_artifacts": ["exit_efficiency_v1.json"],
        "success_criteria": ["hash canonico deterministico"], "verifier": "verify_phase_7_28.py",
        "estimated_complexity": "SMALL", "estimated_runtime": "10-30m", "premium_allowed": False,
        "preferred_executor": "TIER2_LOCAL_STRONG", "fallback_executors": ["TIER3_CLAUDE"],
        "approval_required": "AUTO", "created_by": "TIER3_CLAUDE_SPEC_PHASE",
        "created_at": "2026-09-28T00:00:00Z", "tenant_id": "tenant-1", "account_scope_id": None,
    }

    agent_capability_registry = {
        "schema_version": 1,
        "agents": [
            {"agent_id": "local-qwen25-7b", "provider": "local-ollama",
            "model_or_runtime": "qwen2.5:7b-instruct-q4_K_M", "local_or_remote": "LOCAL",
            "capabilities": ["json_output", "tool_calling", "python", "summarization"],
            "coding_ability": "MODERATE", "scientific_reasoning": "BASIC", "browser_access": False,
            "terminal_access": True, "file_access": "READ_WRITE", "github_access": False,
            "vault_access": "READ_WRITE", "mt5_access": "NONE", "max_concurrency": 1,
            "cost_class": "FREE", "quota_state": "OFFLINE", "availability": "OFFLINE",
            "trust_level": "SANDBOXED", "allowed_task_types": ["BACKFILL", "DOCUMENTATION", "MAINTENANCE"],
            "forbidden_task_types": ["DEPLOY", "MARKET", "MT5_RUN"],
            "specialist_role": "LOCAL_GENERALIST", "integration_status": "NOT_CONFIGURED"},
            {"agent_id": "claude-sonnet-5", "provider": "anthropic",
            "model_or_runtime": "claude-sonnet-5", "local_or_remote": "REMOTE",
            "capabilities": ["json_output", "tool_calling", "python", "scientific_reasoning",
                            "causal_reasoning"], "coding_ability": "STRONG",
            "scientific_reasoning": "STRONG", "browser_access": True, "terminal_access": True,
            "file_access": "READ_WRITE", "github_access": True, "vault_access": "READ_WRITE",
            "mt5_access": "RUN_MANAGEMENT", "max_concurrency": 1, "cost_class": "EXPENSIVE_PREMIUM",
            "quota_state": "AVAILABLE", "availability": "ONLINE", "trust_level": "FULLY_TRUSTED",
            "allowed_task_types": ["RESEARCH", "CODE", "MARKET", "MT5_RUN", "MAINTENANCE"],
            "forbidden_task_types": [],
            "specialist_role": "SCIENTIFIC_RESEARCHER", "integration_status": "NOT_CONFIGURED"},
        ],
    }

    context_packet = {
        "objective": "Esempio di CONTEXT_PACKET_V1.",
        "relevant_findings": ["LIQ_SWEEP ha gia' exit_efficiency, BREAKOUT_ACC/ORDER_BLOCK no."],
        "canonical_artifacts": [{"source_artifact": "phase7_25/baseline_economics_v1.json",
                                "canonical_sha256": "99ebf2dc57cb95da" + "0" * 48,
                                "generated_at": "2026-09-28T00:00:00Z", "mode": "CANONICAL_ARTIFACT"}],
        "current_head": "227965be7b7c687d505e8da7f4380874341d24e9",
        "allowed_files": ["server/research_scripts/phase7/phase7_28/**"],
        "exact_question": "Scrivi build_exit_efficiency.py seguendo il pattern di phase7_25.",
        "previous_attempts": [], "failures": [], "tests": ["test_phase_7_28.py"],
        "constraints": ["nessuna modifica a phase7_21/phase7_22"], "forbidden_actions": ["deploy"],
        "output_required": "Un builder Python + JSON risultante.",
    }

    result_packet = {
        "task_id": "TASK_PILOT_BACKFILL_TEMPORAL_EXIT_EFFICIENCY", "executor": "local-qwen25-7b",
        "start_time": "2026-09-28T00:00:00Z", "end_time": "2026-09-28T00:20:00Z",
        "files_read": ["phase7_21/baseline_economics_v1.json"],
        "files_changed": ["phase7_28/build_exit_efficiency.py", "phase7_28/exit_efficiency_v1.json"],
        "tools_or_commands": ["python phase7_28/build_exit_efficiency.py"],
        "artifacts_created": ["phase7_28/exit_efficiency_v1.json"],
        "tests": {"ran": True, "passed": 4, "failed": 0},
        "verifier": {"ran": True, "passed": True, "errors": []},
        "commit": None, "push_status": "NOT_PUSHED", "decision": "BACKFILL_COMPLETED",
        "confidence": "MEDIUM", "limitations": ["primo tentativo locale, non ancora rivisto da un umano"],
        "unresolved_issues": [], "suggested_next_tasks": ["aggiornare cross_strategy_learning_packet"],
        "escalation_needed": {"needed": False, "reason": None, "target_tier": None},
    }

    nexus_event = {
        "event_id": "EVT_00000001", "event_type": "TASK_COMPLETED",
        "task_id": "TASK_PILOT_BACKFILL_TEMPORAL_EXIT_EFFICIENCY",
        "timestamp": "2026-09-28T00:20:00Z", "tenant_id": "tenant-1",
        "payload": {"executor": "local-qwen25-7b", "confidence": "MEDIUM"},
    }

    schemas_and_instances = [
        ("task-manifest.schema.json", task_manifest, "TASK_MANIFEST_V1"),
        ("agent-capability-registry.schema.json", agent_capability_registry, "AGENT_CAPABILITY_REGISTRY_V1"),
        ("context-packet.schema.json", context_packet, "CONTEXT_PACKET_V1"),
        ("result-packet.schema.json", result_packet, "RESULT_PACKET_V1"),
        ("nexus-event.schema.json", nexus_event, "NEXUS_EVENT_V1"),
    ]

    validated = {}
    for schema_file, instance, label in schemas_and_instances:
        schema = _load_schema(schema_file)
        validate_or_raise(instance, schema, label)
        validated[label] = {"schema_file": schema_file, "instance": instance, "valid": True}

    return validated


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "example_instances", "validated_examples_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  {len(payload)} esempi validati con successo: {list(payload.keys())}")


if __name__ == "__main__":
    main()
