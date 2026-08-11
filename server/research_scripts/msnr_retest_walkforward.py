#!/usr/bin/env python3
"""
11/08 - walk-forward a 5 finestre su MALAYSIAN_SNR_V2_RETEST, confermato
dall'utente dopo il test diagnostico IS/OOS (4h/1h/30m) e la
caratterizzazione delle zone OC (60% tengono, 40% rompono, 91% dei rotti
fa retest entro 12 barre - vedi vault MALAYSIAN_SNR Porting Tier 1).
Un solo split 60/40 non basta a fidarsi, stesso trattamento gia' dato a
BREAKOUT_ACC+regime e FVG_MIT+breakeven oggi. Testato su 1h e 30m (il 4h
ha troppo pochi trade per finestra per essere utile qui).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 60000
STRAT = "MALAYSIAN_SNR_V2_RETEST"
ATR_SL, ATR_TP = 1.5, 3.0
N_WINDOWS = 5


def run(tf, br):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=STRAT, strategies=[STRAT],
                         risk_pct=1.0, atr_sl=ATR_SL, atr_tp=ATR_TP,
                         bar_range=br, bars=BARS)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor")}


def main():
    for tf in ["1h", "30m"]:
        print(f"\n--- {STRAT} su {tf}: walk-forward a {N_WINDOWS} finestre ---")
        print(f"{'Finestra':<12}{'PF':>10}{'n':>6}")
        for w in range(N_WINDOWS):
            br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
            r = run(tf, br)
            print(f"{w+1}/{N_WINDOWS:<8}{str(r['pf']):>10}{r['trades']:>6}")


if __name__ == "__main__":
    main()
