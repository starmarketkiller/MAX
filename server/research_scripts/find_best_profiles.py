#!/usr/bin/env python3
"""
NQROS Fase 3 (ottimizzazione) applicata in batch a tutte le strategie attive
con timeframe nativo noto (TF_MAP, dai profili MQL5 raccolti durante il
porting Pine di questa sessione). Per ognuna: baseline a parametri di
default, poi griglia SL/TP + breakeven/trailing (optimize(sweep_management=
True)), best selezionato per Profit Factor tra i candidati con >=MIN_TRADES
trade (sotto quella soglia il campione e' troppo piccolo per fidarsi del PF -
vedi nota "campione<15!" in output).

Esegui dalla root del repo: python3 server/research_scripts/find_best_profiles.py

NB: questo e' il motore di ricerca Python (dati Yahoo, non MT5 reale) - serve
a fare triage rapido tra 29 strategie, non sostituisce un test MT5/
TradingView vero. Nessuna validazione Out-of-Sample qui (NQROS Fase 4),
quindi i numeri "opt" sono ottimistici per costruzione (overfit in-sample).
"""
import sys
import time
sys.path.insert(0, "server")
import backtest as bt

TF_MAP = {
    "ADX_RSI": "1d", "TSI": "1d", "LIQ_SWEEP": "1d", "SH_BMS_RTO": "1d",
    "SMS_BMS_RTO": "1d", "FVG_MIT": "1d", "OB_MIT": "1d", "ORDER_BLOCK": "1d",
    "OTE_CONT": "1d", "BREAKOUT_ACC": "1d", "LONDON_BO": "1d", "BOLLINGER": "1d",
    "BB_SQUEEZE": "1d", "RANGE_FADE": "1d", "WEEKLY_EXP": "1d", "MALAYSIAN_SNR": "1d",
    "MACD": "4h", "SAR": "4h", "BJORGUM": "4h", "THREE_BAR_DELIVERY_BREAK": "4h",
    "FVG_CONT": "4h", "IFVG": "4h", "EMA_PULLBACK": "4h", "ICHIMOKU": "4h",
    "LIQ_VOID": "4h", "DISP_REBAL": "4h",
    "STRUCT_REACT": "1h", "TURTLE_SOUP": "1h", "RSI_DIV": "1h",
}
# Escluse deliberatamente (stesso motivo del porting Pine): sessione
# intraday/range Asia senza TF fisso D1/H4/H1 pulito (AMD_CONT/AMD_REVERSAL/
# JUDAS_SWING/LDN_REVERSAL/NY_REVERSAL/PO3/SILVER_BULLET) e SCALP_* (nessun
# profilo MQL5, solo motore Python).
MIN_TRADES = 15
COSTS = bt.COST_PRESETS["retail_standard"]


def main():
    results = []
    t0 = time.time()
    for idx, (strat, tf) in enumerate(sorted(TF_MAP.items()), 1):
        try:
            base = bt.run_backtest(symbol="XAUUSD", strategy=strat, timeframe=tf, **COSTS)
            opt = bt.optimize(symbol="XAUUSD", strategy=strat, timeframe=tf,
                               sweep_management=True, **COSTS)
            cands = [r for r in opt["results"] if r["profit_factor"] is not None and r["trades"] >= MIN_TRADES]
            small_sample = False
            if not cands:
                cands = [r for r in opt["results"] if r["profit_factor"] is not None]
                small_sample = True
            cands.sort(key=lambda x: x["profit_factor"], reverse=True)
            best = cands[0] if cands else None
            if best:
                full = bt.run_backtest(symbol="XAUUSD", strategy=strat, timeframe=tf,
                                        atr_sl=best["atr_sl"], atr_tp=best["atr_tp"],
                                        breakeven_r=best.get("breakeven_r", 0.0),
                                        trailing_atr=best.get("trailing_atr", 0.0), **COSTS)
                results.append({
                    "strat": strat, "tf": tf,
                    "base_pf": base["profit_factor"], "base_trades": base["trades"],
                    "opt_pf": full["profit_factor"], "opt_trades": full["trades"],
                    "opt_wr": full["win_rate"], "opt_exp": full["expectancy_r"],
                    "opt_dd": full["max_dd_pct"],
                    "sl": best["atr_sl"], "tp": best["atr_tp"],
                    "be": best.get("breakeven_r", 0.0), "trail": best.get("trailing_atr", 0.0),
                    "small_sample": small_sample, "err": None,
                })
            else:
                results.append({"strat": strat, "tf": tf, "err": "nessun candidato valido"})
        except Exception as e:
            results.append({"strat": strat, "tf": tf, "err": str(e)[:100]})
        print(f"[{idx}/{len(TF_MAP)}] {strat} fatto ({time.time() - t0:.1f}s)", flush=True)

    results.sort(key=lambda r: (r.get("opt_pf") if r.get("opt_pf") is not None else -999), reverse=True)
    print("\n" + "=" * 118)
    print(f"{'Strategia':<26}{'TF':>4}{'BasePF':>8}{'OptPF':>8}{'Trades':>8}"
          f"{'WR%':>6}{'ExpR':>7}{'MaxDD%':>8}{'SL':>5}{'TP':>5}{'BE':>5}{'Trail':>6}  Note")
    for r in results:
        if r.get("err"):
            print(f"{r['strat']:<26}{r['tf']:>4}   ERRORE: {r['err']}")
            continue
        note = "campione<15!" if r["small_sample"] else ""
        print(f"{r['strat']:<26}{r['tf']:>4}{(r['base_pf'] or 0):>8.2f}{(r['opt_pf'] or 0):>8.2f}"
              f"{r['opt_trades']:>8}{r['opt_wr']:>6.1f}{r['opt_exp']:>7.3f}{r['opt_dd']:>8.2f}"
              f"{r['sl']:>5.1f}{r['tp']:>5.1f}{r['be']:>5.1f}{r['trail']:>6.1f}  {note}")
    print("=" * 118)
    print(f"Tempo totale: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
