#!/usr/bin/env python3
"""
11/08 (17) - FVG_MIT e' il secondo problema aperto senza soluzione nel
nucleo (OOS PF 1.01/78 sul vero TF di profilo, 4h). Il trigger MQL5
confronta il gap tra le candele i-6/i-4 SOLO con la barra CORRENTE i -
ogni coppia di candele viene valutata per gap+mitigazione UNA SOLA
VOLTA, mai piu' tardi se il prezzo impiega piu' tempo a tornare sul
gap. Non un bug di fedelta' (MQL5 fa lo stesso) - una variante
sperimentale nuova: registro di zone attive fino a 15 barre, stessa
architettura di successo di SH_BMS_RTO_V2/TURTLE_SOUP_CHOCH.

Confronto diretto FVG_MIT (baseline) vs FVG_MIT_WINDOW, 4h (vero TF di
profilo) e 1h (supplementare), IS/OOS + walk-forward.
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
    for tf in ("4h", "1h"):
        for strat in ("FVG_MIT", "FVG_MIT_WINDOW"):
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
