#!/usr/bin/env python3
"""NEXUS TASK #0003 - Approve Safety Net Backfill.

Applica al file canonico SOLO i 6 campi gia' completati e verificati da
NEXUS TASK #0002 (esclude ORDER_BLOCK.exit_efficiency, che resta
nello stato precedente - escalation genuina ancora in corso).

IMPORTANTE (scoperto durante l'implementazione): questo repository ha un
test di determinismo (test_phase_7_26.py::test_all_artifacts_deterministic)
che verifica che OGNI artifact canonico sia esattamente riproducibile
rieseguendo il proprio script builder. Applicare i valori con un patch
manuale al JSON avrebbe rotto quell'invariante per sempre. La correzione
corretta e' stata fatta sul builder stesso
(build_cross_strategy_learning_packet.py, gia' modificato in questa fase
con le STESSE formule deterministiche gia' indipendentemente verificate in
NEXUS TASK #0001/#0002 - mai una chiamata LLM in un builder canonico) -
questo task rigenera l'artifact RIESEGUENDO il builder (mai scrivendo il
JSON a mano), poi verifica che il risultato sia esattamente quello atteso.

Ruolo di Claude: ha scritto il fix del builder (harness/codice deterministico,
stessa categoria di lavoro gia' fatta in tutte le fasi precedenti - MAI
lavoro scientifico/di contenuto, le formule sono le stesse gia' verificate
dal worker locale in NEXUS TASK #0001/#0002). L'Orchestrator esegue
rebuild/verify/test/commit - approval_required=AUTO qui perche' l'utente
ha gia' dato approvazione ESPLICITA a questa esatta applicazione nel suo
messaggio (non un bypass - l'approvazione e' avvenuta fuori dal codice,
nel canale umano, esattamente come previsto dal modello di approval)."""
import json
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))

sys.path.insert(0, ORCH_DIR)
from core.orchestrator import Orchestrator  # noqa: E402

EXPECTED_CHANGED_FIELDS = [["BREAKOUT_ACC", "temporal_concentration"],
                          ["BREAKOUT_ACC", "exit_efficiency"],
                          ["BREAKOUT_ACC", "execution_degradation"],
                          ["BREAKOUT_ACC", "favorable_before_loss"],
                          ["BREAKOUT_ACC", "adverse_before_win"],
                          ["ORDER_BLOCK", "temporal_concentration"]]
SENSITIVE_FIELDS = ["failure_modes", "candidate_hypotheses", "confidence", "fidelity",
                   "strategy_identity", "mechanism"]


def _manifest():
    return {
        "task_id": "TASK_NEXUS_0003_APPROVE_BACKFILL",
        "title": "Approve Safety Net Backfill (6 campi verificati)",
        "objective": "Applicare al file canonico i 6 campi DERIVABLE_NOW completati e "
                    "verificati da NEXUS TASK #0002 - MAI ORDER_BLOCK.exit_efficiency "
                    "(escalation genuina in corso).",
        "task_type": "BACKFILL", "priority": "NORMAL", "risk_level": "A1",
        "scientific_risk": "NONE", "code_risk": "LOW", "financial_risk": "NONE",
        "required_capabilities": ["registry_updates"], "deterministic_tools_available": True,
        "repo_scope": "server/research_scripts/phase7/phase7_26/",
        "files_allowed": ["server/research_scripts/phase7/phase7_26/*"],
        "files_forbidden": ["MQL5/*", "Product-Platform/*", "contracts/*",
                           "server/research_scripts/phase7/phase7_21/*",
                           "server/research_scripts/phase7/phase7_22/*"],
        "dependencies": [], "blockers": [],
        "expected_artifacts": ["server/research_scripts/phase7/phase7_26/"
                              "cross_strategy_learning_packets_v1.json"],
        "success_criteria": ["esattamente i 6 campi attesi cambiati",
                           "ORDER_BLOCK.exit_efficiency invariato",
                           "nessun campo sensibile toccato",
                           "test_phase_7_26.py determinismo passa"],
        "verifier": "server/orchestrator_v1/verify_nexus_task_0003.py",
        "estimated_complexity": "SMALL", "estimated_runtime": "1m", "premium_allowed": False,
        "preferred_executor": "TIER0_DETERMINISTIC", "fallback_executors": [],
        "approval_required": "AUTO", "created_by": "nexus_task_0003_human_approved_in_chat",
        "created_at": "2026-09-29T00:00:00Z", "tenant_id": "tenant-1", "account_scope_id": None,
    }


def main():
    orch = Orchestrator()
    task_id = "TASK_NEXUS_0003_APPROVE_BACKFILL"
    orch.submit(_manifest(), action="apply_approved_backfill", action_params={
        "builder_script": "server/research_scripts/phase7/phase7_26/"
                         "build_cross_strategy_learning_packet.py",
        "learning_packet_path": "server/research_scripts/phase7/phase7_26/"
                               "cross_strategy_learning_packets_v1.json",
        "expected_changed_fields": EXPECTED_CHANGED_FIELDS,
        "never_change_field": ["ORDER_BLOCK", "exit_efficiency"],
        "sensitive_fields": SENSITIVE_FIELDS,
        "test_command": [sys.executable, "-m", "pytest", "phase7_26/test_phase_7_26.py", "-q"],
        "test_cwd": "server/research_scripts/phase7",
        # cross_strategy_synthesis_v1.json LEGGE il Learning Packet (temporal_concentration/
        # exit_efficiency) - scoperto durante l'implementazione che va rigenerato IN CASCATA,
        # altrimenti la SUA verifica di determinismo si rompe (le osservazioni sono gia'
        # parametriche/calcolate a runtime, nessuna correzione manuale del builder di sintesi
        # e' stata necessaria - solo rieseguirlo).
        "downstream_builder_scripts": ["server/research_scripts/phase7/phase7_26/"
                                      "build_cross_strategy_synthesis.py"],
        "downstream_artifact_paths": ["server/research_scripts/phase7/phase7_26/"
                                     "cross_strategy_synthesis_v1.json"],
    })
    rec = orch.process_task(task_id)
    print(f"Stato: {rec['state']}")
    rp = rec.get("result_packet")
    if rp:
        print(f"Decisione RESULT_PACKET: {rp['decision']}, confidence={rp['confidence']}")

    decision = "BACKFILL_APPROVED_AND_APPLIED" if rec["state"] == "COMPLETED" \
        else "BACKFILL_APPLICATION_BLOCKED"

    output = {"nexus_task": "0003", "title": "Approve Safety Net Backfill",
            "task_id": task_id, "final_state": rec["state"], "decision": decision,
            "result_packet": rp, "ledger_events": orch.ledger.read_for_task(task_id),
            "premium_calls": 0, "premium_cost": 0}

    out_path = os.path.join(ORCH_DIR, "nexus_task_0003_result_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nDECISIONE: {decision}")
    print(f"Scritto {out_path}")
    return rec, output


if __name__ == "__main__":
    main()
