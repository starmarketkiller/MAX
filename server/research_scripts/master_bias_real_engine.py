#!/usr/bin/env python3
"""
12/08 - riverifica sul motore vero la "pipeline gerarchica master->slave"
(Metodo 2, 10/08, phase3c_bias_pipeline.py) che aveva trovato "alcuni
miglioramenti isolati" su SAR/FVG_CONT/TSI con BREAKOUT_ACC come master
di bias persistente. Quello script usava un simulatore PROPRIO (SL/TP
piatto 1.5x/3.0x ATR hardcoded per ogni slave, non il profilo/SL/TP reale
di ciascuna) - stessa categoria di problema gia' trovata con
ensemble_engine_search.py e msnr_retest_gates.py, mai riverificata sul
motore vero dopo quella scoperta.

Qui: run_backtest(master_bias=...) (aggiunto oggi, stesso principio di
regime_filter - precomputa il bias persistente del master, poi lo usa
come gate su _find_signal, ogni slave gira col proprio SL/TP reale).
Stesso TF=4h per master e slave dello script originale (per confrontare
la stessa identica claim, non una versione diversa) - IS(60%)/OOS(40%)
+ walk-forward a 5 finestre, baseline vs biased.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS, TF = "XAUUSD", 110000, "4h"
MASTER = "BREAKOUT_ACC"
SLAVES = ["SAR", "FVG_CONT", "TSI"]
N_WINDOWS = 5


def run(strat, bar_range, biased):
    kwargs = dict(symbol=SYMBOL, timeframe=TF, strategy=strat, strategies=[strat],
                  risk_pct=1.0, bars=BARS, bar_range=bar_range)
    if biased:
        kwargs["master_bias"] = MASTER
    r = bt.run_backtest(**kwargs)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor"), "dd": r.get("max_dd_pct")}


def main():
    for slave in SLAVES:
        for label, biased in (("baseline", False), (f"+{MASTER} bias", True)):
            is_r, oos_r = run(slave, (0.0, 0.6), biased), run(slave, (0.6, 1.0), biased)
            print(f"\n=== {slave} [{label}] @ {TF} ===", flush=True)
            print(f"  IS pf={is_r['pf']} n={is_r['trades']} dd={is_r['dd']}%   "
                  f"OOS pf={oos_r['pf']} n={oos_r['trades']} dd={oos_r['dd']}%", flush=True)
            row = []
            for w in range(N_WINDOWS):
                br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
                r = run(slave, br, biased)
                row.append(f"{r['pf']}/{r['trades']}")
            print("  walk-forward: " + "  |  ".join(row), flush=True)


if __name__ == "__main__":
    main()
