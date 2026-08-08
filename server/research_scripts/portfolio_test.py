#!/usr/bin/env python3
"""
06/08 - test di combinazione: le strategie con edge positivo confermato
(PF>1.0, >=15 trade, nessun flag campione<15! nel giro find_best_profiles.py
del 06/08 post-fix) fatte girare insieme, ognuna col proprio profilo
SL/TP/BE/trailing trovato in quel giro (strategy_profiles per-strategia,
non piu' un unico SL/TP globale per tutte).

Limite del motore (dichiarato, non nuovo): un run lavora su una sola serie
di candele -> TF diversi non possono girare in un unico run, quindi il
test resta separato per gruppo D1/H4/H1 come nel report precedente.
Escluse: SMS_BMS_RTO (0 trade, sospetto difetto strutturale gia' segnalato,
condiviso con l'MQL5 reale) e tutte le strategie con PF<=1.0 o campione<15.

Esegui dalla root del repo: python3 server/research_scripts/portfolio_test.py
"""
import sys
sys.path.insert(0, "server")
import backtest as bt

COSTS = bt.COST_PRESETS["retail_standard"]

# strat_id -> (tf, atr_sl, atr_tp, breakeven_r, trailing_atr) dal giro
# find_best_profiles.py del 06/08 (post-fix soglia Dukascopy + TF_MAP),
# solo PF>1.0 e trades>=15 senza flag campione piccolo.
GROUPS = {
    "1d": {
        "OTE_CONT":     (1.0, 4.0, 1.0, 2.5),
        "BREAKOUT_ACC": (2.0, 4.0, 1.5, 2.5),
        "SH_BMS_RTO":   (1.0, 2.0, 1.0, 2.5),
        "TSI":          (1.0, 4.0, 0.0, 2.5),
        "ADX_RSI":      (2.0, 4.0, 0.0, 2.5),
        "LIQ_SWEEP":    (1.5, 2.0, 0.0, 0.0),
        "FVG_MIT":      (1.0, 2.0, 0.0, 0.0),
    },
    "4h": {
        "THREE_BAR_DELIVERY_BREAK": (1.5, 3.0, 0.0, 0.0),
        "EMA_PULLBACK":             (1.0, 4.0, 0.0, 0.0),
        "MACD":                     (1.0, 4.0, 0.0, 0.0),
        "SAR":                      (2.0, 4.0, 0.0, 0.0),
        "FVG_CONT":                 (1.0, 4.0, 0.0, 0.0),
        "LIQ_VOID":                 (1.5, 3.0, 0.0, 0.0),
    },
}


def main():
    for tf, strats in GROUPS.items():
        strategy_profiles = {
            sid: {"atr_sl": sl, "atr_tp": tp, "breakeven_r": be, "trailing_atr": tr}
            for sid, (sl, tp, be, tr) in strats.items()
        }
        r = bt.run_backtest(symbol="XAUUSD", timeframe=tf, strategies=list(strats),
                            strategy_profiles=strategy_profiles, **COSTS)
        print(f"\n=== gruppo {tf}: {len(strats)} strategie insieme ===")
        print(f"  trade={r['trades']}  WR={r['win_rate']:.1f}%  PF={r['profit_factor']:.2f}  "
              f"ExpR={r['expectancy_r']:.3f}  MaxDD={r['max_dd_pct']:.2f}%  "
              f"NetPnL={r['net_pnl']:.2f}")
        by_strat = {}
        for t in r["trade_list"]:
            by_strat.setdefault(t.get("strategy", "?"), []).append(t)
        print("  contributo per strategia (trade attivati nel gruppo):")
        for sid, tlist in sorted(by_strat.items(), key=lambda x: -len(x[1])):
            wins = sum(1 for t in tlist if t["pnl"] >= 0)
            print(f"    {sid:<26} {len(tlist):>4} trade  WR={100*wins/len(tlist):5.1f}%")


if __name__ == "__main__":
    main()
