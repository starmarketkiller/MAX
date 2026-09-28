#!/usr/bin/env python3
"""Verifica INDIPENDENTE del NEXUS Orchestrator V1 Core - non si fida del
self-report, ricontrolla dai file grezzi (acceptance test 1/2) e dallo stato
reale del repository che le affermazioni chiave siano vere. Fail-closed."""
import json
import math
import os
import subprocess
import sys


def _deep_isclose(a, b):
    """Stessa lezione gia' appresa nella fase precedente (Local Model
    Bake-Off V1, pilot v2): un confronto '==' stretto su dict con float
    prodotti da somme in ordine diverso produce falsi negativi per rumore
    di arrotondamento (~1e-15), non per errori di logica reali."""
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a.keys()) == set(b.keys()) and all(_deep_isclose(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_deep_isclose(x, y) for x, y in zip(a, b))
    return a == b

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))


def _load(fname):
    with open(os.path.join(ORCH_DIR, fname), encoding="utf-8") as f:
        return json.load(f)["payload"]


def verify():
    errors = []

    # Acceptance test 1: deve essere WAITING_APPROVAL (mai COMPLETED - questo task tocca un
    # file reale, deve fermarsi per approvazione, mai auto-applicare) E il file tracciato
    # reale NON deve essere stato modificato.
    at1 = _load("acceptance_test_1_result_v1.json")
    final_state = at1["final_task_record"]["state"]
    if final_state != "WAITING_APPROVAL":
        errors.append(f"acceptance test 1: stato finale atteso WAITING_APPROVAL, trovato "
                     f"{final_state}")
    real_test_file = os.path.join(ROOT, "server", "tests", "test_research_control_plane_v2.py")
    with open(real_test_file, encoding="utf-8") as f:
        real_lines = f.readlines()
    if "== 8" not in real_lines[8] or "== 8" not in real_lines[9]:
        errors.append("acceptance test 1: il file REALE del repository risulta modificato "
                     "(le righe 9-10 non contengono piu' '== 8') - l'Orchestrator non deve "
                     "MAI applicare automaticamente una patch a un file reale senza "
                     "approvazione")
    diff_path = os.path.join(ORCH_DIR, "proposed_patches", "hypothesis_count_fix_v1.diff")
    if not os.path.exists(diff_path):
        errors.append("acceptance test 1: manca l'artifact della patch proposta "
                     f"({diff_path})")
    sandbox_leftover = os.path.join(ROOT, "server", "tests",
                                   "_orchestrator_sandbox_hypothesis_count_patch_v1.py")
    if os.path.exists(sandbox_leftover):
        errors.append("acceptance test 1: il file di verifica sandbox effimero non e' stato "
                     "ripulito (dovrebbe essere cancellato a fine verifica)")

    # Acceptance test 2: entrambi i task devono essere COMPLETED, il risultato deve
    # corrispondere davvero al riferimento indipendente (ricalcolato qui, non solo letto).
    at2 = _load("acceptance_test_2_result_v1.json")
    if at2["task_a"]["state"] != "COMPLETED":
        errors.append(f"acceptance test 2: TASK A atteso COMPLETED, trovato "
                     f"{at2['task_a']['state']}")
    if at2["task_b"]["state"] != "COMPLETED":
        errors.append(f"acceptance test 2: TASK B atteso COMPLETED, trovato "
                     f"{at2['task_b']['state']}")
    result_artifact = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_28",
                                   "acceptance2_result_breakout_acc_temporal_v1.json")
    if not os.path.exists(result_artifact):
        errors.append(f"acceptance test 2: artifact di output mancante: {result_artifact}")
    else:
        sys.path.insert(0, ORCH_DIR)
        from run_pilot_worker_v2 import _load_breakout_acc_events, _reference_temporal_concentration  # noqa: E402
        events = _load_breakout_acc_events()
        expected = _reference_temporal_concentration(events)
        with open(result_artifact, encoding="utf-8") as f:
            actual = json.load(f)
        if not _deep_isclose(actual, expected):
            errors.append("acceptance test 2: il risultato salvato NON corrisponde (con "
                         "tolleranza sui float) al ricalcolo indipendente fatto ORA da questo "
                         "verificatore (non solo al riferimento salvato nel file originale)")

    # Il report finale deve avere una decisione valida e coerente con gli stati reali.
    report = _load("orchestrator_core_final_report_v1.json")
    if report["decision"] not in ("ORCHESTRATOR_V1_OPERATIONAL",
                                  "ORCHESTRATOR_V1_OPERATIONAL_WITH_LIMITATIONS",
                                  "ORCHESTRATOR_V1_NEEDS_REVISION"):
        errors.append(f"decisione finale non valida: {report['decision']}")
    if (report["decision"] == "ORCHESTRATOR_V1_OPERATIONAL" and
            (final_state != "WAITING_APPROVAL" or at2["task_b"]["state"] != "COMPLETED")):
        errors.append("decisione ORCHESTRATOR_V1_OPERATIONAL ma gli acceptance test non "
                     "mostrano entrambi l'esito atteso")

    # Test suite core deve passare per intero.
    proc = subprocess.run([sys.executable, "-m", "pytest", "server/orchestrator_v1/core/",
                          "server/tests/test_orchestrator_v1_core.py", "-q"],
                         capture_output=True, text=True, cwd=ROOT, timeout=120)
    if proc.returncode != 0:
        errors.append(f"suite di test core non passa: {proc.stdout[-1000:]}")

    if not errors:
        print("VERIFY PASSED - Orchestrator V1 Core coerente con acceptance test e stato repo")
        return True
    print("VERIFY FAILED:")
    for e in errors:
        print(f"  - {e}")
    return False


if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
