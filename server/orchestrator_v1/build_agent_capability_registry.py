#!/usr/bin/env python3
"""Local Model Bake-Off V1 - Fase 12: prima istanza REALE di
AGENT_CAPABILITY_REGISTRY_V1 (contracts/agent-capability-registry.schema.json),
popolata SOLO con capacita' dimostrate dal bake-off (bakeoff_scorecard_v1.json),
non teoriche. qwen3:4b e gemma3:4b NON compaiono come agenti operativi (il
primo squalificato per inaffidabilita', il secondo retrocesso - vedi
esclusioni documentate nel report finale, non in questo contratto).

Esteso in NEXUS TASK #0008 (Multi-Agent Review & Finalization Pipeline V1)
con specialist_role/integration_status (schema esteso in modo additivo) e
con 3 record di READINESS per Claude/Codex/ChatGPT come specialist provider
remoti - MAI simulati come raggiungibili automaticamente: ogni valore qui
riflette lo stato REALE osservato in questa sessione (nessun connector
automatico verso Claude esiste nel codice dell'Orchestrator - le
escalation vengono risolte per via conversazionale, non per chiamata API;
il server MCP Codex ha risposto CONNECTION_CLOSED in questa sessione;
ChatGPT non ha alcun connector configurato in questo repo)."""
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
        "specialist_role": "LOCAL_GENERALIST", "integration_status": "AVAILABLE",
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
        "specialist_role": "LOCAL_GENERALIST", "integration_status": "AVAILABLE",
    }
    # Record di READINESS (NEXUS TASK #0008 punti 14-15): nessuno di questi 3
    # provider e' oggi chiamabile in automatico dal codice dell'Orchestrator.
    # Servono per popolare REVIEW_MATRIX_V1/escalation con provider reali
    # anziche' nomi hardcoded nei prompt, e per generare correttamente
    # ESCALATION_READY_FOR_MANUAL_DELIVERY quando serve un loro intervento.
    claude_specialist = {
        "agent_id": "CLAUDE_TIER3", "provider": "anthropic", "model_or_runtime": "claude (sessione conversazionale)",
        "local_or_remote": "REMOTE", "capabilities": ["scientific_reasoning", "architecture_design",
                                                      "strategic_ambiguity_resolution", "code_review"],
        "coding_ability": "STRONG", "scientific_reasoning": "STRONG",
        "browser_access": False, "terminal_access": False, "file_access": "NONE",
        "github_access": False, "vault_access": "NONE", "mt5_access": "NONE",
        "max_concurrency": 1, "cost_class": "EXPENSIVE_PREMIUM", "quota_state": "UNKNOWN",
        "availability": "OFFLINE",  # nessun connector automatico - vedi docstring del modulo
        "trust_level": "FULLY_TRUSTED",
        "allowed_task_types": ["RESEARCH", "CODE", "DOCUMENTATION"],
        "forbidden_task_types": ["DEPLOY", "MT5_RUN", "MARKET"],
        "specialist_role": "SCIENTIFIC_RESEARCHER", "integration_status": "NOT_CONFIGURED",
    }
    codex_specialist = {
        "agent_id": "CODEX_TIER4", "provider": "openai-codex", "model_or_runtime": "codex (MCP server)",
        "local_or_remote": "REMOTE", "capabilities": ["complex_code_change", "multi_file_refactor"],
        "coding_ability": "STRONG", "scientific_reasoning": "MODERATE",
        "browser_access": False, "terminal_access": True, "file_access": "READ_WRITE",
        "github_access": True, "vault_access": "NONE", "mt5_access": "NONE",
        "max_concurrency": 1, "cost_class": "EXPENSIVE_PREMIUM", "quota_state": "UNKNOWN",
        "availability": "OFFLINE",  # server MCP configurato ma CONNECTION_CLOSED osservato
        "trust_level": "TRUSTED",
        "allowed_task_types": ["CODE", "DEPLOY"],
        "forbidden_task_types": ["MT5_RUN", "MARKET", "APPROVAL"],
        "specialist_role": "CODE_SPECIALIST", "integration_status": "CONFIGURED",
    }
    chatgpt_specialist = {
        "agent_id": "CHATGPT_SPECIALIST", "provider": "openai-chatgpt", "model_or_runtime": "chatgpt (non connesso)",
        "local_or_remote": "REMOTE", "capabilities": ["business_analysis", "second_opinion"],
        "coding_ability": "MODERATE", "scientific_reasoning": "MODERATE",
        "browser_access": False, "terminal_access": False, "file_access": "NONE",
        "github_access": False, "vault_access": "NONE", "mt5_access": "NONE",
        "max_concurrency": 1, "cost_class": "CHEAP_PREMIUM", "quota_state": "UNKNOWN",
        "availability": "OFFLINE",  # nessun connector presente in questo repo
        "trust_level": "TRUSTED",
        "allowed_task_types": ["RESEARCH", "DOCUMENTATION"],
        "forbidden_task_types": ["DEPLOY", "MT5_RUN", "MARKET", "APPROVAL", "CODE"],
        "specialist_role": "STRATEGIC_GENERALIST", "integration_status": "NOT_CONFIGURED",
    }
    return {"schema_version": 1, "agents": [local_fast, local_strong, claude_specialist,
                                           codex_specialist, chatgpt_specialist]}


def main():
    payload = build()
    validate_or_raise(payload, SCHEMA, label="AGENT_CAPABILITY_REGISTRY_V1")
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "agent_capability_registry_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} - validato contro lo schema, {len(payload['agents'])} agenti")


if __name__ == "__main__":
    main()
