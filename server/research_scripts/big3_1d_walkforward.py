#!/usr/bin/env python3
"""
10/08 (13) - lo scan multi-TF ha mostrato PF OOS molto piu' alti su 1d per
MACD/TURTLE_SOUP/BREAKOUT_ACC (2.12/2.18/3.21 contro 1.63/1.66/1.71 su 4h)
ma su campioni piccoli (20-33 trade, un solo split 60/40). Prima di
considerare di spostarle su 1d nel demo: walk-forward a 5 finestre, stesso
trattamento gia' applicato a BREAKOUT_ACC+regime e FVG_MIT+breakeven oggi -
non ci si fida di un singolo split quando il campione e' piccolo.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 60000
STRATS = ["MACD", "TURTLE_SOUP", "BREAKOUT_ACC"]
ATR_SL, ATR_TP = 1.5, 3.0
N_WINDOWS = 5


def run(strat, tf, br):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                         risk_pct=1.0, atr_sl=ATR_SL, atr_tp=ATR_TP,
                         bar_range=br, bars=BARS)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor")}


def main():
    for strat in STRATS:
        print(f"\n--- {strat}: walk-forward a {N_WINDOWS} finestre, 1d vs 4h ---")
        print(f"{'Finestra':<12}{'1d PF':>10}{'n':>5}   {'4h PF':>10}{'n':>5}")
        for w in range(N_WINDOWS):
            br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
            r_1d = run(strat, "1d", br)
            r_4h = run(strat, "4h", br)
            print(f"{w+1}/{N_WINDOWS:<8}{str(r_1d['pf']):>10}{r_1d['trades']:>5}   "
                  f"{str(r_4h['pf']):>10}{r_4h['trades']:>5}")


if __name__ == "__main__":
    main()
