#!/usr/bin/env python3
"""
11/08 (5) - walk-forward a 5 finestre sui candidati "ricetta migliore"
emersi da profile_recipe_audit.py, prima di toccare NXS_StrategyProfiles.mqh.
Stessa disciplina usata per CRT/RETEST: un solo split IS/OOS non basta.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
N_WINDOWS = 5

# (strategia, TF, slMult, tpMult, htf, beR)
CANDIDATES = [
    ("FVG_CONT", "4h", 1.0, 4.5, True, 0.0),
    ("SAR", "4h", 1.5, 4.0, True, 0.0),
    ("TURTLE_SOUP", "1h", 1.0, 4.5, True, 0.0),
    ("EMA_PULLBACK", "1h", 1.5, 4.0, True, 0.0),
    ("TSI", "1d", 1.5, 4.5, True, 1.0),
    ("ADX_RSI", "1d", 1.0, 10.0, True, 1.5),
]


def run(strat, tf, br, sl, tp, htf, be):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                         risk_pct=1.0, bars=BARS, bar_range=br,
                         atr_sl=sl, atr_tp=tp, htf_filter=htf, breakeven_r=be)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor")}


def run_flat(strat, tf, br):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                         risk_pct=1.0, bars=BARS, bar_range=br, atr_sl=1.5, atr_tp=3.0)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor")}


def main():
    for strat, tf, sl, tp, htf, be in CANDIDATES:
        print(f"\n=== {strat} @ {tf}  ricetta(sl{sl}/tp{tp}/htf{int(htf)}/be{be}) ===", flush=True)
        rec_row, flat_row = [], []
        rec_wins = 0
        for w in range(N_WINDOWS):
            br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
            r_rec = run(strat, tf, br, sl, tp, htf, be)
            r_flat = run_flat(strat, tf, br)
            rec_row.append(f"{r_rec['pf']}/{r_rec['trades']}")
            flat_row.append(f"{r_flat['pf']}/{r_flat['trades']}")
            if r_rec["pf"] is not None and r_flat["pf"] is not None and r_rec["pf"] > r_flat["pf"]:
                rec_wins += 1
        print("  ricetta: " + "  |  ".join(rec_row))
        print("  flat:    " + "  |  ".join(flat_row))
        print(f"  ricetta batte flat in {rec_wins}/{N_WINDOWS} finestre", flush=True)


if __name__ == "__main__":
    main()
