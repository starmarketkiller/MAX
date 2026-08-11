#!/usr/bin/env python3
"""
11/08 (15) - riverifica del gate fuori-range su MALAYSIAN_SNR_V2_RETEST
attraverso run_backtest (SL/TP strutturale reale rispettato) sullo
storico ampliato, IS/OOS + walk-forward a 5 finestre, confronto diretto
con la baseline RETEST senza gate.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
N_WINDOWS = 5


def run(strat, tf, br):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                         risk_pct=1.0, bars=BARS, bar_range=br)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor"), "dd": r.get("max_dd_pct")}


def main():
    for tf in ("30m", "1h"):
        for strat in ("MALAYSIAN_SNR_V2_RETEST", "MALAYSIAN_SNR_V2_RETEST_OUTRANGE"):
            is_r, oos_r = run(strat, tf, (0.0, 0.6)), run(strat, tf, (0.6, 1.0))
            print(f"\n=== {strat} @ {tf} ===", flush=True)
            print(f"  IS pf={is_r['pf']} n={is_r['trades']} dd={is_r['dd']}%   "
                  f"OOS pf={oos_r['pf']} n={oos_r['trades']} dd={oos_r['dd']}%", flush=True)
            row = []
            for w in range(N_WINDOWS):
                br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
                r = run(strat, tf, br)
                row.append(f"{r['pf']}/{r['trades']}")
            print("  walk-forward: " + "  |  ".join(row), flush=True)


if __name__ == "__main__":
    main()
