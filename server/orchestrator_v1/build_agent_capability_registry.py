#!/usr/bin/env python3
"""Local Model Bake-Off V1 - Fase 12: prima istanza REALE di
AGENT_CAPABILITY_REGISTRY_V1 (contracts/agent-capability-registry.schema.json),
popolata SOLO con capacita' dimostrate dal bake-off (bakeoff_scorecard_v1.json),
non teoriche. qwen3:4b e gemma3:4b NON compaiono come agenti operativi (il
primo squalificato per inaffidabilita', il secondo retrocesso - vedi
esclusioni documentate nel report finale, non in questo contratto)."""
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
CONTRACTS_DIR = os.path.join(ROOT, "contracts")

sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402
sys.path.insert(0, ORCH_DIR)
from nxs_schema_validator import validate_or_raise  # noqa: E402

import json  # noqa: E402

with open(os.path.join(CONTRACTS_DIR, "agent-capability-registry.schema.json"), encoding="utf-8") as f:
    SCHEMA = json.load(f)


def build():
    local_fast = {
        "agent_id": "LOCAL_FAST_MINISTRAL3B",
        "provider": "local-ollama", "model_or_runtime": "ministral-3:3b (Q4_K_M, Ollama 0.34.4)",
        "local_or_remote": "LOCAL",
        "capabilities": ["summaries", "log_parsing", "json_structured_output", "registry_updates",
                        "artifact_field_extraction", "italian", "english"],
        "coding_ability": "BASIC",
        "scientific_reasoning": "BASIC",
        "browser_access": False, "terminal_access": True, "file_access": "READ_WRITE",
        "github_access": False, "vault_access": "READ_ONLY", "mt5_access": "NONE",
        "max_concurrency": 1, "cost_class": "LOCAL_COMPUTE", "quota_state": "AVAILABLE",
        "availability": "ONLINE", "trust_level": "SANDBOXED",
        "allowed_task_types": ["DOCUMENTATION", "MONITORING", "MAINTENANCE"],
        "forbidden_task_types": ["DEPLOY", "MT5_RUN", "APPROVAL", "MARKET"],
    }
    local_strong = {
        "agent_id": "LOCAL_STRONG_MINISTRAL3B",
        "provider": "local-ollama", "model_or_runtime": "ministral-3:3b (Q4_K_M, Ollama 0.34.4)",
        "local_or_remote": "LOCAL",
        "capabilities": ["summaries", "log_parsing", "json_structured_output", "registry_updates",
                        "artifact_field_extraction", "italian", "english", "small_python_functions",
                        "unit_test_writing", "native_tool_calling"],
        "coding_ability": "MODERATE",
        "scientific_reasoning": "BASIC",
        "browser_access": False, "terminal_access": True, "file_access": "READ_WRITE",
        "github_access": False, "vault_access": "READ_ONLY", "mt5_access": "NONE",
        "max_concurrency": 1, "cost_class": "LOCAL_COMPUTE", "quota_state": "AVAILABLE",
        "availability": "ONLINE", "trust_level": "SANDBOXED",
        "allowed_task_types": ["CODE", "BACKFILL", "DOCUMENTATION", "MONITORING", "MAINTENANCE"],
        "forbidden_task_types": ["DEPLOY", "MT5_RUN", "APPROVAL", "MARKET",
                                "RESEARCH"],
    }
    return {"schema_version": 1, "agents": [local_fast, local_strong]}


def main():
    payload = build()
    validate_or_raise(payload, SCHEMA, label="AGENT_CAPABILITY_REGISTRY_V1")
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "agent_capability_registry_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} - validato contro lo schema, {len(payload['agents'])} agenti")


if __name__ == "__main__":
    main()
