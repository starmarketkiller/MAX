#!/usr/bin/env python3
"""
11/08 (18) - stessa idea gia' provata su TURTLE_SOUP_CHOCH: CHoCH
fractal richiesto entro una finestra di N barre invece che sulla
STESSA barra di altri trigger. La nota vault di IFVG aveva gia'
generalizzato l'insight ("vero anche per TURTLE_SOUP, non solo qui")
ma non era mai stata applicata a se stessa. SMS_BMS_RTO condivide la
stessa struttura (4 condizioni su una barra, CHoCH incluso).

Baseline IFVG e SMS_BMS_RTO danno 0 trade strutturali (verificato).
Confronto diretto baseline (0 trade, quindi nessun IS/OOS possibile)
vs CHOCH_WINDOW, sui TF di profilo reali: IFVG=4h, SMS_BMS_RTO=1d.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
N_WINDOWS = 5

PAIRS = [
    ("IFVG", "IFVG_CHOCH_WINDOW", "4h"),
    ("SMS_BMS_RTO", "SMS_BMS_RTO_CHOCH_WINDOW", "1d"),
]


def run(strat, tf, br):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                         risk_pct=1.0, bars=BARS, bar_range=br)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor"), "dd": r.get("max_dd_pct")}


def main():
    for baseline, variant, tf in PAIRS:
        for strat in (baseline, variant):
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
