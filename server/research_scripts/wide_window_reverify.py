#!/usr/bin/env python3
"""
11/08 - richiesta esplicita dell'utente: "ho paura che abbiamo insistito
su strategie che erano gia' ottimali" - riverifica sistematica di tutte
le scoperte "buone" della sessione (10-11/08) sul nuovo storico Dukascopy,
cresciuto da 1.618 a 2.636 giorni (63.245 -> 105.304 candele M15, ora dal
2019-05-20 invece che dal 2022-03-04) dopo un refresh dalla produzione.

Stessa disciplina di tutta la sessione: IS(60%)/OOS(40%), walk-forward a
5 finestre dove gia' fatto prima, BARS alzato a 110000 per usare tutto lo
storico nuovo (i vecchi script erano a 60000/70000, ora insufficienti).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as bt
import ensemble_engine_search as e

SYMBOL, BARS = "XAUUSD", 110000
N_WINDOWS = 5
REGIME = {"nessuno": None, "STRONG_TREND": {1}, "WEAK_TREND": {2}, "STRONG+WEAK": {1, 2}}


def run(tf, strat, br, **kw):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                         risk_pct=1.0, atr_sl=1.5, atr_tp=3.0, bars=BARS, bar_range=br, **kw)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor")}


def is_oos(tf, strat, **kw):
    r_is = run(tf, strat, (0.0, 0.6), **kw)
    r_oos = run(tf, strat, (0.6, 1.0), **kw)
    print(f"{strat:<16}{tf:<6}IS pf={str(r_is['pf']):<7}n={r_is['trades']:<6}  "
          f"OOS pf={str(r_oos['pf']):<7}n={r_oos['trades']}")
    return r_is, r_oos


def walk_forward(tf, strat, label=None, **kw):
    print(f"  walk-forward {label or strat} {tf}:", end=" ")
    row = []
    for w in range(N_WINDOWS):
        br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
        r = run(tf, strat, br, **kw)
        row.append(f"{r['pf']}/{r['trades']}")
    print("  |  ".join(row))


def section(title):
    print(f"\n{'='*70}\n{title}\n{'='*70}")


def main():
    section("1. Le tre 'buone confermate' (baseline 4h, nessun filtro)")
    for strat in ["MACD", "TURTLE_SOUP", "BREAKOUT_ACC"]:
        is_oos("4h", strat)
        walk_forward("4h", strat)

    section("2. Filtri di regime (BREAKOUT_ACC/LIQ_SWEEP/SAR/TSI/FVG_CONT) - stesso metodo di regime_filter_singles.py")
    for strat, want in [("BREAKOUT_ACC", "STRONG_TREND"), ("LIQ_SWEEP", "STRONG_TREND"),
                         ("SAR", "WEAK_TREND"), ("TSI", "WEAK_TREND"),
                         ("FVG_CONT", "STRONG+WEAK")]:
        candles_is, ind_is = e.load_slice(SYMBOL, "4h", BARS, (0.0, 0.6))
        candles_oos, ind_oos = e.load_slice(SYMBOL, "4h", BARS, (0.6, 1.0))
        sigs_is = e.precompute_signals(candles_is, ind_is, [strat])
        sigs_oos = e.precompute_signals(candles_oos, ind_oos, [strat])
        base_oos = e.simulate(candles_oos, ind_oos, sigs_oos, [strat], 1, regime_ok=None)
        r_want = e.simulate(candles_oos, ind_oos, sigs_oos, [strat], 1, regime_ok=REGIME[want])
        r_is_want = e.simulate(candles_is, ind_is, sigs_is, [strat], 1, regime_ok=REGIME[want])
        print(f"{strat:<12}+{want:<14}IS pf={r_is_want['pf']:<7}n={r_is_want['trades']:<6}  "
              f"OOS pf={r_want['pf']:<7}n={r_want['trades']:<6}  baseline OOS pf={base_oos['pf']} n={base_oos['trades']}")

    section("3. MALAYSIAN_SNR_V2_RETEST (1h/30m) + gate fuori-range")
    for tf in ["1h", "30m"]:
        is_oos(tf, "MALAYSIAN_SNR_V2_RETEST")
        walk_forward(tf, "MALAYSIAN_SNR_V2_RETEST")

    section("4. CRT (4h/1h/30m) - il piu' solido della sessione")
    for tf in ["4h", "1h", "30m"]:
        is_oos(tf, "CRT")
        walk_forward(tf, "CRT")

    section("5. MALAYSIAN_SNR_V2_STAGE1 / STAGE3 (baseline, mai avuto edge)")
    for strat in ["MALAYSIAN_SNR_V2_STAGE1", "MALAYSIAN_SNR_V2_STAGE3"]:
        is_oos("4h", strat)


if __name__ == "__main__":
    main()
