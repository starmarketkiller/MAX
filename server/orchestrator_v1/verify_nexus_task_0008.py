#!/usr/bin/env python3
"""Verifica INDIPENDENTE di NEXUS TASK #0008 (Multi-Agent Review &
Finalization Pipeline V1) - non si fida del self-report: ricontrolla ogni
schema, riesegue davvero i 5 acceptance test A-E contro il motore reale (non
si limita a leggere il risultato salvato), e verifica che nessun provider
premium sia dichiarato disponibile senza esserlo davvero. Fail-closed."""
import json
import os
import subprocess
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
REVIEW_DIR = os.path.join(ROOT, "server", "review_pipeline_v1")
CONTRACTS_DIR = os.path.join(ROOT, "contracts")

sys.path.insert(0, ORCH_DIR)
sys.path.insert(0, REVIEW_DIR)


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def verify():
    errors = []
    from nxs_schema_validator import validate
    from core.task_queue import TaskQueue

    queue = TaskQueue()
    try:
        record = queue.get("TASK_NEXUS_0008_REVIEW_PIPELINE")
    except KeyError:
        record = None
    if record is None:
        errors.append("TASK_NEXUS_0008_REVIEW_PIPELINE non trovato nella Task Queue")
    elif record["state"] != "WAITING_APPROVAL":
        errors.append(f"stato atteso WAITING_APPROVAL, trovato {record['state']}")
    elif record.get("result_packet", {}).get("decision") != \
            "MULTI_AGENT_FINALIZATION_PIPELINE_V1_OPERATIONAL_WITH_LIMITATIONS":
        errors.append(f"decision inattesa: {record.get('result_packet', {}).get('decision')}")

    for schema_name, instance_rel in [
        ("work-product-lifecycle.schema.json", "example_instances/work_product_lifecycle_v1.json"),
        ("review-matrix.schema.json", "example_instances/review_matrix_v1.json"),
        ("premium-budget-policy.schema.json", "example_instances/premium_budget_policy_v1.json"),
    ]:
        schema = _load(os.path.join(CONTRACTS_DIR, schema_name))
        payload = _load(os.path.join(REVIEW_DIR, instance_rel))["payload"]
        schema_errors = validate(payload, schema)
        if schema_errors:
            errors.append(f"{instance_rel}: {schema_errors}")

    registry_schema = _load(os.path.join(CONTRACTS_DIR, "agent-capability-registry.schema.json"))
    registry_doc = _load(os.path.join(ORCH_DIR, "agent_capability_registry_v1.json"))
    registry_errors = validate(registry_doc["payload"], registry_schema)
    if registry_errors:
        errors.append(f"agent_capability_registry_v1.json: {registry_errors}")

    # Nessun provider premium deve risultare "usabile ora" senza un
    # integration_status realmente configurato - altrimenti la pipeline
    # potrebbe fingere una chiamata automatica che non esiste.
    for agent in registry_doc["payload"]["agents"]:
        if agent.get("local_or_remote") == "REMOTE" and agent.get("cost_class") != "FREE":
            if agent.get("availability") == "ONLINE" and agent.get("integration_status") \
                    in ("NOT_CONFIGURED", "UNAVAILABLE"):
                errors.append(f"{agent['agent_id']}: availability=ONLINE ma integration_status="
                             f"{agent['integration_status']} - incoerente, rischio di falso "
                             "positivo di disponibilita'")

    # Riesecuzione REALE dei 5 acceptance test (non il solo self-report salvato).
    proc = subprocess.run([sys.executable, "-m", "pytest", "server/tests/test_review_pipeline_v1.py",
                          "-q", "-k", "test_A_ or test_B_ or test_C_ or test_D_ or test_E_"],
                         capture_output=True, text=True, cwd=ROOT, timeout=60)
    if proc.returncode != 0:
        errors.append(f"acceptance test A-E non passano: {proc.stdout[-1500:]}")
    elif "5 passed" not in proc.stdout and "6 passed" not in proc.stdout:
        errors.append(f"attesi almeno 5 acceptance test eseguiti, output: {proc.stdout[-500:]}")

    proc_full = subprocess.run([sys.executable, "-m", "pytest", "server/tests/test_review_pipeline_v1.py",
                               "server/tests/test_funding_v1.py", "-q"],
                              capture_output=True, text=True, cwd=ROOT, timeout=120)
    if proc_full.returncode != 0:
        errors.append(f"regressione (review_pipeline + funding_v1) non passa: "
                     f"{proc_full.stdout[-1500:]}")

    if not errors:
        print("VERIFY PASSED - NEXUS TASK #0008 coerente (WORK_PRODUCT_V1/Review Matrix/"
             "Premium Budget Policy/Specialist Registry validati contro schema, 5 acceptance "
             "test A-E rieseguiti con esito reale, nessun provider premium dichiarato "
             "disponibile senza esserlo, regressione PASS)")
        return True
    print("VERIFY FAILED:")
    for e in errors:
        print(f"  - {e}")
    return False


if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
