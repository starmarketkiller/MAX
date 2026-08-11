#!/usr/bin/env python3
"""
11/08 (2) - completa la riverifica sullo storico ampliato per le
strategie del nucleo demo non ancora testate nel primo giro
(wide_window_reverify.py aveva coperto solo MACD/TURTLE_SOUP/
BREAKOUT_ACC/LIQ_SWEEP/SAR/TSI/FVG_CONT/CRT). Qui le restanti 8, ognuna
sul proprio timeframe di profilo (NXS_StrategyProfiles.mqh).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
N_WINDOWS = 5

REST = [
    ("ADX_RSI", "1d"),
    ("EMA_PULLBACK", "1h"),
    ("LONDON_BO", "1d"),
    ("FVG_MIT", "1d"),
    ("AMD_CONT", "30m"),
    ("LDN_REVERSAL", "15m"),
    ("AMD_REVERSAL", "15m"),
    ("THREE_BAR_DELIVERY_BREAK", "4h"),
]


def run(strat, tf, br):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                         risk_pct=1.0, atr_sl=1.5, atr_tp=3.0, bars=BARS, bar_range=br)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor")}


def main():
    for strat, tf in REST:
        r_is = run(strat, tf, (0.0, 0.6))
        r_oos = run(strat, tf, (0.6, 1.0))
        print(f"{strat:<26}{tf:<6}IS pf={str(r_is['pf']):<7}n={r_is['trades']:<6}  "
              f"OOS pf={str(r_oos['pf']):<7}n={r_oos['trades']}")
        row = []
        for w in range(N_WINDOWS):
            br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
            r = run(strat, tf, br)
            row.append(f"{r['pf']}/{r['trades']}")
        print("  walk-forward: " + "  |  ".join(row))


if __name__ == "__main__":
    main()
