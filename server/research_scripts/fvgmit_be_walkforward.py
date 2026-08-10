#!/usr/bin/env python3
"""
10/08 (12) - verifica di credibilita' sul risultato piu' vistoso del test
exit-management esteso: FVG_MIT + breakeven_r=0.5 (OOS PF 1.52->4.23, 49
trade) - ma scelto sull'IS come "il meno peggio" di una griglia tutta in
perdita (IS PF 0.39 contro un baseline IS gia' debole di 0.68), lo stesso
schema che oggi si e' sgonfiato piu' volte (ensemble greedy, LDN_REVERSAL/
AMD_REVERSAL). Walk-forward a 5 finestre sequenziali, come gia' fatto per
BREAKOUT_ACC/LIQ_SWEEP - se il vantaggio e' concentrato in una sola
finestra fortunata, non e' un edge reale.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, TF, BARS = "XAUUSD", "4h", 60000
STRAT = "FVG_MIT"
ATR_SL, ATR_TP = 1.5, 3.0
N_WINDOWS = 5


def run(br, **kw):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=TF, strategy=STRAT, strategies=[STRAT],
                         risk_pct=1.0, atr_sl=ATR_SL, atr_tp=ATR_TP,
                         bar_range=br, bars=BARS, **kw)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor")}


def main():
    print(f"{'Finestra':<12}{'BE=0.5 PF':>12}{'n':>5}   {'Baseline PF':>12}{'n':>5}")
    for w in range(N_WINDOWS):
        br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
        r_be = run(br, breakeven_r=0.5)
        r_base = run(br)
        print(f"{w+1}/{N_WINDOWS:<8}{str(r_be['pf']):>12}{r_be['trades']:>5}   "
              f"{str(r_base['pf']):>12}{r_base['trades']:>5}")


if __name__ == "__main__":
    main()
