#!/usr/bin/env python3
"""
11/08 (10) - TURTLE_SOUP_CHOCH: la nota vault "Strategie/Turtle Soup.md"
aveva gia' testato il CHoCH fractal fedele richiesto sulla STESSA barra
del sweep (0 trade su H1/4h, storico Yahoo ~2 anni) e diagnosticato il
problema (l'allineamento stesso-bar, non i parametri). Mai testata la
correzione ovvia: CHoCH entro una finestra di N barre DOPO il sweep,
sui 7+ anni Dukascopy invece dei 2 di Yahoo.

Confronto diretto TURTLE_SOUP (baseline attuale) vs TURTLE_SOUP_CHOCH,
stesso TF, stesso storico, IS/OOS + walk-forward a 5 finestre.
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
    for strat in ("TURTLE_SOUP", "TURTLE_SOUP_CHOCH"):
        for tf in ("1h", "4h"):
            is_r = run(strat, tf, (0.0, 0.6))
            oos_r = run(strat, tf, (0.6, 1.0))
            print(f"{strat:<20}{tf:<4} IS pf={is_r['pf']} n={is_r['trades']} dd={is_r['dd']}%   "
                  f"OOS pf={oos_r['pf']} n={oos_r['trades']} dd={oos_r['dd']}%", flush=True)
            row = []
            for w in range(N_WINDOWS):
                br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
                r = run(strat, tf, br)
                row.append(f"{r['pf']}/{r['trades']}")
            print("  walk-forward: " + "  |  ".join(row), flush=True)


if __name__ == "__main__":
    main()
