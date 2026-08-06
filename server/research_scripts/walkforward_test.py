#!/usr/bin/env python3
"""
06/08 - NQROS Fase 4 (Out-of-Sample), mai fatta finora: tutti i numeri
prodotti oggi (find_best_profiles.py, portfolio_test.py, grid_recovery_test.py)
sono in-sample, ottimizzati e misurati sugli STESSI dati - overfit per
costruzione, come dichiarato in ognuno di quegli script.

Per ogni strategia con edge gia' confermato: ottimizza SL/TP/BE/trailing
SOLO sul primo 60% della serie (bar_range=(0.0,0.6)), poi verifica quel
profilo (senza toccarlo) sull'ultimo 40%, mai visto durante
l'ottimizzazione (bar_range=(0.6,1.0)). Se il PF regge (o quasi) nella
finestra out-of-sample, l'edge e' probabilmente reale. Se crolla o si
inverte, il numero in-sample era rumore che sembrava un pattern.

Esegui dalla root del repo: python3 server/research_scripts/walkforward_test.py
"""
import sys
sys.path.insert(0, "server")
import backtest as bt

COSTS = bt.COST_PRESETS["retail_standard"]

CANDIDATES = {
    "OTE_CONT": "1d", "BREAKOUT_ACC": "1d", "SH_BMS_RTO": "1d", "TSI": "1d",
    "ADX_RSI": "1d", "LIQ_SWEEP": "1d", "FVG_MIT": "1d",
    "THREE_BAR_DELIVERY_BREAK": "4h", "EMA_PULLBACK": "4h", "MACD": "4h",
    "SAR": "4h", "FVG_CONT": "4h", "LIQ_VOID": "4h",
}
MIN_TRADES = 10   # piu' basso di find_best_profiles.py: la finestra IS e' gia' il 60%


def main():
    rows = []
    for strat, tf in CANDIDATES.items():
        opt = bt.optimize(symbol="XAUUSD", strategy=strat, timeframe=tf,
                          bar_range=(0.0, 0.6), sweep_management=True, **COSTS)
        cands = [r for r in opt["results"] if r["profit_factor"] is not None
                and r["trades"] >= MIN_TRADES]
        small_sample = False
        if not cands:
            cands = [r for r in opt["results"] if r["profit_factor"] is not None]
            small_sample = True
        cands.sort(key=lambda x: x["profit_factor"], reverse=True)
        best = cands[0] if cands else None
        if not best:
            rows.append({"strat": strat, "tf": tf, "err": "nessun candidato IS"})
            print(f"[{strat}] fatto (nessun candidato IS)", flush=True)
            continue
        oos = bt.run_backtest(symbol="XAUUSD", strategy=strat, timeframe=tf,
                              bar_range=(0.6, 1.0),
                              atr_sl=best["atr_sl"], atr_tp=best["atr_tp"],
                              breakeven_r=best.get("breakeven_r", 0.0),
                              trailing_atr=best.get("trailing_atr", 0.0), **COSTS)
        rows.append({
            "strat": strat, "tf": tf, "small_sample": small_sample,
            "is_pf": best["profit_factor"], "is_trades": best["trades"],
            "is_dd": best["max_dd_pct"],
            "oos_pf": oos["profit_factor"], "oos_trades": oos["trades"],
            "oos_dd": oos["max_dd_pct"], "oos_pnl": oos["net_pnl"],
            "sl": best["atr_sl"], "tp": best["atr_tp"],
            "be": best.get("breakeven_r", 0.0), "trail": best.get("trailing_atr", 0.0),
        })
        print(f"[{strat}] fatto", flush=True)

    print("\n" + "=" * 130)
    print(f"{'Strategia':<26}{'TF':>4}{'IS_PF':>7}{'IS_Tr':>6}{'IS_DD%':>8}"
          f"{'OOS_PF':>8}{'OOS_Tr':>7}{'OOS_DD%':>9}{'OOS_PnL':>10}  Esito")
    for r in rows:
        if r.get("err"):
            print(f"{r['strat']:<26}{r['tf']:>4}   {r['err']}")
            continue
        if r["oos_pf"] is None:
            esito = "OOS: 0 trade"
        elif r["oos_pf"] >= r["is_pf"] * 0.7:
            esito = "TIENE"
        elif r["oos_pf"] >= 1.0:
            esito = "si riduce ma resta >1"
        else:
            esito = "CROLLA"
        oos_pf_s = f"{r['oos_pf']:.2f}" if r["oos_pf"] is not None else "  n/a"
        note = " campione IS<10!" if r.get("small_sample") else ""
        print(f"{r['strat']:<26}{r['tf']:>4}{r['is_pf']:>7.2f}{r['is_trades']:>6}"
              f"{r['is_dd']:>8.2f}{oos_pf_s:>8}{r['oos_trades']:>7}{r['oos_dd']:>9.2f}"
              f"{r['oos_pnl']:>10.1f}  {esito}{note}")
    print("=" * 130)


if __name__ == "__main__":
    main()
