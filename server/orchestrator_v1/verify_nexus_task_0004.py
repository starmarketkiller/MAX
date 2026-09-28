#!/usr/bin/env python3
"""Verifica INDIPENDENTE di NEXUS TASK #0004 (Merge Escalation Resolution) -
ricalcola da zero il valore risolto da Claude, confrontandolo col file
reale, non si fida del self-report. Fail-closed."""
import json
import os
import subprocess
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
PHASE722_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_22")
PHASE726_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_26")


def _load(fname):
    with open(os.path.join(ORCH_DIR, fname), encoding="utf-8") as f:
        return json.load(f)


def verify():
    errors = []
    result = _load("nexus_task_0004_result_v1.json")

    if result["final_state"] != "COMPLETED":
        errors.append(f"stato finale atteso COMPLETED, trovato {result['final_state']}")
    if result["decision"] != "ESCALATION_MERGED":
        errors.append(f"decisione attesa ESCALATION_MERGED, trovata {result['decision']}")

    # Ricalcolo INDIPENDENTE del valore, direttamente dal dataset canonico, senza fidarsi
    # ne' del risultato salvato ne' della formula del builder - implementazione separata qui.
    with open(os.path.join(PHASE722_DIR, "canonical_economic_dataset_v1.json"),
             encoding="utf-8") as f:
        events = json.load(f)["payload"]["events"]
    if len(events) != 13:
        errors.append(f"atteso 13 eventi nel dataset canonico ORDER_BLOCK, trovati {len(events)}")

    ratios = []
    for e in events:
        is_buy = e["direction"] == 1
        if is_buy:
            captured = e["exit_price"] - e["entry_price"]
            available = e["entry_tp"] - e["entry_price"]
        else:
            captured = e["entry_price"] - e["exit_price"]
            available = e["entry_price"] - e["entry_tp"]
        if available == 0:
            continue
        ratios.append(captured / available)
    independent_mean = sum(ratios) / len(ratios) if ratios else None

    with open(os.path.join(PHASE726_DIR, "cross_strategy_learning_packets_v1.json"),
             encoding="utf-8") as f:
        saved = json.load(f)["payload"]
    saved_text = saved["packets"]["ORDER_BLOCK"]["exit_efficiency"]
    if saved_text == "NOT_AVAILABLE":
        errors.append("ORDER_BLOCK.exit_efficiency e' ancora NOT_AVAILABLE - merge non riuscito")
    else:
        rounded = round(independent_mean, 2)
        if str(rounded) not in saved_text and str(rounded).replace(".", ",") not in saved_text:
            errors.append(f"il valore ricalcolato indipendentemente ({rounded}) non compare "
                         f"nel testo salvato: {saved_text!r}")

    # Il valore deve essere IDENTICO a quello gia' calcolato in NEXUS TASK #0001 (nessuna
    # deriva fra le due misure indipendenti fatte in fasi diverse).
    task0001_path = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_28",
                                "nexus0001_result_order_block_exitfx_v1.json")
    if os.path.exists(task0001_path):
        with open(task0001_path, encoding="utf-8") as f:
            task0001_value = json.load(f)["mean_exit_efficiency_ratio"]
        if abs(task0001_value - independent_mean) > 1e-9:
            errors.append(f"il ricalcolo indipendente ({independent_mean}) diverge dal valore "
                         f"gia' calcolato in NEXUS TASK #0001 ({task0001_value})")

    # BREAKOUT_ACC.temporal_concentration (gia' applicato in TASK #0003) non deve essere
    # cambiato da questo task.
    if saved["packets"]["BREAKOUT_ACC"]["temporal_concentration"] == "NOT_AVAILABLE":
        errors.append("BREAKOUT_ACC.temporal_concentration risulta NOT_AVAILABLE - "
                     "regressione rispetto a NEXUS TASK #0003")

    # Suite Phase 7.26 completa deve passare senza esclusioni.
    proc = subprocess.run([sys.executable, "-m", "pytest", "phase7_26/test_phase_7_26.py", "-q"],
                         capture_output=True, text=True,
                         cwd=os.path.join(ROOT, "server", "research_scripts", "phase7"),
                         timeout=120)
    if proc.returncode != 0:
        errors.append(f"test_phase_7_26.py non passa: {proc.stdout[-1500:]}")

    if not errors:
        print("VERIFY PASSED - NEXUS TASK #0004 coerente con ricalcolo indipendente e stato repo")
        return True
    print("VERIFY FAILED:")
    for e in errors:
        print(f"  - {e}")
    return False


if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
