#!/usr/bin/env python3
"""NEXUS TASK #0009 - Jarvis Multi-Agent Finalization Integration - submit.

A differenza di #0008 (design di un framework nuovo), qui la pipeline
esiste gia' (server/review_pipeline_v1/) - il compito e' collegarla al
Jarvis Access Layer V1 gia' esistente (server/jarvis_v1/service.py) senza
romperne il comportamento gia' testato (11 test in
test_jarvis_access_layer_v1.py). task_type=CODE (non RESEARCH): non serve
nuovo giudizio di design, solo integrazione."""
import json
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))

sys.path.insert(0, ORCH_DIR)
from core.orchestrator import Orchestrator  # noqa: E402


def _manifest():
    return {
        "task_id": "TASK_NEXUS_0009_JARVIS_INTEGRATION",
        "title": "Jarvis Multi-Agent Finalization Integration",
        "objective": "Collegare la Multi-Agent Review & Finalization Pipeline V1 (#0008, gia' "
                    "costruita) al Jarvis Access Layer V1 (#0007, gia' costruito): ogni task "
                    "creata da Jarvis deve passare per WORK_PRODUCT_V1/review_engine prima di "
                    "essere consegnata. Jarvis non deve mai consegnare DRAFT/UNDER_REVIEW/"
                    "REVISION_REQUIRED o un'escalation aperta come risultato finale. Quando "
                    "una review premium serve ma il provider non e' connesso, Jarvis deve "
                    "restituire un messaggio esplicito di tipo "
                    "ESCALATION_READY_FOR_MANUAL_DELIVERY, non un output silenziosamente "
                    "incompleto.",
        "task_type": "CODE",  # integrazione, non nuovo design - la pipeline esiste gia'
        "priority": "HIGH", "risk_level": "A1",
        "scientific_risk": "LOW",  # nessun nuovo giudizio scientifico/di design richiesto
        "code_risk": "MEDIUM",  # tocca un modulo esistente gia' testato (jarvis_v1/service.py)
        "financial_risk": "NONE",
        "required_capabilities": ["jarvis_service_integration", "state_machine_integration"],
        "deterministic_tools_available": False,
        "repo_scope": "server/jarvis_v1/, server/review_pipeline_v1/",
        "files_allowed": ["server/jarvis_v1/*", "server/review_pipeline_v1/*",
                         "server/tests/test_jarvis_access_layer_v1.py",
                         "server/orchestrator_v1/verify_nexus_task_0009.py"],
        "files_forbidden": ["MQL5/*", "Product-Platform/*", "server/research_scripts/phase7/*",
                           "server/funding_v1/*", "render.yaml"],
        "dependencies": ["NEXUS_TASK_0007", "NEXUS_TASK_0008"], "blockers": [],
        "expected_artifacts": ["server/jarvis_v1/service.py (modificato)"],
        "success_criteria": [
            "Jarvis non consegna mai DRAFT/UNDER_REVIEW/REVISION_REQUIRED come risultato finale",
            "quando serve una review premium non connessa, risposta esplicita "
            "ESCALATION_READY_FOR_MANUAL_DELIVERY, mai un bypass silenzioso",
            "gli 11 test esistenti di test_jarvis_access_layer_v1.py continuano a passare "
            "(nessuna regressione sul comportamento gia' validato)",
            "verifier PASS", "regression PASS",
        ],
        "verifier": "server/orchestrator_v1/verify_nexus_task_0009.py",
        "estimated_complexity": "MEDIUM", "estimated_runtime": "N/A - integrazione",
        "premium_allowed": True, "preferred_executor": "TIER2_LOCAL_STRONG",
        "fallback_executors": ["TIER3_CLAUDE"], "approval_required": "REVIEW_REQUIRED",
        "created_by": "nexus_task_0009", "created_at": "2026-09-29T00:00:00Z",
        "tenant_id": "tenant-1", "account_scope_id": None,
    }


def main():
    orch = Orchestrator()
    task_id = "TASK_NEXUS_0009_JARVIS_INTEGRATION"
    orch.submit(_manifest(), action=None, action_params={})
    rec = orch.process_task(task_id)
    print(f"Stato dopo routing: {rec['state']}")
    print(f"Escalation: {rec.get('escalation')}")
    return orch, rec


if __name__ == "__main__":
    orch, rec = main()
    out_path = os.path.join(ORCH_DIR, "nexus_task_0009_routing_result_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"task_id": "TASK_NEXUS_0009_JARVIS_INTEGRATION", "state": rec["state"],
                 "escalation": rec.get("escalation"),
                 "ledger_events": orch.ledger.read_for_task("TASK_NEXUS_0009_JARVIS_INTEGRATION")},
                f, indent=2, ensure_ascii=False)
    print(f"Scritto {out_path}")
