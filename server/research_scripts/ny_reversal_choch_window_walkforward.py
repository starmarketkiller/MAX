#!/usr/bin/env python3
"""
11/08 (19) - NY_REVERSAL condivide lo stesso pattern gia' visto su
TURTLE_SOUP/IFVG/SMS_BMS_RTO: `sig_ny_reversal` richiede il CHoCH
fractal sulla STESSA barra dello sweep+reclaim del range di Londra
(6-12 GMT), non entro una finestra. Registrata NY_REVERSAL_CHOCH_WINDOW,
stessa detection CHoCH ma verificata entro 5 barre.

Smoke test grezzo (bars=110000, nessuno split) mostrava campione molto
piu' grande ma PF/DD peggiori (1h: 30 trade pf1.21 dd6% -> 103 trade
pf1.07 dd15.8%; 30m: 69 trade pf1.3 dd6.3% -> 228 trade pf0.88 dd25.5%)
- serve IS/OOS + walk-forward per capire se e' solo piu' rumore o un
peggioramento reale.
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
    for tf in ("1h", "30m"):
        for strat in ("NY_REVERSAL", "NY_REVERSAL_CHOCH_WINDOW"):
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
