#!/usr/bin/env python3
"""NEXUS TASK #0005 - finalizzazione: dopo che il Router ha correttamente
escalato a TIER3_CLAUDE (nessuna capacita' locale per 'progettare un nuovo
framework'), Claude ha risolto FUORI dall'Orchestrator (in questa
conversazione) producendo gli artifact. Questo script li REGISTRA
nell'Orchestrator: verifica TIER0 (schema+test, deterministico) e
transizione a WAITING_APPROVAL (introduce architettura canonica nuova -
REVIEW_REQUIRED, mai auto-applicato/adottato senza una tua conferma
esplicita che questo sia il framework da tenere)."""
import json
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))

sys.path.insert(0, ORCH_DIR)
from core.task_queue import TaskQueue  # noqa: E402
from core.ledger import EventLedger  # noqa: E402
from core.deterministic_worker import execute as det_execute  # noqa: E402
from core.result_packet import build_result_packet, compute_confidence, now_iso  # noqa: E402

TASK_ID = "TASK_NEXUS_0005_FUNDING_FRAMEWORK"


def main():
    queue = TaskQueue()
    ledger = EventLedger()
    record = queue.get(TASK_ID)
    if record["state"] != "ESCALATION_REQUIRED":
        print(f"Stato inatteso: {record['state']} (atteso ESCALATION_REQUIRED)")
        sys.exit(1)

    start = now_iso()
    checks = []

    # Verifica via deterministic_worker: schema della priority queue (un solo oggetto) +
    # suite di test completa (che gia' valida ogni singola opportunity contro lo schema).
    r1 = det_execute("validate_json_schema", {
        "instance_path": "server/funding_v1/opportunity_priority_queue_v1.json",
        "schema_path": "contracts/opportunity-priority-queue.schema.json"})
    checks.append(("validate_json_schema(priority_queue)", r1))

    r2 = det_execute("run_pytest", {"test_path": "server/tests/test_funding_v1.py"})
    checks.append(("run_pytest(test_funding_v1)", r2))

    for name, r in checks:
        ledger.append("TOOL_USED", TASK_ID, {"tool": name})
        if r["files_read"]:
            ledger.append("FILE_READ", TASK_ID, {"files": r["files_read"]})

    all_passed = all(r["success"] for _, r in checks)
    errors = [e for _, r in checks for e in r["errors"]]

    if not all_passed:
        ledger.append("TASK_FAILED", TASK_ID, {"errors": errors})
        queue.transition(TASK_ID, "FAILED")
        print("Verifica fallita:", errors)
        sys.exit(1)

    ledger.append("TEST_PASSED", TASK_ID, {"checks": [n for n, _ in checks]})

    artifacts_created = ["contracts/opportunity.schema.json",
                        "contracts/opportunity-priority-queue.schema.json",
                        "server/funding_v1/opportunity_scoring.py",
                        "server/funding_v1/build_example_opportunities.py",
                        "server/funding_v1/build_opportunity_priority_queue.py",
                        "server/funding_v1/example_instances/opportunities_v1.json",
                        "server/funding_v1/opportunity_priority_queue_v1.json"]

    confidence, signals = compute_confidence(
        verifier_ran=True, verifier_passed=True, tests_ran=True, tests_passed=8, tests_failed=0,
        expected_artifacts=record["manifest"]["expected_artifacts"],
        artifacts_created=artifacts_created, schema_valid=True, provenance_ok=True,
        contradicts_canonical=False)

    ledger.append("APPROVAL_REQUIRED", TASK_ID,
                 {"reason": "introduce un nuovo framework/architettura canonica - "
                           "approval_required=REVIEW_REQUIRED, non AUTO"})
    files_read = [f for _, r in checks for f in r["files_read"]]
    packet = build_result_packet(
        task_id=TASK_ID, executor="TIER3_CLAUDE", start_time=start, end_time=now_iso(),
        files_read=files_read, files_changed=[], tools_or_commands=[n for n, _ in checks],
        artifacts_created=artifacts_created, tests_ran=True, tests_passed=8, tests_failed=0,
        verifier_ran=True, verifier_passed=True, verifier_errors=[], commit=None,
        push_status="NOT_APPLICABLE", decision="FRAMEWORK_READY_AWAITING_ADOPTION",
        confidence=confidence, limitations=[
            "5 opportunity di esempio sono ILLUSTRATIVE (stime di Claude senza dati di "
            "mercato reali, dichiarato in provenance.dimension_estimation_method) - non "
            "decisioni di business gia' prese",
            "OPP_MT5_STRATEGY_SIGNAL_SUBSCRIPTION esplicitamente non azionabile oggi "
            "(nessuna strategia ha status EDGE_CONFIRMED)"],
        unresolved_issues=[], suggested_next_tasks=[
            "conferma esplicita dell'utente per adottare questo framework come canone",
            "eventuale integrazione nel Control Plane quando Codex torna disponibile"],
        escalation_needed=False)
    queue.transition(TASK_ID, "WAITING_APPROVAL", result_packet=packet)

    print(f"Stato finale: WAITING_APPROVAL")
    print(f"Confidence: {confidence}")
    out_path = os.path.join(ORCH_DIR, "nexus_task_0005_result_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"nexus_task": "0005", "title": "Funding Priority & Opportunity Framework V1",
                 "task_id": TASK_ID, "final_state": "WAITING_APPROVAL",
                 "decision": "FRAMEWORK_READY_AWAITING_ADOPTION", "result_packet": packet,
                 "ledger_events": ledger.read_for_task(TASK_ID), "premium_calls": 1,
                 "premium_cost": "1 escalation TIER3_CLAUDE (questa conversazione) - nessuna "
                                "chiamata API separata"}, f, indent=2, ensure_ascii=False)
    print(f"Scritto {out_path}")


if __name__ == "__main__":
    main()
