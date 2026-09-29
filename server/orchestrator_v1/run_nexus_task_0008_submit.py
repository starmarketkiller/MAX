#!/usr/bin/env python3
"""NEXUS TASK #0008 - Multi-Agent Review & Finalization Pipeline V1 - submit.

Come #0005 (design di un framework nuovo, non backfill di dati esistenti):
il Router deve riconoscere che nessuna capacita' locale dimostrata copre
"progettare una pipeline di revisione multi-agente per l'Orchestrator" ed
escalare SENZA sprecare un tentativo locale. A differenza di #0005/#0006
(dominio funding_v1, isolato), questa task tocca potenzialmente il core
dell'Orchestrator stesso (ledger/router/capability registry) - risk_level
piu' alto, code_risk MEDIUM (nuovi moduli, nessuna modifica a file core
esistenti pianificata a priori)."""
import json
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))

sys.path.insert(0, ORCH_DIR)
from core.orchestrator import Orchestrator  # noqa: E402


def _manifest():
    return {
        "task_id": "TASK_NEXUS_0008_REVIEW_PIPELINE",
        "title": "Multi-Agent Review & Finalization Pipeline V1 - design",
        "objective": "Fare in modo che Jarvis non restituisca all'utente il primo output "
                    "grezzo di un worker, ma un work product finale verificato, revisionato "
                    "(quando richiesto) e consolidato: WORK_PRODUCT_V1 lifecycle, "
                    "producer/reviewer/verifier/finalizer separation, Review Matrix V1, "
                    "estensione dello Specialist Registry, Premium Budget Policy V1, "
                    "provider availability, escalation flow classificato, Review Context "
                    "Packet/Review Result contracts, revision loop con limite massimo, "
                    "Finalization Gate deterministico, Final Result Packet V1, "
                    "comportamento di consegna di Jarvis, readiness per ChatGPT/Claude/Codex "
                    "come specialist provider, learning telemetry, confidence derivata da "
                    "segnali esterni (mai auto-dichiarata).",
        "task_type": "RESEARCH",  # design architetturale, non backfill - stesso enum di #0005
        "priority": "HIGH", "risk_level": "A2",  # tocca potenzialmente Orchestrator core
                                                 # (ledger event types, capability registry),
                                                 # non solo un modulo foglia come funding_v1
        "scientific_risk": "MEDIUM",  # giudizio di design architetturale
        "code_risk": "MEDIUM",  # nuovi moduli + estensione di contratti/registry esistenti
        "financial_risk": "NONE",
        "required_capabilities": ["multi_agent_pipeline_design",
                                 "orchestrator_architecture_extension"],
        "deterministic_tools_available": False,
        "repo_scope": "server/review_pipeline_v1/, contracts/, server/orchestrator_v1/",
        "files_allowed": ["server/review_pipeline_v1/*", "contracts/work-product*.schema.json",
                         "contracts/review-*.schema.json", "contracts/final-result-packet*.schema.json",
                         "server/orchestrator_v1/agent_capability_registry_v1.json",
                         "server/orchestrator_v1/core/ledger.py",
                         "server/orchestrator_v1/verify_nexus_task_0008.py",
                         "server/tests/test_review_pipeline_v1.py"],
        "files_forbidden": ["MQL5/*", "Product-Platform/*", "server/research_scripts/phase7/*",
                           "server/funding_v1/*"],
        "dependencies": ["NEXUS_TASK_0001", "NEXUS_TASK_0002", "NEXUS_TASK_0003",
                        "NEXUS_TASK_0004"],  # riusa Task Queue/Router/Ledger/escalation gia'
                                            # validati, non li riprogetta
        "blockers": [],
        "expected_artifacts": ["contracts/work-product.schema.json",
                              "contracts/review-matrix.schema.json",
                              "contracts/review-context-packet.schema.json",
                              "contracts/review-result.schema.json",
                              "contracts/final-result-packet.schema.json",
                              "server/review_pipeline_v1/"],
        "success_criteria": [
            "Jarvis non consegna draft non verificati",
            "premium usato solo quando policy/router lo richiede",
            "Ministral puo' completare task semplici da solo",
            "escalation mirate producono context packet minimo",
            "reviewer puo' correggere senza rifare tutto",
            "review e approval restano separati",
            "provider exhausted gestito senza bypass silenzioso",
            "final output ha provenance completa",
            "Jarvis puo' spiegare chi ha fatto cosa",
            "telemetry pronta per il routing futuro",
            "verifier PASS", "regression PASS",
        ],
        "verifier": "server/orchestrator_v1/verify_nexus_task_0008.py",
        "estimated_complexity": "LARGE", "estimated_runtime": "N/A - design",
        "premium_allowed": True, "preferred_executor": "TIER3_CLAUDE",
        "fallback_executors": [], "approval_required": "REVIEW_REQUIRED",
        "created_by": "nexus_task_0008", "created_at": "2026-09-29T00:00:00Z",
        "tenant_id": "tenant-1", "account_scope_id": None,
    }


def main():
    orch = Orchestrator()
    task_id = "TASK_NEXUS_0008_REVIEW_PIPELINE"
    orch.submit(_manifest(), action=None, action_params={})
    rec = orch.process_task(task_id)
    print(f"Stato dopo routing: {rec['state']}")
    print(f"Escalation: {rec.get('escalation')}")
    return orch, rec


if __name__ == "__main__":
    orch, rec = main()
    out_path = os.path.join(ORCH_DIR, "nexus_task_0008_routing_result_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"task_id": "TASK_NEXUS_0008_REVIEW_PIPELINE", "state": rec["state"],
                 "escalation": rec.get("escalation"),
                 "ledger_events": orch.ledger.read_for_task("TASK_NEXUS_0008_REVIEW_PIPELINE")},
                f, indent=2, ensure_ascii=False)
    print(f"Scritto {out_path}")
