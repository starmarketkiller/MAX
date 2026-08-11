#!/usr/bin/env python3
"""
11/08 (16) - TSI e' l'unico problema aperto senza soluzione nel nucleo
(OOS PF 0.71/39 sul vero TF di profilo, 1d). Il trigger MQL5 e' un cross
puro TSI/signal-line, gia' fedele al 100% nel port Python - non un bug.
Ipotesi nuova (non di fedelta'): richiedere che il cross parta da una
zona di momentum estremo (soglia=15, mediana del TSI assoluto su
XAUUSD 1d) invece di un cross qualunque vicino allo zero - stessa
ragione per cui RSI si usa con soglie di ipercomprato/ipervenduto.

Confronto diretto TSI (baseline) vs TSI_EXTREME, 1d (vero TF di
profilo) e 4h (supplementare, piu' campione), IS/OOS + walk-forward.
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
    for tf in ("1d", "4h"):
        for strat in ("TSI", "TSI_EXTREME"):
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
