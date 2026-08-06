#!/usr/bin/env python3
"""
06/08 - le 7 strategie a sessione fissa (AMD_CONT, AMD_REVERSAL, JUDAS_SWING,
LDN_REVERSAL, NY_REVERSAL, PO3, SILVER_BULLET) sono gia' state riscritte con
fedelta' verificata contro l'MQL5 in questa sessione (vedi i commenti "04/08"
in ognuna delle sig_* in backtest.py) ma find_best_profiles.py non le ha mai
testate: sono legate a `ind["sess"]["session"]`/`amd_phase` (derivati
dall'ora della barra), un concetto che non esiste su barre giornaliere - lo
stesso motivo per cui LONDON_BO/WEEKLY_EXP davano 0 trade prima di essere
spostate su TF intraday. Qui si testano su 1h, dove il rilevamento sessione
ha senso (stesso TF gia' usato per STRUCT_REACT/TURTLE_SOUP/RSI_DIV/LONDON_BO
in find_best_profiles.py).

ELLIOTT esclusa: research_implementation=False nel registro, nessuna
implementazione nel motore Python - non e' un TF sbagliato, e' un porting
mai fatto. Richiederebbe scrivere da zero una logica Elliott Wave, un
lavoro separato, non incluso qui.

Esegui dalla root del repo: python3 server/research_scripts/session_strategies_test.py
"""
import sys
sys.path.insert(0, "server")
import backtest as bt

COSTS = bt.COST_PRESETS["retail_standard"]
STRATS = ["AMD_CONT", "AMD_REVERSAL", "JUDAS_SWING", "LDN_REVERSAL",
         "NY_REVERSAL", "PO3", "SILVER_BULLET"]
TF = "1h"
MIN_TRADES = 15


def main():
    results = []
    for strat in STRATS:
        try:
            base = bt.run_backtest(symbol="XAUUSD", strategy=strat, timeframe=TF, **COSTS)
            opt = bt.optimize(symbol="XAUUSD", strategy=strat, timeframe=TF,
                              sweep_management=True, **COSTS)
            cands = [r for r in opt["results"] if r["profit_factor"] is not None and r["trades"] >= MIN_TRADES]
            small_sample = False
            if not cands:
                cands = [r for r in opt["results"] if r["profit_factor"] is not None]
                small_sample = True
            cands.sort(key=lambda x: x["profit_factor"], reverse=True)
            best = cands[0] if cands else None
            if best:
                full = bt.run_backtest(symbol="XAUUSD", strategy=strat, timeframe=TF,
                                       atr_sl=best["atr_sl"], atr_tp=best["atr_tp"],
                                       breakeven_r=best.get("breakeven_r", 0.0),
                                       trailing_atr=best.get("trailing_atr", 0.0), **COSTS)
                results.append({
                    "strat": strat, "base_pf": base["profit_factor"], "base_trades": base["trades"],
                    "opt_pf": full["profit_factor"], "opt_trades": full["trades"],
                    "opt_wr": full["win_rate"], "opt_dd": full["max_dd_pct"],
                    "sl": best["atr_sl"], "tp": best["atr_tp"],
                    "be": best.get("breakeven_r", 0.0), "trail": best.get("trailing_atr", 0.0),
                    "small_sample": small_sample, "err": None,
                })
            else:
                results.append({"strat": strat, "err": "nessun candidato valido"})
        except Exception as e:
            results.append({"strat": strat, "err": str(e)[:150]})
        print(f"[{strat}] fatto", flush=True)

    print("\n" + "=" * 110)
    print(f"{'Strategia':<18}{'BasePF':>8}{'OptPF':>8}{'Trades':>8}{'WR%':>6}{'MaxDD%':>8}"
          f"{'SL':>5}{'TP':>5}{'BE':>5}{'Trail':>6}  Note")
    for r in results:
        if r.get("err"):
            print(f"{r['strat']:<18}   ERRORE: {r['err']}")
            continue
        note = "campione<15!" if r["small_sample"] else ""
        print(f"{r['strat']:<18}{(r['base_pf'] or 0):>8.2f}{(r['opt_pf'] or 0):>8.2f}"
              f"{r['opt_trades']:>8}{r['opt_wr']:>6.1f}{r['opt_dd']:>8.2f}"
              f"{r['sl']:>5.1f}{r['tp']:>5.1f}{r['be']:>5.1f}{r['trail']:>6.1f}  {note}")
    print("=" * 110)


if __name__ == "__main__":
    main()
