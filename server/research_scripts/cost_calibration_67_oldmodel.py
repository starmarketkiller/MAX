#!/usr/bin/env python3
"""Rerun leggero SOLO con OLD_COST_MODEL (retail_standard) sulle 67 strategie,
necessario per l'audit dei falsi negativi storici (item 8) - non incluso nel
rerun principale a 4 profili (cost_calibration_67_rerun.py)."""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt
from cost_calibration_67_rerun import ALL_STRATEGIES, STRATEGY_TF, SYMBOL, BARS, BAR_RANGE, RISK_PCT, ATR_SL, ATR_TP, run_one

OLD_COST_MODEL = dict(bt.COST_PRESETS["retail_standard"])


def main():
    t0 = time.time()
    results = {}
    for i, strat in enumerate(ALL_STRATEGIES, 1):
        tf = STRATEGY_TF[strat]
        r = run_one(strat, tf, OLD_COST_MODEL)
        results[strat] = r
        print(f"[{i}/{len(ALL_STRATEGIES)}] {strat:<34}{tf:<5} PF={r.get('pf')} n={r.get('n')} "
              f"net={r.get('net')} ({time.time()-t0:.0f}s)", flush=True)
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                            "results", "cost_calibration_67_rerun")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "old_cost_model_results.json"), "w", encoding="utf-8") as f:
        json.dump({"cost_profile": OLD_COST_MODEL, "results": results}, f, indent=2, default=str)
    print(f"\nCompletato in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
