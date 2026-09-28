#!/usr/bin/env python3
"""Verifica INDIPENDENTE di NEXUS TASK #0003 (Approve Safety Net Backfill) -
non si fida del self-report, ricontrolla dai file grezzi e dallo stato
reale del repository. Fail-closed."""
import json
import os
import subprocess
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
PHASE726_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_26")

EXPECTED_CHANGED_FIELDS = {("BREAKOUT_ACC", "temporal_concentration"),
                          ("BREAKOUT_ACC", "exit_efficiency"),
                          ("BREAKOUT_ACC", "execution_degradation"),
                          ("BREAKOUT_ACC", "favorable_before_loss"),
                          ("BREAKOUT_ACC", "adverse_before_win"),
                          ("ORDER_BLOCK", "temporal_concentration")}


def _load(fname):
    with open(os.path.join(ORCH_DIR, fname), encoding="utf-8") as f:
        return json.load(f)


def verify():
    errors = []
    result = _load("nexus_task_0003_result_v1.json")

    if result["final_state"] != "COMPLETED":
        errors.append(f"stato finale atteso COMPLETED, trovato {result['final_state']}")
    if result["decision"] != "BACKFILL_APPROVED_AND_APPLIED":
        errors.append(f"decisione attesa BACKFILL_APPROVED_AND_APPLIED, trovata "
                     f"{result['decision']}")
    if result["premium_calls"] != 0 or result["premium_cost"] != 0:
        errors.append("premium_calls/premium_cost devono essere 0")

    # 1. Il file reale deve davvero essere stato rigenerato RIESEGUENDO il builder - non un
    # patch manuale. Ricalcolo IO STESSO chiamando build() e confronto col file salvato.
    sys.path.insert(0, PHASE726_DIR)
    import build_cross_strategy_learning_packet as packet_builder  # noqa: E402
    sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
    from canonical_utils import canonical_sha256, load_json  # noqa: E402

    saved = load_json(os.path.join(PHASE726_DIR, "cross_strategy_learning_packets_v1.json"))
    fresh = packet_builder.build()
    if canonical_sha256(saved["payload"]) != canonical_sha256(fresh):
        errors.append("il file reale NON corrisponde a una rigenerazione fresca del builder - "
                     "sospetto patch manuale invece di rebuild")

    # 2. ORDER_BLOCK.exit_efficiency deve essere rimasto esattamente NOT_AVAILABLE.
    if saved["payload"]["packets"]["ORDER_BLOCK"]["exit_efficiency"] != "NOT_AVAILABLE":
        errors.append("ORDER_BLOCK.exit_efficiency e' stato modificato - MAI permesso in "
                     "questo task")

    # 3. Confronto con la versione precedente (git) - esattamente i 6 campi attesi cambiati.
    proc = subprocess.run(["git", "show", "HEAD~1:server/research_scripts/phase7/phase7_26/"
                          "cross_strategy_learning_packets_v1.json"],
                         capture_output=True, text=True, cwd=ROOT)
    if proc.returncode == 0:
        previous = json.loads(proc.stdout)["payload"]
        changed = set()
        for strat in previous["packets"]:
            for field in previous["packets"][strat]:
                if field == "provenance":
                    continue
                if previous["packets"][strat][field] != saved["payload"]["packets"][strat][field]:
                    changed.add((strat, field))
        if changed != EXPECTED_CHANGED_FIELDS:
            errors.append(f"campi effettivamente cambiati rispetto al commit precedente "
                         f"{changed} non corrisponde all'atteso {EXPECTED_CHANGED_FIELDS}")
    else:
        errors.append("impossibile leggere la versione precedente del file da git per il diff")

    # 4. Suite Phase 7.26 completa (SENZA esclusioni) deve passare.
    proc2 = subprocess.run([sys.executable, "-m", "pytest", "phase7_26/test_phase_7_26.py", "-q"],
                          capture_output=True, text=True,
                          cwd=os.path.join(ROOT, "server", "research_scripts", "phase7"),
                          timeout=120)
    if proc2.returncode != 0:
        errors.append(f"test_phase_7_26.py (completo, senza esclusioni) non passa: "
                     f"{proc2.stdout[-1500:]}")

    # 5. Nessun file MQL5/Product-Platform toccato in nessuno degli ultimi commit di questa
    # task (il vero confine di sicurezza - contracts/server/vault sono legittimamente in
    # scope per questo lavoro di infrastruttura/backfill).
    proc3 = subprocess.run(["git", "diff", "--name-only", "HEAD~2", "HEAD"], capture_output=True,
                          text=True, cwd=ROOT)
    changed_files = [line.strip() for line in proc3.stdout.strip().splitlines() if line.strip()]
    forbidden_prefixes = ("MQL5/", "Product-Platform/")
    unexpected = [f for f in changed_files if f.startswith(forbidden_prefixes)]
    if unexpected:
        errors.append(f"file MQL5/Product-Platform modificati: {unexpected}")

    if not errors:
        print("VERIFY PASSED - NEXUS TASK #0003 coerente con i dati grezzi e con lo stato repo")
        return True
    print("VERIFY FAILED:")
    for e in errors:
        print(f"  - {e}")
    return False


if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
