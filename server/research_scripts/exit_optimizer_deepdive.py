#!/usr/bin/env python3
"""
12/08 - approfondimento quantitativo di TUTTI i candidati sopravvissuti al
filtro IS di exit_optimizer_grid.py (non solo il vincitore per PF o i 3
scelti a mano per il trade-off PF/DD). Per ognuno: metriche OOS complete
(pf/n/win_rate/dd/expectancy_r/sharpe/net_pnl, gia' calcolate da
run_backtest, prima non stampate) + walk-forward completo a 5 finestre
(prima calcolato solo per 1-2 candidati per strategia).

Punteggio di robustezza (trasparente, riproducibile, non un giudizio
qualitativo): robustness = media(pf walk-forward) - stdev(pf walk-forward).
Premia un edge medio alto E penalizza l'incoerenza tra finestre - lo stesso
principio dello Sharpe ratio applicato al PF invece che ai ritorni, scelto
perche' e' esattamente il tipo di instabilita' (una finestra ottima e una
pessima) che ha gia' fatto scartare risultati "belli in media" altrove in
sessione (regime filter, filtri di regime falliti nonostante PF aggregati
alti). Non sostituisce il giudizio finale, ma rende il confronto tra
candidati un numero solo invece di una lettura riga per riga.
"""
import sys
import os
import statistics

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

BARS = 110000
IS_RANGE, OOS_RANGE = (0.0, 0.6), (0.6, 1.0)
N_WINDOWS = 5
MIN_IS_PF = 1.10
MIN_IS_TRADES = 50


def call(symbol, timeframe, strategy, bar_range, sl, tp, be, trail):
    return bt.run_backtest(symbol=symbol, timeframe=timeframe, strategy=strategy,
                            strategies=[strategy], risk_pct=1.0, bars=BARS,
                            bar_range=bar_range, atr_sl=sl, atr_tp=tp,
                            breakeven_r=be, trailing_atr=trail)


def full_metrics(symbol, tf, strat, sl, tp, be, trail):
    oos = call(symbol, tf, strat, OOS_RANGE, sl, tp, be, trail)
    wf = []
    for w in range(N_WINDOWS):
        br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
        r = call(symbol, tf, strat, br, sl, tp, be, trail)
        wf.append(r.get("profit_factor") or 0.0)
    wf_mean = statistics.mean(wf)
    wf_std = statistics.pstdev(wf)
    robustness = round(wf_mean - wf_std, 3)
    return {
        "sl": sl, "tp": tp, "be": be, "trail": trail,
        "oos_pf": oos.get("profit_factor"), "oos_n": oos.get("trades"),
        "oos_wr": oos.get("win_rate"), "oos_dd": oos.get("max_dd_pct"),
        "oos_exp_r": oos.get("expectancy_r"), "oos_sharpe": oos.get("sharpe"),
        "oos_net": oos.get("net_pnl"),
        "wf": [round(x, 2) for x in wf], "wf_mean": round(wf_mean, 3),
        "wf_std": round(wf_std, 3), "wf_min": round(min(wf), 2),
        "wf_above1": sum(1 for x in wf if x >= 1.0),
        "robustness": robustness,
    }


def print_row(r):
    print(f"  sl={r['sl']} tp={r['tp']} be={r['be']} trail={r['trail']} | "
          f"OOS pf={r['oos_pf']} n={r['oos_n']} wr={r['oos_wr']}% dd={r['oos_dd']}% "
          f"exp_r={r['oos_exp_r']} sharpe={r['oos_sharpe']} net={r['oos_net']} | "
          f"WF={r['wf']} mean={r['wf_mean']} std={r['wf_std']} min={r['wf_min']} "
          f"({r['wf_above1']}/5 >=1.0) | ROBUSTEZZA={r['robustness']}", flush=True)


def main():
    print("NEXUS - OPTIMIZATION DESK: approfondimento quantitativo completo\n", flush=True)

    # ---------------- CRT (30m) - tutti i 6 combinazioni be x trail ----------------
    print("=" * 90 + "\nCRT @ 30m (sl/tp fissi e inerti 1.5/3.0 - solo be x trail)\n" + "=" * 90, flush=True)
    crt_rows = []
    for be in (0.0, 1.0, 1.5):
        for trail in (0.0, 1.0):
            r = full_metrics("XAUUSD", "30m", "CRT", 1.5, 3.0, be, trail)
            crt_rows.append(r)
            print_row(r)
    crt_rows.sort(key=lambda x: x["robustness"], reverse=True)
    print("\n-- ranking per robustezza (media WF - stdev WF):", flush=True)
    for r in crt_rows:
        print(f"   be={r['be']} trail={r['trail']} -> robustezza={r['robustness']} "
              f"(oos pf={r['oos_pf']} dd={r['oos_dd']}%)", flush=True)

    # ---------------- FVG_CONT (4h) - tutti i 12 candidati sopravvissuti al filtro IS ----------------
    print("\n" + "=" * 90 + "\nFVG_CONT @ 4h - tutti i candidati che superano il filtro IS (pf>1.10, n>50)\n" + "=" * 90, flush=True)
    fvg_candidates = [
        (1.0, 2.0, 0.0, 0.0), (1.0, 3.0, 0.0, 0.0), (1.0, 4.0, 0.0, 0.0), (1.0, 4.0, 1.5, 0.0),
        (1.5, 3.0, 0.0, 0.0), (1.5, 4.0, 0.0, 0.0), (1.5, 4.0, 1.5, 0.0),
        (2.0, 2.0, 0.0, 0.0), (2.0, 3.0, 0.0, 0.0), (2.0, 4.0, 0.0, 0.0), (2.0, 4.0, 1.0, 0.0), (2.0, 4.0, 1.5, 0.0),
    ]
    fvg_rows = []
    for sl, tp, be, trail in fvg_candidates:
        r = full_metrics("XAUUSD", "4h", "FVG_CONT", sl, tp, be, trail)
        fvg_rows.append(r)
        print_row(r)
    fvg_rows.sort(key=lambda x: x["robustness"], reverse=True)
    print("\n-- ranking per robustezza (media WF - stdev WF):", flush=True)
    for r in fvg_rows:
        print(f"   sl={r['sl']} tp={r['tp']} be={r['be']} -> robustezza={r['robustness']} "
              f"(oos pf={r['oos_pf']} dd={r['oos_dd']}%)", flush=True)


if __name__ == "__main__":
    main()
