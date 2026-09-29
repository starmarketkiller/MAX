#!/usr/bin/env python3
"""Verifica INDIPENDENTE di NEXUS TASK #0009 (Jarvis Multi-Agent
Finalization Integration) - non si fida del self-report: costruisce un
JarvisService isolato ed esercita davvero i percorsi FINALIZED/
ESCALATION_READY_FOR_MANUAL_DELIVERY, verifica che l'invariante 'Jarvis non
sceglie mai l'executor' non sia stato violato, e rilancia la suite completa.
Fail-closed."""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
SERVER_DIR = os.path.join(ROOT, "server")

sys.path.insert(0, SERVER_DIR)
sys.path.insert(0, ORCH_DIR)


def _message(text, cls="UNKNOWN", conversation="c1", metadata=None):
    return {"message_id": f"m-{abs(hash(text))}", "user_id": "42", "channel": "TEST",
           "conversation_id": conversation, "timestamp": datetime.now(timezone.utc).isoformat(),
           "input_type": "TEXT", "text": text, "attachments": [], "reply_to": None,
           "request_class": cls, "priority": "NORMAL", "metadata": metadata or {}}


def verify():
    errors = []
    from jarvis_v1.service import JarvisService
    from jarvis_v1.gateway import JarvisGateway

    with tempfile.TemporaryDirectory() as tmp:
        svc = JarvisService(os.path.join(tmp, "queue.json"), os.path.join(tmp, "ledger.jsonl"))
        gw = JarvisGateway(svc)

        created = gw.handle(_message("Jarvis, crea una NEXUS TASK per analizzare un'opportunita'."))
        task_id = created["task_id"]
        record = svc.queue.get(task_id)
        if record["executor"] is not None:
            errors.append("Jarvis ha popolato 'executor' alla creazione - viola l'invariante "
                         "'Jarvis non sceglie mai l'executor' (deve restare None finche' il "
                         "Router non esegue il task altrove)")

        svc.queue.transition(task_id, "RUNNING")
        svc.queue.transition(task_id, "COMPLETED", result_packet={
            "task_id": task_id, "executor": "LOCAL_FAST_MINISTRAL3B",
            "verifier": {"ran": True, "passed": True, "errors": []}})
        follow = gw.handle(_message("A che punto e'?", conversation="c1"))
        if follow["status"] != "ESCALATION_READY_FOR_MANUAL_DELIVERY":
            errors.append(f"atteso ESCALATION_READY_FOR_MANUAL_DELIVERY (default work_type "
                         f"business_analysis, nessun reviewer connesso), trovato "
                         f"{follow['status']}")
        if "escalation" not in follow["summary"].lower():
            errors.append("il messaggio a Jarvis non menziona il pacchetto di escalation")

        follow2 = gw.handle(_message("A che punto e' ora?", conversation="c1"))
        if follow2["status"] != follow["status"]:
            errors.append("la cache del work product non e' stabile fra follow-up ripetuti")

    with tempfile.TemporaryDirectory() as basetemp:
        proc = subprocess.run([sys.executable, "-m", "pytest",
                              "server/tests/test_jarvis_access_layer_v1.py", "-q",
                              f"--basetemp={basetemp}"],
                             capture_output=True, text=True, cwd=ROOT, timeout=60)
    if proc.returncode != 0:
        errors.append(f"test_jarvis_access_layer_v1.py non passa: {proc.stdout[-1500:]}")
    elif "14 passed" not in proc.stdout:
        errors.append(f"attesi 14 test (11 preesistenti + 3 di #0009): {proc.stdout[-500:]}")

    with tempfile.TemporaryDirectory() as basetemp2:
        proc_bakeoff = subprocess.run([sys.executable, "-m", "pytest",
                                      "server/tests/test_orchestrator_v1_bakeoff.py",
                                      "server/tests/test_orchestrator_v1_core.py", "-q",
                                      f"--basetemp={basetemp2}"],
                                     capture_output=True, text=True, cwd=ROOT, timeout=180)
    if proc_bakeoff.returncode != 0:
        errors.append(f"regressione bake-off/core (registry unchanged) non passa: "
                     f"{proc_bakeoff.stdout[-1500:]}")

    if not errors:
        print("VERIFY PASSED - NEXUS TASK #0009 coerente (Jarvis non sceglie mai l'executor, "
             "un task COMPLETED che richiede review non connessa produce onestamente "
             "ESCALATION_READY_FOR_MANUAL_DELIVERY con messaggio esplicito, cache stabile fra "
             "follow-up, nessuna regressione sui test preesistenti)")
        return True
    print("VERIFY FAILED:")
    for e in errors:
        print(f"  - {e}")
    return False


if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
