#!/usr/bin/env python3
"""
11/08 (11) - le 5 confluenze regime trovate l'11/08 (wide_window_reverify.py,
sezione 2) usavano ensemble_engine_search.simulate() - un motore
SEMPLIFICATO, non run_backtest, e tutte sul TF 4h di riferimento sessione
invece del vero TF di profilo di ognuna (TSI/LIQ_SWEEP=1d, SAR/FVG_CONT=4h
gia' corretto, BREAKOUT_ACC=1d). Stessa lezione di CRT v1/v2: non fidarsi
di un motore parallelo prima di riverificare su quello vero.

Aggiunto regime_filter a run_backtest() (opt-in, riusa ind["regime"],
porting fedele di NXS_DetectRegime gia' usato da grid_regime_filter) -
qui riverifica le 5 confluenze sul motore vero, TF di profilo reale,
IS/OOS + walk-forward a 5 finestre.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
N_WINDOWS = 5

REGIME = {
    "STRONG_TREND": (bt._REGIME_STRONG_TREND,),
    "WEAK_TREND": (bt._REGIME_WEAK_TREND,),
    "STRONG_OR_WEAK": (bt._REGIME_STRONG_TREND, bt._REGIME_WEAK_TREND),
}

# (strategia, TF di profilo reale, nome regime)
CANDIDATES = [
    ("BREAKOUT_ACC", "1d", "STRONG_TREND"),
    ("LIQ_SWEEP", "1d", "STRONG_TREND"),
    ("SAR", "4h", "WEAK_TREND"),
    ("TSI", "1d", "WEAK_TREND"),
    ("FVG_CONT", "4h", "STRONG_OR_WEAK"),
]


def run(strat, tf, br, regime=None):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                         risk_pct=1.0, bars=BARS, bar_range=br, regime_filter=regime)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor")}


def main():
    for strat, tf, regime_name in CANDIDATES:
        regime = REGIME[regime_name]
        print(f"\n=== {strat} @ {tf} + {regime_name} (TF di profilo reale) ===", flush=True)
        flat_is, flat_oos = run(strat, tf, (0.0, 0.6)), run(strat, tf, (0.6, 1.0))
        filt_is, filt_oos = run(strat, tf, (0.0, 0.6), regime), run(strat, tf, (0.6, 1.0), regime)
        print(f"  flat:    IS pf={flat_is['pf']} n={flat_is['trades']}   OOS pf={flat_oos['pf']} n={flat_oos['trades']}")
        print(f"  +regime: IS pf={filt_is['pf']} n={filt_is['trades']}   OOS pf={filt_oos['pf']} n={filt_oos['trades']}", flush=True)
        flat_row, filt_row = [], []
        wins = 0
        for w in range(N_WINDOWS):
            br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
            rf, rr = run(strat, tf, br), run(strat, tf, br, regime)
            flat_row.append(f"{rf['pf']}/{rf['trades']}")
            filt_row.append(f"{rr['pf']}/{rr['trades']}")
            if rr["pf"] is not None and rf["pf"] is not None and rr["pf"] > rf["pf"]:
                wins += 1
        print("  flat wf:    " + "  |  ".join(flat_row))
        print("  +regime wf: " + "  |  ".join(filt_row))
        print(f"  regime batte flat in {wins}/{N_WINDOWS} finestre", flush=True)


if __name__ == "__main__":
    main()
