#!/usr/bin/env python3
"""
10/08 - Fase 4b: stesso raffinamento a due stadi della Fase 3
(fase3_param_refine.py: griglia SL/TP/HTF/breakeven/trailing, selezione
SOLO su in-sample, verifica su out-of-sample mai visto) applicato a
OTE_CONT e RSI_DIV - le due strategie del Gruppo A (Fase 4) con volume
di trade reale ma PF < 1 sia IS che OOS ai parametri default.

Differenza dalla Fase 3: qui si parte da un edge NEGATIVO, non positivo -
c'e' quindi piu' margine per un miglioramento genuino (la Fase 3 ha
mostrato che ottimizzare una strategia GIA' positiva (MACD/TURTLE_SOUP/
BREAKOUT_ACC) quasi sempre overfitta e peggiora l'OOS; qui la domanda e'
se esiste un angolo dello spazio dei parametri con edge vero, non se se
ne puo' spremere ancora da uno che gia' funziona).

TF proprio di ciascuna strategia (dalla Fase 4: quello col piu' alto
conteggio trade tra 15m/30m/1h), non 4h come nella Fase 3.

10/08 (2) - RI-ESEGUITO dopo il fix del bug bars/_fetch_dukascopy: la
prima esecuzione (stesso giorno) girava senza saperlo su un tetto di
~52 giorni di calendario su 30m, ~26 su 15m - non l'intero storico
Dukascopy disponibile (~3.9 anni). BARS=60000 sotto forza l'uso dello
storico pieno.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as bt
import bt_verdict

SYMBOL = "XAUUSD"
STRATS_TF = {"OTE_CONT": "15m", "RSI_DIV": "30m"}
MIN_TRADES = 8

ATR_SLS = [1.2, 1.5, 1.8, 2.2, 2.6]
ATR_TPS = [2.0, 2.8, 3.5, 4.5]
HTF_OPTS = [False, True]
BE_OPTS = [0.0, 1.0]
TRAIL_OPTS = [0.0, 2.0]

RANK = {"FORTE": 0, "OK": 1, "DEBOLE": 2, "CRITICA": 3, "POCHI_DATI": 4, "NO_SETUP": 5}


BARS = 60000  # 10/08 - vedi nota di modulo: senza questo _fetch_dukascopy
# tagliava sempre alle ultime 2500 barre (26-52 giorni su 15m/30m)
# indipendentemente dallo storico su disco - bug corretto in backtest.py,
# ma i chiamanti devono comunque chiedere esplicitamente di piu' del
# default (run_backtest(bars=800)) per usarlo davvero.


def _eval(strat, tf, sl, tp, htf, be, tr, bar_range):
    try:
        r = bt.run_backtest(
            symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
            risk_pct=1.0, atr_sl=float(sl), atr_tp=float(tp), start_equity=10000.0,
            htf_filter=bool(htf), breakeven_r=float(be), trailing_atr=float(tr),
            bar_range=bar_range, bars=BARS)
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
    return {"strategy": strat, "tf": tf, "atr_sl": float(sl), "atr_tp": float(tp),
            "htf_filter": bool(htf), "breakeven_r": float(be), "trailing_atr": float(tr),
            "trades": n, "pf": round(pf, 2), "net": round(r.get("net_pnl", 0.0), 2),
            "exp": round(exp, 3), "dd": round(dd, 2), "wr": r.get("win_rate", 0),
            "verdict": v, "why": why, "robust": robust}


def _key(c):
    return (RANK.get(c["verdict"], 9), -c["robust"])


def _best_on_is(strat, tf):
    best = None
    for sl in ATR_SLS:
        for tp in ATR_TPS:
            for htf in HTF_OPTS:
                c = _eval(strat, tf, sl, tp, htf, 0.0, 0.0, (0.0, 0.6))
                if c and (best is None or _key(c) < _key(best)):
                    best = c
    if not best:
        return None
    for be in BE_OPTS:
        for tr in TRAIL_OPTS:
            if be == 0.0 and tr == 0.0:
                continue
            c = _eval(strat, tf, best["atr_sl"], best["atr_tp"], best["htf_filter"], be, tr, (0.0, 0.6))
            if c and _key(c) < _key(best):
                best = c
    return best


def _baseline(strat, tf, bar_range):
    return _eval(strat, tf, 1.5, 3.0, False, 0.0, 0.0, bar_range)


def main():
    results = []
    for strat, tf in STRATS_TF.items():
        is_best = _best_on_is(strat, tf)
        if not is_best:
            print(f"{strat}: nessun risultato in-sample")
            continue
        oos = _eval(strat, tf, is_best["atr_sl"], is_best["atr_tp"], is_best["htf_filter"],
                     is_best["breakeven_r"], is_best["trailing_atr"], (0.6, 1.0))
        base_is = _baseline(strat, tf, (0.0, 0.6))
        base_oos = _baseline(strat, tf, (0.6, 1.0))
        results.append({"strategy": strat, "tf": tf, "params": {
            "atr_sl": is_best["atr_sl"], "atr_tp": is_best["atr_tp"],
            "htf_filter": is_best["htf_filter"], "breakeven_r": is_best["breakeven_r"],
            "trailing_atr": is_best["trailing_atr"]},
            "in_sample": is_best, "out_of_sample": oos,
            "baseline_in_sample": base_is, "baseline_out_of_sample": base_oos})

    print(f"\n{'Strategia':<10}{'TF':>5}{'SL':>5}{'TP':>5}{'HTF':>6}{'BE':>5}{'Trail':>6}"
          f"{'IS PF':>7}{'IS n':>6}{'IS V':>8}   {'OOS PF':>7}{'OOS n':>6}{'OOS V':>8}"
          f"   {'Base IS PF':>11}{'Base OOS PF':>12}")
    for r in results:
        p, i, o, bi, bo = r["params"], r["in_sample"], r["out_of_sample"], r["baseline_in_sample"], r["baseline_out_of_sample"]
        print(f"{r['strategy']:<10}{r['tf']:>5}{p['atr_sl']:>5}{p['atr_tp']:>5}{str(p['htf_filter']):>6}"
              f"{p['breakeven_r']:>5}{p['trailing_atr']:>6}"
              f"{i['pf']:>7}{i['trades']:>6}{i['verdict']:>8}   "
              f"{(o['pf'] if o else '-'):>7}{(o['trades'] if o else '-'):>6}{(o['verdict'] if o else '-'):>8}"
              f"   {(bi['pf'] if bi else '-'):>11}{(bo['pf'] if bo else '-'):>12}")

    import json
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phase4b_param_refine_groupA_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSalvato: {out_path}")


if __name__ == "__main__":
    main()
