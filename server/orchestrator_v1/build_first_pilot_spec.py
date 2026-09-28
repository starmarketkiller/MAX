#!/usr/bin/env python3
"""Orchestrator V1 punto 39 - specifica del primo pilota locale. NON
eseguito in questa fase (il runtime locale non e' ancora installato -
vedi install_plan_v1.json e la decisione finale in
build_final_decision_card.py: LOCAL_RUNTIME_NEEDS_SETUP)."""
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    task_manifest_example = {
        "task_id": "TASK_PILOT_BACKFILL_TEMPORAL_EXIT_EFFICIENCY",
        "title": "Backfill temporal_concentration + exit_efficiency per BREAKOUT_ACC e ORDER_BLOCK",
        "objective": "Colmare il gap esplicito trovato dalla Cross-Strategy Synthesis (Phase 7.26): "
                    "solo LIQ_SWEEP ha oggi queste due statistiche nel proprio Learning Packet.",
        "task_type": "BACKFILL", "priority": "NORMAL", "risk_level": "A1",
        "scientific_risk": "LOW", "code_risk": "MEDIUM", "financial_risk": "NONE",
        "required_capabilities": ["python", "pandas", "reading_existing_json_artifacts"],
        "deterministic_tools_available": True,
        "repo_scope": "server/research_scripts/phase7/phase7_28/ (nuova directory dedicata)",
        "files_allowed": ["server/research_scripts/phase7/phase7_28/**"],
        "files_forbidden": ["MQL5/**", "Product-Platform/**", "contracts/**",
                            "server/research_scripts/phase7/phase7_21/**",
                            "server/research_scripts/phase7/phase7_22/**"],
        "dependencies": ["phase7_21/baseline_economics_v1.json", "phase7_21/temporal_robustness_v1.json",
                        "phase7_22/orderblock_baseline_economics_v1.json",
                        "phase7_22/orderblock_temporal_robustness_v1.json"],
        "blockers": [], "expected_artifacts": ["breakout_acc_exit_efficiency_v1.json",
                                              "order_block_exit_efficiency_v1.json"],
        "success_criteria": ["Determinismo hash canonico", "Nessun riferimento orfano",
                            "Nessuna modifica a phase7_21/phase7_22 (diff zero)"],
        "verifier": "verify_phase_7_28.py", "estimated_complexity": "SMALL",
        "estimated_runtime": "10-30m (stima, dipende dalla velocita' reale del modello locale)",
        "premium_allowed": False, "preferred_executor": "TIER2_LOCAL_STRONG",
        "fallback_executors": ["TIER3_CLAUDE"], "approval_required": "AUTO",
        "created_by": "TIER3_CLAUDE_SPEC_PHASE", "created_at": "2026-09-28T00:00:00Z",
        "tenant_id": "tenant-1", "account_scope_id": None,
    }

    steps = {
        "deterministic_steps": [
            "1. Leggere baseline_economics_v1.json e temporal_robustness_v1.json di BREAKOUT_ACC/"
            "ORDER_BLOCK (gia' esistenti, nessun ricalcolo dei dati grezzi).",
            "2. Calcolare temporal_concentration (per-anno, stesso schema di LIQ_SWEEP Phase 7.25) "
            "con codice Python puro - NESSUN LLM necessario per questo calcolo specifico.",
        ],
        "local_model_steps": [
            "3. Il modello locale scrive/adatta il builder Python (build_exit_efficiency.py) "
            "seguendo ESPLICITAMENTE il pattern gia' esistente in phase7_25/"
            "build_liq_sweep_execution_realism.py come riferimento - non deve inventare uno "
            "schema nuovo.",
            "4. Il modello locale genera il testo descrittivo breve (campo 'exit_efficiency' del "
            "Learning Packet) a partire dai numeri calcolati - un task di sintesi testuale "
            "TIER 1/2 tipico.",
        ],
        "verifier": "verify_phase_7_28.py - rigenera gli artifact, confronta hash canonico, "
                   "verifica diff zero su phase7_21/phase7_22/MQL5/Product-Platform/contracts.",
        "pass_fail_rule": "PASS solo se il verificatore ritorna 0 errori E i test passano - "
                         "altrimenti FAIL, 1 retry delimitato, poi escalation.",
        "escalation_rule": "Se il retry fallisce ancora: classificare la causa (metodologica -> "
                          "Claude; codice complesso -> Codex; ambiente/tool -> rimedio "
                          "deterministico; sconosciuta -> revisione umana) - MAI un secondo retry "
                          "locale silenzioso (vedi ROUTING_POLICY_V1, punto 7 dell'architettura).",
        "expected_result_packet_confidence": "MEDIUM se verifier+test passano al primo tentativo "
            "locale, HIGH solo dopo una revisione umana o un secondo verificatore indipendente.",
    }

    payload = {
        "task_manifest_example": task_manifest_example, "execution_steps": steps,
        "not_executed_this_phase": True,
        "blocked_by": "LOCAL_RUNTIME_NEEDS_SETUP (Ollama + modello non ancora installati - vedi "
                     "install_plan_v1.json)",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "first_pilot_spec_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
