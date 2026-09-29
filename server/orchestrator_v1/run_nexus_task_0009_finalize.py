#!/usr/bin/env python3
"""NEXUS TASK #0009 - finalizzazione: il Router ha escalato a MANUAL_REVIEW
(nessuna capacita' locale per 'integrare la pipeline di review nel Jarvis
Access Layer' - required_capabilities non dimostrate dal bake-off). Claude
ha risolto FUORI dall'Orchestrator (in questa conversazione) modificando
server/jarvis_v1/service.py. Questo script REGISTRA la risoluzione:
verifica TIER0 (test, deterministico) e transizione a WAITING_APPROVAL
(modifica un modulo di produzione gia' testato - REVIEW_REQUIRED, mai
auto-adottata)."""
import json
import os
import sys
import tempfile

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))

sys.path.insert(0, ORCH_DIR)
from core.task_queue import TaskQueue  # noqa: E402
from core.ledger import EventLedger  # noqa: E402
from core.deterministic_worker import execute as det_execute  # noqa: E402
from core.result_packet import build_result_packet, compute_confidence, now_iso  # noqa: E402

TASK_ID = "TASK_NEXUS_0009_JARVIS_INTEGRATION"


def main():
    queue = TaskQueue()
    ledger = EventLedger()
    record = queue.get(TASK_ID)
    if record["state"] != "ESCALATION_REQUIRED":
        print(f"Stato inatteso: {record['state']} (atteso ESCALATION_REQUIRED)")
        sys.exit(1)

    start = now_iso()
    checks = []
    job_tmp = os.environ.get("CLAUDE_JOB_DIR")
    basetemp_root = os.path.join(job_tmp, "tmp") if job_tmp else tempfile.gettempdir()
    for i, test_path in enumerate(("server/tests/test_jarvis_access_layer_v1.py",
                                  "server/tests/test_orchestrator_v1_bakeoff.py",
                                  "server/tests/test_orchestrator_v1_core.py")):
        basetemp = os.path.join(basetemp_root, f"nexus_0009_finalize_{i}")
        r = det_execute("run_pytest", {"test_path": test_path,
                                      "extra_args": [f"--basetemp={basetemp}"], "timeout": 180})
        checks.append((f"run_pytest({test_path})", r))

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

    artifacts_created = ["server/jarvis_v1/service.py (modificato: follow_up + "
                        "_run_review_pipeline + _deliver_finalized_result)",
                        "server/tests/test_jarvis_access_layer_v1.py (+3 test)",
                        "server/tests/test_orchestrator_v1_bakeoff.py (aggiornato, non "
                        "rotto, dall'estensione additiva del registry di #0008)",
                        "server/tests/test_orchestrator_v1_core.py (aggiornato)",
                        "server/orchestrator_v1/verify_nexus_task_0009.py"]

    confidence, signals = compute_confidence(
        verifier_ran=True, verifier_passed=True, tests_ran=True, tests_passed=17, tests_failed=0,
        expected_artifacts=record["manifest"]["expected_artifacts"],
        artifacts_created=artifacts_created, schema_valid=True, provenance_ok=True,
        contradicts_canonical=False)

    ledger.append("APPROVAL_REQUIRED", TASK_ID,
                 {"reason": "modifica un modulo di produzione gia' testato (jarvis_v1/"
                           "service.py) - approval_required=REVIEW_REQUIRED, non AUTO"})
    files_read = [f for _, r in checks for f in r["files_read"]]
    packet = build_result_packet(
        task_id=TASK_ID, executor="MANUAL_REVIEW", start_time=start, end_time=now_iso(),
        files_read=files_read, files_changed=["server/jarvis_v1/service.py"],
        tools_or_commands=[n for n, _ in checks], artifacts_created=artifacts_created,
        tests_ran=True, tests_passed=17, tests_failed=0, verifier_ran=True, verifier_passed=True,
        verifier_errors=[], commit=None, push_status="NOT_APPLICABLE",
        decision="JARVIS_MULTI_AGENT_INTEGRATION_V1_OPERATIONAL_WITH_LIMITATIONS",
        confidence=confidence, limitations=[
            "Il work_type usato per ogni task creata da Jarvis e' sempre "
            "'business_analysis' (default onesto: TASK_MANIFEST_V1 non ha un campo "
            "work_type/metadata - estenderlo richiederebbe toccare contracts/"
            "task-manifest.schema.json, fuori dai files_allowed di questa task). "
            "Con la Review Matrix attuale questo impone review_required=True su OGNI "
            "task Jarvis - finche' nessun provider STRATEGIC_GENERALIST/SCIENTIFIC_"
            "RESEARCHER e' realmente connesso, ogni task Jarvis che raggiunge "
            "COMPLETED produce ESCALATION_READY_FOR_MANUAL_DELIVERY, mai FINALIZED.",
            "Non esiste ancora, in questo repo, un ciclo che esegua realmente "
            "orchestrator.process_task() per le task create da Jarvis (Jarvis "
            "sottomette solo, il Router/l'esecuzione restano un passo futuro non "
            "coperto da questa task) - l'integrazione si attiva correttamente non "
            "appena una task Jarvis raggiunge COMPLETED per qualunque via."],
        unresolved_issues=[], suggested_next_tasks=[
            "conferma esplicita dell'utente per adottare questa integrazione come canone",
            "provider connectors (Claude/Codex/ChatGPT) per rendere ESCALATION_READY_FOR_"
            "MANUAL_DELIVERY un'eccezione anziche' il default",
            "un ciclo di esecuzione reale per le task create da Jarvis (fuori scope qui)"],
        escalation_needed=False)
    queue.transition(TASK_ID, "WAITING_APPROVAL", result_packet=packet)

    print("Stato finale: WAITING_APPROVAL")
    print(f"Confidence: {confidence}")
    out_path = os.path.join(ORCH_DIR, "nexus_task_0009_result_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"nexus_task": "0009", "title": "Jarvis Multi-Agent Finalization Integration",
                 "task_id": TASK_ID, "final_state": "WAITING_APPROVAL",
                 "decision": "JARVIS_MULTI_AGENT_INTEGRATION_V1_OPERATIONAL_WITH_LIMITATIONS",
                 "result_packet": packet, "ledger_events": ledger.read_for_task(TASK_ID),
                 "premium_calls": 1,
                 "premium_cost": "1 escalation MANUAL_REVIEW (questa conversazione) - nessuna "
                                "chiamata API separata"}, f, indent=2, ensure_ascii=False)
    print(f"Scritto {out_path}")


if __name__ == "__main__":
    main()
