#!/usr/bin/env python3
"""
06/08 - "testa qualsiasi cosa puo' migliorare": per ogni strategia con edge
gia' confermato, sweep di max_per_dir (1..4, il tetto reale e' InpMaxPerDirTF
default=4) al profilo SL/TP/BE/trailing gia' trovato - trova il livello che
massimizza il PF per unita' di drawdown, invece di usare 4 per tutte senza
distinzione (il 06/08 ha gia' mostrato che per SAR/ADX_RSI il cap a 4 aggiunge
solo rischio senza beneficio, mentre per MACD/FVG_CONT aiuta davvero).

Per MACD e FVG_CONT (le due che beneficiano di piu' posizioni) testa anche
grid_max_legs=3 sopra il miglior max_per_dir, per vedere se i due meccanismi
si sommano o si ostacolano.

Punteggio: PF diviso per MaxDD% (approssimazione grezza di rendimento
aggiustato per rischio - non uno Sharpe vero, ma sufficiente per un
confronto relativo fra livelli dello stesso max_per_dir).

Esegui dalla root del repo: python3 server/research_scripts/optimize_max_per_dir.py
"""
import sys
sys.path.insert(0, "server")
import backtest as bt

COSTS = bt.COST_PRESETS["retail_standard"]

# strat -> (tf, sl, tp, be, trail) dal profilo migliore gia' trovato
CONFIGS = {
    "MACD":          ("4h", 1.0, 4.0, 0.0, 0.0),
    "SAR":           ("4h", 2.0, 4.0, 0.0, 0.0),
    "ADX_RSI":       ("1d", 2.0, 4.0, 0.0, 0.0),
    "FVG_CONT":      ("4h", 1.0, 4.0, 0.0, 0.0),
    "LIQ_VOID":      ("4h", 1.5, 3.0, 0.0, 0.0),
    "LONDON_BO":     ("1h", 2.0, 4.0, 0.0, 0.0),
    "SH_BMS_RTO":    ("1d", 1.0, 2.0, 1.0, 2.5),
}
GRID_CANDIDATES = ("MACD", "FVG_CONT")


def score(pf, dd):
    if pf is None or dd is None or dd <= 0:
        return -999
    return pf / dd


def main():
    for strat, (tf, sl, tp, be, trail) in CONFIGS.items():
        kw = dict(symbol="XAUUSD", strategy=strat, timeframe=tf,
                  atr_sl=sl, atr_tp=tp, breakeven_r=be, trailing_atr=trail, **COSTS)
        rows = []
        for mpd in (None, 1, 2, 3, 4):
            r = bt.run_backtest(max_per_dir=mpd, **kw)
            rows.append(("base", mpd, r["profit_factor"], r["max_dd_pct"],
                        r["trades"], r["net_pnl"], score(r["profit_factor"], r["max_dd_pct"])))
        if strat in GRID_CANDIDATES:
            best_base_mpd = max((r for r in rows if r[0] == "base"), key=lambda r: r[6])[1]
            r = bt.run_backtest(max_per_dir=best_base_mpd, grid_max_legs=3,
                                grid_step_atr=1.2, grid_regime_filter=True, **kw)
            rows.append(("+grid", best_base_mpd, r["profit_factor"], r["max_dd_pct"],
                        r["trades"], r["net_pnl"], score(r["profit_factor"], r["max_dd_pct"])))
        print(f"\n=== {strat} ({tf}, SL={sl} TP={tp} BE={be} Trail={trail}) ===")
        for tag, mpd, pf, dd, tr, pnl, sc in rows:
            mpd_s = "singola(default)" if mpd is None else f"max_per_dir={mpd}"
            pf_s = f"{pf:.2f}" if pf is not None else " n/a"
            print(f"  {tag:<6} {mpd_s:<20} trades={tr:>4}  PF={pf_s}  MaxDD={dd:>5.1f}%  "
                  f"NetPnL={pnl:>9.1f}  score(PF/DD)={sc:.3f}")
        best = max(rows, key=lambda r: r[6])
        print(f"  -> MIGLIORE: {best[0]} {('singola' if best[1] is None else f'max_per_dir={best[1]}')} "
              f"(score={best[6]:.3f})", flush=True)


if __name__ == "__main__":
    main()
