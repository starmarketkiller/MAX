#!/usr/bin/env python3
"""
NQROS Fase 1 (baseline) applicata a TUTTE le strategie del motore Python
(non solo il sottoinsieme con TF nativo fisso da profilo MQL5) su TUTTI i
timeframe disponibili (M5/M15/M30/H1/H4/D1/W1) - "Testare M5, M15, M30, H1,
H4, D1, W1... Eliminare i timeframe deboli" (manuale NQROS v1.0).

Profilo di default (atr_sl=1.5, atr_tp=3.0, no breakeven/trailing) - questa
e' la BASELINE, non un'ottimizzazione (quella e' Fase 3, va fatta solo sui
TF che sopravvivono qui). Costi realistici (retail_standard).

Esegui dalla root del repo: python3 server/research_scripts/multi_tf_baseline.py
"""
import sys
import time
sys.path.insert(0, "server")
import backtest as bt

TIMEFRAMES = ["1wk", "1d", "4h", "1h", "30m", "15m", "5m"]
MIN_TRADES = 15
COSTS = bt.COST_PRESETS["retail_standard"]

STRATS = sorted(bt.STRATEGIES.keys())


def main():
    results = {}   # strat -> {tf: row}
    t0 = time.time()
    n_total = len(STRATS) * len(TIMEFRAMES)
    done = 0
    for strat in STRATS:
        results[strat] = {}
        for tf in TIMEFRAMES:
            done += 1
            try:
                r = bt.run_backtest(symbol="XAUUSD", strategy=strat, timeframe=tf, **COSTS)
                results[strat][tf] = {
                    "trades": r["trades"], "pf": r["profit_factor"], "wr": r["win_rate"],
                    "exp": r["expectancy_r"], "dd": r["max_dd_pct"], "net": r["net_pnl"],
                    "sharpe": r["sharpe"], "err": None,
                }
            except Exception as e:
                results[strat][tf] = {"err": str(e)[:80]}
            if done % 40 == 0:
                print(f"[{done}/{n_total}] ({time.time() - t0:.1f}s)", flush=True)

    print(f"\nCompletato in {time.time() - t0:.1f}s\n")

    # --- Vista 1: miglior TF per strategia (tra quelli con trades>=MIN_TRADES) ---
    best_rows = []
    for strat in STRATS:
        cands = [(tf, row) for tf, row in results[strat].items()
                 if not row.get("err") and row["pf"] is not None and row["trades"] >= MIN_TRADES]
        small = False
        if not cands:
            cands = [(tf, row) for tf, row in results[strat].items()
                      if not row.get("err") and row["pf"] is not None]
            small = True
        if not cands:
            best_rows.append((strat, None, None, True))
            continue
        cands.sort(key=lambda x: x[1]["pf"], reverse=True)
        best_tf, best_row = cands[0]
        best_rows.append((strat, best_tf, best_row, small))

    best_rows.sort(key=lambda x: (x[2]["pf"] if x[2] else -999), reverse=True)
    print("=" * 110)
    print("MIGLIOR TF PER STRATEGIA (tra i TF con >=15 trade, altrimenti il migliore disponibile)")
    print("=" * 110)
    print(f"{'Strategia':<26}{'TF':>5}{'PF':>7}{'Trades':>8}{'WR%':>6}{'ExpR':>7}{'MaxDD%':>8}  Note")
    for strat, tf, row, small in best_rows:
        if row is None:
            print(f"{strat:<26}  nessun dato disponibile su nessun TF")
            continue
        note = "campione<15 su TUTTI i TF!" if small else ""
        print(f"{strat:<26}{tf:>5}{row['pf']:>7.2f}{row['trades']:>8}{row['wr']:>6.1f}"
              f"{row['exp']:>7.3f}{row['dd']:>8.2f}  {note}")

    # --- Vista 2: matrice PF completa (strategia x TF) ---
    print("\n" + "=" * 110)
    print("MATRICE PROFIT FACTOR (strategia x timeframe) - 'x' = errore/non disponibile, '.' = <15 trade")
    print("=" * 110)
    hdr = f"{'Strategia':<26}" + "".join(f"{tf:>8}" for tf in TIMEFRAMES)
    print(hdr)
    for strat in STRATS:
        cells = []
        for tf in TIMEFRAMES:
            row = results[strat][tf]
            if row.get("err"):
                cells.append("x".rjust(8))
            elif row["pf"] is None:
                cells.append("-".rjust(8))
            else:
                mark = "" if row["trades"] >= MIN_TRADES else "."
                cells.append(f"{row['pf']:.2f}{mark}".rjust(8))
        print(f"{strat:<26}" + "".join(cells))
    print("=" * 110)

    # --- CSV completo per analisi ulteriore ---
    import csv
    out_csv = "docs/testing/multi_tf_baseline_full.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["strategy", "tf", "trades", "pf", "wr", "exp_r", "max_dd_pct", "net_pnl", "sharpe", "err"])
        for strat in STRATS:
            for tf in TIMEFRAMES:
                row = results[strat][tf]
                if row.get("err"):
                    w.writerow([strat, tf, "", "", "", "", "", "", "", row["err"]])
                else:
                    w.writerow([strat, tf, row["trades"], row["pf"], row["wr"], row["exp"],
                                row["dd"], row["net"], row["sharpe"], ""])
    print(f"\nCSV completo salvato in {out_csv}")


if __name__ == "__main__":
    main()
