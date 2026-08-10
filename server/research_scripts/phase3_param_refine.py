#!/usr/bin/env python3
"""
10/08 - Fase 3 della pipeline: raffinamento parametri (SL/TP/HTF/breakeven/
trailing) per i 4 sopravvissuti della Fase 2 (auto_combo_search.py: nessuna
combinazione batte i singoli) - FVG_CONT, MACD, TURTLE_SOUP, BREAKOUT_ACC.

Stessa griglia e stessa logica a due stadi di /api/backtest/optimize_per_strategy
(server/app.py) ma con una differenza deliberata: quell'endpoint ottimizza SEMPRE
sull'intero periodo disponibile, senza split - esattamente il tipo di numero
"in-sample gonfiato" scartato piu' volte in questa sessione (LONDON_BO PF 4.08,
TURTLE_SOUP PF 6.38 su 1d, il primo majority-vote PF 1.85). Qui la selezione dei
parametri migliori avviene SOLO sul 60% in-sample (bar_range 0.0-0.6), e la
metrica che conta e' quella dello stesso identico config valutato sul 40%
out-of-sample (0.6-1.0) mai visto durante la scelta.

TF=4h per tutte e 4: dal full_strategy_tf_scan.py di ieri e' il timeframe con
miglior compromesso PF/campione per tutte e 4 (51-76 trade, PF 1.51-2.31),
a differenza di 1d (campione troppo piccolo, es. TURTLE_SOUP 17 trade).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as bt
import bt_verdict

SYMBOL = "XAUUSD"
TF = "4h"
STRATS = ["FVG_CONT", "MACD", "TURTLE_SOUP", "BREAKOUT_ACC"]
MIN_TRADES = 8

ATR_SLS = [1.2, 1.5, 1.8, 2.2, 2.6]
ATR_TPS = [2.0, 2.8, 3.5, 4.5]
HTF_OPTS = [False, True]
BE_OPTS = [0.0, 1.0]
TRAIL_OPTS = [0.0, 2.0]

RANK = {"FORTE": 0, "OK": 1, "DEBOLE": 2, "CRITICA": 3, "POCHI_DATI": 4, "NO_SETUP": 5}


def _eval(strat, sl, tp, htf, be, tr, bar_range):
    try:
        r = bt.run_backtest(
            symbol=SYMBOL, timeframe=TF, strategy=strat, strategies=[strat],
            risk_pct=1.0, atr_sl=float(sl), atr_tp=float(tp), start_equity=10000.0,
            htf_filter=bool(htf), breakeven_r=float(be), trailing_atr=float(tr),
            bar_range=bar_range)
    except Exception:
        return None
    n = r.get("trades", 0)
    pf = r.get("profit_factor") or 0.0
    exp = r.get("expectancy_r", 0.0)
    dd = r.get("max_dd_pct", 0.0)
    v, why = bt_verdict._verdict(
        {"executed": n, "profit_factor": pf, "expectancy_R": exp,
         "winrate_pct": r.get("win_rate", 0), "setup": n}, MIN_TRADES)
    robust = round(exp * (n ** 0.5) / (1.0 + max(0.0, dd) / 10.0), 3)
    return {"strategy": strat, "atr_sl": float(sl), "atr_tp": float(tp),
            "htf_filter": bool(htf), "breakeven_r": float(be), "trailing_atr": float(tr),
            "trades": n, "pf": round(pf, 2), "net": round(r.get("net_pnl", 0.0), 2),
            "exp": round(exp, 3), "dd": round(dd, 2), "wr": r.get("win_rate", 0),
            "verdict": v, "why": why, "robust": robust}


def _key(c):
    return (RANK.get(c["verdict"], 9), -c["robust"])


def _best_on_is(strat):
    best = None
    for sl in ATR_SLS:
        for tp in ATR_TPS:
            for htf in HTF_OPTS:
                c = _eval(strat, sl, tp, htf, 0.0, 0.0, (0.0, 0.6))
                if c and (best is None or _key(c) < _key(best)):
                    best = c
    if not best:
        return None
    for be in BE_OPTS:
        for tr in TRAIL_OPTS:
            if be == 0.0 and tr == 0.0:
                continue
            c = _eval(strat, best["atr_sl"], best["atr_tp"], best["htf_filter"], be, tr, (0.0, 0.6))
            if c and _key(c) < _key(best):
                best = c
    return best


def _baseline(strat, bar_range):
    """Default NON ottimizzato (1.5/3.0, nessun gate) - il termine di paragone
    per capire se il grid-search ha trovato un vero miglioramento o solo
    overfit sull'in-sample (vedi lezione vault 'overfitting 3M->3Y', v2.4.8:
    PF 1.24/DD 29.6% -> PF 0.85/DD 87% dopo tuning troppo stretto)."""
    return _eval(strat, 1.5, 3.0, False, 0.0, 0.0, bar_range)


def main():
    results = []
    for strat in STRATS:
        is_best = _best_on_is(strat)
        if not is_best:
            print(f"{strat}: nessun risultato in-sample (dati insufficienti)")
            continue
        oos = _eval(strat, is_best["atr_sl"], is_best["atr_tp"], is_best["htf_filter"],
                     is_best["breakeven_r"], is_best["trailing_atr"], (0.6, 1.0))
        base_oos = _baseline(strat, (0.6, 1.0))
        results.append({"strategy": strat, "params": {
            "atr_sl": is_best["atr_sl"], "atr_tp": is_best["atr_tp"],
            "htf_filter": is_best["htf_filter"], "breakeven_r": is_best["breakeven_r"],
            "trailing_atr": is_best["trailing_atr"]},
            "in_sample": is_best, "out_of_sample": oos, "baseline_out_of_sample": base_oos,
            "optimization_helped": bool(oos and base_oos and (oos["pf"] or 0) > (base_oos["pf"] or 0))})

    print(f"\n{'Strategia':<14}{'SL':>5}{'TP':>5}{'HTF':>6}{'BE':>5}{'Trail':>6}"
          f"{'IS PF':>7}{'IS n':>6}{'IS V':>8}   {'OOS PF':>7}{'OOS n':>6}{'OOS V':>8}"
          f"   {'Base OOS PF':>12}{'Aiuta?':>8}")
    for r in results:
        p, i, o, b = r["params"], r["in_sample"], r["out_of_sample"], r["baseline_out_of_sample"]
        print(f"{r['strategy']:<14}{p['atr_sl']:>5}{p['atr_tp']:>5}{str(p['htf_filter']):>6}"
              f"{p['breakeven_r']:>5}{p['trailing_atr']:>6}"
              f"{i['pf']:>7}{i['trades']:>6}{i['verdict']:>8}   "
              f"{(o['pf'] if o else '-'):>7}{(o['trades'] if o else '-'):>6}{(o['verdict'] if o else '-'):>8}"
              f"   {(b['pf'] if b else '-'):>12}{str(r['optimization_helped']):>8}")

    import json
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phase3_param_refine_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSalvato: {out_path}")


if __name__ == "__main__":
    main()
