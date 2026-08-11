#!/usr/bin/env python3
"""
11/08 (20) - Le 4 SCALP_* (BB_FADE/EMA/RANGE_BRK/RSI_SNAP) sono
flaggate nel report diagnostico come "problema aperto": PF vicino/sopra
1 su campioni enormi (3000-5000 trade/15m) ma drawdown sproporzionati
(35-79%) - tipico di alta frequenza senza filtro di qualita'.

Scan grezzo (senza split) con regime_filter=(STRONG_TREND,) mostra un
pattern consistente sulle 4: drawdown circa dimezzato, PF stabile o
leggermente migliore, campione ridotto a ~25-35% del totale:

  BB_FADE:    3215/dd60 -> 867/dd32   (pf 1.02->1.05)
  EMA:        3728/dd82 -> 956/dd45   (pf 0.93->0.94)
  RANGE_BRK:  5041/dd79 -> 1712/dd39  (pf 0.97->1.02)
  RSI_SNAP:   3135/dd50 -> 1554/dd31  (pf 0.99->1.03)

VOLATILE e' ancora piu' aggressivo (dd a singola cifra) ma il campione
crolla a 60-320 trade - troppo poco per fidarsi da solo.

Verifica IS/OOS + walk-forward a 5 finestre per capire se il filtro
STRONG_TREND regge un test onesto o e' solo un artefatto del taglio
campione (meno trade = meno drawdown quasi per costruzione).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS, TF = "XAUUSD", 110000, "15m"
N_WINDOWS = 5
STRATS = ("SCALP_BB_FADE", "SCALP_EMA", "SCALP_RANGE_BRK", "SCALP_RSI_SNAP")


def run(strat, br, rf=None):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=TF, strategy=strat, strategies=[strat],
                         risk_pct=1.0, bars=BARS, bar_range=br, regime_filter=rf)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor"), "dd": r.get("max_dd_pct")}


def main():
    for strat in STRATS:
        for label, rf in (("baseline", None), ("STRONG_TREND", (bt._REGIME_STRONG_TREND,))):
            is_r, oos_r = run(strat, (0.0, 0.6), rf), run(strat, (0.6, 1.0), rf)
            print(f"\n=== {strat} [{label}] ===", flush=True)
            print(f"  IS pf={is_r['pf']} n={is_r['trades']} dd={is_r['dd']}%   "
                  f"OOS pf={oos_r['pf']} n={oos_r['trades']} dd={oos_r['dd']}%", flush=True)
            row = []
            for w in range(N_WINDOWS):
                br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
                r = run(strat, br, rf)
                row.append(f"{r['pf']}/{r['trades']}/dd{r['dd']}")
            print("  walk-forward: " + "  |  ".join(row), flush=True)


if __name__ == "__main__":
    main()
