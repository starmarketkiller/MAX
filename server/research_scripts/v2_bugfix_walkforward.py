#!/usr/bin/env python3
"""
11/08 (14) - richiesta esplicita dell'utente: analisi una-ad-una delle
34 strategie escluse dal nucleo, cercando miglioramenti reali. Trovati
(git log 2a5c2f1) 3 bug documentati e mai corretti nelle varianti "_v2"
(brief esterno "Decomposizione Edge"), portati fedelmente e confermati
empiricamente a 0 trade:
  - SILVER_BULLET_V2: check "fresh" auto-referenziale (confrontava la
    barra che definisce il gap con se stessa) - corretto.
  - FVG_CONT_V2: check "EntryAt50Pct" auto-referenziale (stessa causa) -
    rimosso (nessuna informazione reale da recuperare).
  - OTE_CONT_V2: fib618/fib705 invertiti sul lato SELL (intervallo
    impossibile) - corretto, ma resta 0 trade su ogni TF (il lato BUY e'
    gia' quasi tautologico di suo, non e' colpa del bug SELL).

Walk-forward a 5 finestre sui due che ora sparano davvero.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
N_WINDOWS = 5

CANDIDATES = [
    ("SILVER_BULLET_V2", "15m"),
    ("FVG_CONT_V2", "4h"),
]


def run(strat, tf, br):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                         risk_pct=1.0, bars=BARS, bar_range=br)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor"), "dd": r.get("max_dd_pct")}


def main():
    for strat, tf in CANDIDATES:
        is_r, oos_r = run(strat, tf, (0.0, 0.6)), run(strat, tf, (0.6, 1.0))
        print(f"\n=== {strat} @ {tf} (corretta) ===", flush=True)
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
