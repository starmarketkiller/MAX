#!/usr/bin/env python3
"""NEXUS TASK #0005 - Funding Priority & Opportunity Framework V1.

Diverso per natura da #0001/#0002 (backfill di dati GIA' esistenti): qui
non c'e' nulla da "scoprire" per il worker locale - e' un compito di
DESIGN di un nuovo framework (schemi, modello di scoring, separazione
TECHNICAL_PRIORITY/FUNDING_PRIORITY). Il Router deve riconoscere
IMMEDIATAMENTE che nessuna capacita' locale dimostrata copre "definire un
nuovo framework di prioritizzazione business" ed escalare SENZA sprecare
un tentativo locale - comportamento diverso ma altrettanto corretto di
quello dimostrato in #0002 (dove invece 6/7 sotto-task erano genuinamente
derivabili localmente).

Consegna di Claude (TIER3, risolto in questa conversazione, non tramite
API premium separata): contracts/opportunity.schema.json,
contracts/opportunity-priority-queue.schema.json,
server/funding_v1/opportunity_scoring.py (motore deterministico, pesi
espliciti), server/funding_v1/build_example_opportunities.py (5 esempi
radicati nel contesto reale, NON decisioni di business gia' prese),
server/funding_v1/build_opportunity_priority_queue.py."""
import json
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))

sys.path.insert(0, ORCH_DIR)
from core.orchestrator import Orchestrator  # noqa: E402


def _manifest():
    return {
        "task_id": "TASK_NEXUS_0005_FUNDING_FRAMEWORK",
        "title": "Funding Priority & Opportunity Framework V1 - design",
        "objective": "Definire un sistema che assegna priorita' alle opportunity in base a "
                    "11 dimensioni dichiarate (time-to-cash, capitale, difficolta' vendita, "
                    "margine, ricorrenza, automazione, competenze, dipendenza da tool "
                    "premium, riuso strategico, rischio, tempo umano) - separando "
                    "esplicitamente TECHNICAL_PRIORITY da FUNDING_PRIORITY.",
        "task_type": "RESEARCH",  # design di un nuovo framework, non un backfill di dati
                                 # esistenti - riusa 'RESEARCH' (valore gia' esistente
                                 # nell'enum), nessun nuovo task_type inventato
        "priority": "HIGH", "risk_level": "A1",
        "scientific_risk": "MEDIUM",  # richiede giudizio di design/strategia - nessun
                                     # agente locale puo' farlo per costruzione (§6)
        "code_risk": "LOW", "financial_risk": "NONE",
        "required_capabilities": ["business_framework_design", "priority_scoring_model_design"],
        "deterministic_tools_available": False,
        "repo_scope": "server/funding_v1/, contracts/",
        "files_allowed": ["server/funding_v1/*", "contracts/opportunity*.schema.json"],
        "files_forbidden": ["MQL5/*", "Product-Platform/*", "server/research_scripts/phase7/*",
                           "server/orchestrator_v1/core/*"],
        "dependencies": [], "blockers": [],
        "expected_artifacts": ["contracts/opportunity.schema.json",
                              "contracts/opportunity-priority-queue.schema.json",
                              "server/funding_v1/opportunity_scoring.py",
                              "server/funding_v1/opportunity_priority_queue_v1.json"],
        "success_criteria": ["schemi validano contro nxs_schema_validator.py",
                           "TECHNICAL_PRIORITY e FUNDING_PRIORITY restano assi separati",
                           "almeno 5 opportunity di esempio con punteggi coerenti",
                           "pesi di scoring espliciti e documentati (somma 1.0)"],
        "verifier": "server/orchestrator_v1/verify_nexus_task_0005.py",
        "estimated_complexity": "MEDIUM", "estimated_runtime": "N/A - design",
        "premium_allowed": True, "preferred_executor": "TIER3_CLAUDE",
        "fallback_executors": [], "approval_required": "REVIEW_REQUIRED",
        "created_by": "nexus_task_0005", "created_at": "2026-09-29T00:00:00Z",
        "tenant_id": "tenant-1", "account_scope_id": None,
    }


def main():
    orch = Orchestrator()
    task_id = "TASK_NEXUS_0005_FUNDING_FRAMEWORK"
    orch.submit(_manifest(), action=None, action_params={})  # nessuna azione TIER0/locale -
                                                             # il Router deve escalare
    rec = orch.process_task(task_id)
    print(f"Stato dopo routing: {rec['state']}")
    print(f"Escalation: {rec.get('escalation')}")
    return orch, rec


if __name__ == "__main__":
    orch, rec = main()
    out_path = os.path.join(ORCH_DIR, "nexus_task_0005_routing_result_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"task_id": "TASK_NEXUS_0005_FUNDING_FRAMEWORK", "state": rec["state"],
                 "escalation": rec.get("escalation"),
                 "ledger_events": orch.ledger.read_for_task("TASK_NEXUS_0005_FUNDING_FRAMEWORK")},
                f, indent=2, ensure_ascii=False)
    print(f"Scritto {out_path}")
