#!/usr/bin/env python3
"""Verifica INDIPENDENTE di NEXUS TASK #0005 (Funding Priority & Opportunity
Framework V1) - non si fida del self-report, ricalcola gli score da zero e
ricontrolla contro gli schemi. Fail-closed."""
import json
import os
import subprocess
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
FUNDING_DIR = os.path.join(ROOT, "server", "funding_v1")
CONTRACTS_DIR = os.path.join(ROOT, "contracts")

sys.path.insert(0, FUNDING_DIR)
sys.path.insert(0, ORCH_DIR)


def verify():
    errors = []
    from nxs_schema_validator import validate
    from opportunity_scoring import (score_funding_priority, score_technical_priority,
                                    FUNDING_DIMENSION_WEIGHTS, TECHNICAL_CRITERIA_WEIGHTS)

    if abs(sum(FUNDING_DIMENSION_WEIGHTS.values()) - 1.0) > 1e-9:
        errors.append("pesi funding non sommano a 1.0")
    if abs(sum(TECHNICAL_CRITERIA_WEIGHTS.values()) - 1.0) > 1e-9:
        errors.append("pesi technical non sommano a 1.0")

    with open(os.path.join(CONTRACTS_DIR, "opportunity.schema.json"), encoding="utf-8") as f:
        opp_schema = json.load(f)
    with open(os.path.join(FUNDING_DIR, "example_instances", "opportunities_v1.json"),
             encoding="utf-8") as f:
        opportunities = json.load(f)["payload"]["opportunities"]

    if len(opportunities) < 5:
        errors.append(f"attese almeno 5 opportunity di esempio, trovate {len(opportunities)}")

    for opp in opportunities:
        schema_errors = validate(opp, opp_schema)
        if schema_errors:
            errors.append(f"{opp['opportunity_id']}: {schema_errors}")
        # Ricalcolo INDIPENDENTE dei punteggi (non fidarsi del valore salvato).
        recomputed_funding, _ = score_funding_priority(opp["dimensions"])
        recomputed_technical, _ = score_technical_priority(opp["technical_priority"]["criteria"])
        if abs(recomputed_funding - opp["funding_priority"]["score"]) > 1e-6:
            errors.append(f"{opp['opportunity_id']}: funding_priority salvato "
                         f"({opp['funding_priority']['score']}) non corrisponde al ricalcolo "
                         f"({recomputed_funding})")
        if abs(recomputed_technical - opp["technical_priority"]["score"]) > 1e-6:
            errors.append(f"{opp['opportunity_id']}: technical_priority salvato "
                         f"({opp['technical_priority']['score']}) non corrisponde al ricalcolo "
                         f"({recomputed_technical})")

    with open(os.path.join(CONTRACTS_DIR, "opportunity-priority-queue.schema.json"),
             encoding="utf-8") as f:
        queue_schema = json.load(f)
    with open(os.path.join(FUNDING_DIR, "opportunity_priority_queue_v1.json"),
             encoding="utf-8") as f:
        queue = json.load(f)["payload"]
    queue_errors = validate(queue, queue_schema)
    if queue_errors:
        errors.append(f"priority queue: {queue_errors}")

    technical_order = [o["opportunity_id"] for o in queue["ranked_by_technical_priority"]]
    funding_order = [o["opportunity_id"] for o in queue["ranked_by_funding_priority"]]
    if technical_order == funding_order:
        errors.append("i ranking technical e funding sono identici - i due assi non sono "
                     "genuinamente indipendenti")

    proc = subprocess.run([sys.executable, "-m", "pytest", "server/tests/test_funding_v1.py",
                          "-q"], capture_output=True, text=True, cwd=ROOT, timeout=60)
    if proc.returncode != 0:
        errors.append(f"test_funding_v1.py non passa: {proc.stdout[-1000:]}")

    if not errors:
        print("VERIFY PASSED - NEXUS TASK #0005 coerente (ricalcolo indipendente, schemi validi, "
             "assi genuinamente separati)")
        return True
    print("VERIFY FAILED:")
    for e in errors:
        print(f"  - {e}")
    return False


if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
