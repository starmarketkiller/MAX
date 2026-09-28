#!/usr/bin/env python3
"""NEXUS TASK #0004 - Merge Escalation Resolution (ORDER_BLOCK.exit_efficiency).

Chiude il ciclo aperto da NEXUS TASK #0002: l'unico campo escalato a
TIER3_CLAUDE (il worker locale non riusciva a produrre una narrativa
affidabile, non un problema di dato) e' stato risolto da Claude usando
ESCLUSIVAMENTE il CONTEXT_PACKET_V1 gia' generato da NEXUS + gli artifact
canonici indicati (canonical_economic_dataset_v1.json, Phase 7.22) -
nessun riesame della strategia, nessuna nuova hypothesis, nessun verdict
cambiato.

Risoluzione di Claude: FIELD_VALUE (non KEEP_NOT_AVAILABLE) - 0.31 (13
eventi, 0 esclusi), ricalcolato indipendentemente e confermato identico al
valore gia' presente in NEXUS TASK #0001. Trovata e corretta una
robustezza latente nella formula (campo 'direction' e' un intero 1/-1, non
la stringa 'BUY'/'SELL' - verificato algebricamente e numericamente che il
valore non cambia, ne' per ORDER_BLOCK ne' per il BREAKOUT_ACC gia'
applicato in TASK #0003).

Applicato attraverso la STESSA infrastruttura di TASK #0003
(apply_approved_backfill) - mai un patch manuale al JSON."""
import json
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))

sys.path.insert(0, ORCH_DIR)
from core.orchestrator import Orchestrator  # noqa: E402

EXPECTED_CHANGED_FIELDS = [["ORDER_BLOCK", "exit_efficiency"]]
SENSITIVE_FIELDS = ["failure_modes", "candidate_hypotheses", "confidence", "fidelity",
                   "strategy_identity", "mechanism"]


def _manifest():
    return {
        "task_id": "TASK_NEXUS_0004_MERGE_ESCALATION", "title": "Merge escalation resolution "
                  "ORDER_BLOCK.exit_efficiency",
        "objective": "Applicare al file canonico la risoluzione Claude (TIER3) dell'unica "
                    "escalation genuina di NEXUS TASK #0002 - FIELD_VALUE per "
                    "ORDER_BLOCK.exit_efficiency, verificato indipendentemente contro il "
                    "dataset canonico Phase 7.22.",
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
        "success_criteria": ["esattamente ORDER_BLOCK.exit_efficiency cambiato",
                           "nessun campo sensibile toccato",
                           "test_phase_7_26.py completo passa"],
        "verifier": "server/orchestrator_v1/verify_nexus_task_0004.py",
        "estimated_complexity": "TRIVIAL", "estimated_runtime": "1m", "premium_allowed": True,
        "preferred_executor": "TIER0_DETERMINISTIC", "fallback_executors": [],
        # TIER3_CLAUDE ha gia' risolto il CONTENUTO (fuori da questo task, nella
        # conversazione) - questo task applica meccanicamente quella risoluzione gia'
        # approvata, stessa logica di TASK #0003.
        "approval_required": "AUTO", "created_by": "nexus_task_0004_claude_escalation_resolved",
        "created_at": "2026-09-29T00:00:00Z", "tenant_id": "tenant-1", "account_scope_id": None,
    }


def main():
    orch = Orchestrator()
    task_id = "TASK_NEXUS_0004_MERGE_ESCALATION"
    orch.submit(_manifest(), action="apply_approved_backfill", action_params={
        "builder_script": "server/research_scripts/phase7/phase7_26/"
                         "build_cross_strategy_learning_packet.py",
        "learning_packet_path": "server/research_scripts/phase7/phase7_26/"
                               "cross_strategy_learning_packets_v1.json",
        "expected_changed_fields": EXPECTED_CHANGED_FIELDS,
        "never_change_field": ["BREAKOUT_ACC", "temporal_concentration"],  # sentinella:
                                                                          # NON deve cambiare
                                                                          # rispetto a TASK #0003
        "sensitive_fields": SENSITIVE_FIELDS,
        "test_command": [sys.executable, "-m", "pytest", "phase7_26/test_phase_7_26.py", "-q"],
        "test_cwd": "server/research_scripts/phase7",
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

    decision = "ESCALATION_MERGED" if rec["state"] == "COMPLETED" else "ESCALATION_MERGE_BLOCKED"

    output = {"nexus_task": "0004", "title": "Merge Escalation Resolution", "task_id": task_id,
            "final_state": rec["state"], "decision": decision, "result_packet": rp,
            "ledger_events": orch.ledger.read_for_task(task_id),
            "claude_resolution": {
                "field": "ORDER_BLOCK.exit_efficiency", "verdict": "FIELD_VALUE",
                "value": "Rapporto medio di efficienza di uscita: 0.31 (su 13 eventi, 0 "
                       "esclusi per assenza di target).",
                "source_artifact": "server/research_scripts/phase7/phase7_22/"
                                  "canonical_economic_dataset_v1.json",
                "derivation": "captured/available per evento (stessa formula gia' verificata "
                             "per BREAKOUT_ACC), media su 13 eventi - ricalcolato "
                             "indipendentemente da Claude, identico a NEXUS TASK #0001",
                "confidence": "ALTA per il calcolo - BASSA resta il caveat generale di "
                             "campione (n=13) gia' presente altrove nel packet",
                "limitations": ["n=13, campione minimo", "1 evento anomalo (ratio=0.125) "
                               "riportato senza interpretarne la causa",
                               "campo 'direction' scoperto codificato come intero 1/-1 non "
                               "stringa - corretto per robustezza, valore invariato"]},
            "premium_calls": 1, "premium_cost": "1 escalation TIER3_CLAUDE (questa "
                                               "conversazione) - nessuna chiamata API separata"}

    out_path = os.path.join(ORCH_DIR, "nexus_task_0004_result_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nDECISIONE: {decision}")
    print(f"Scritto {out_path}")
    return rec, output


if __name__ == "__main__":
    main()
