#!/usr/bin/env python3
"""
11/08 (9) - CISD_TRUE: test onesto IS/OOS + walk-forward a 5 finestre,
ora attraverso run_backtest() (stesso motore di esecuzione di tutte le
altre strategie, niente reimplementazione parallela) sui 3 TF dove la
diagnostica di frequenza mostra un campione utilizzabile (15m/1h/4h).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
N_WINDOWS = 5


def run(tf, br):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy="CISD_TRUE", strategies=["CISD_TRUE"],
                         risk_pct=1.0, bars=BARS, bar_range=br)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor"), "dd": r.get("max_dd_pct")}


def main():
    for tf in ("15m", "1h", "4h"):
        is_r = run(tf, (0.0, 0.6))
        oos_r = run(tf, (0.6, 1.0))
        print(f"{tf}  IS pf={is_r['pf']} n={is_r['trades']} dd={is_r['dd']}%   "
              f"OOS pf={oos_r['pf']} n={oos_r['trades']} dd={oos_r['dd']}%", flush=True)
        row = []
        for w in range(N_WINDOWS):
            br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
            r = run(tf, br)
            row.append(f"{r['pf']}/{r['trades']}")
        print("  walk-forward: " + "  |  ".join(row), flush=True)


if __name__ == "__main__":
    main()
