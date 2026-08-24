#!/usr/bin/env python3
"""
24/08 (16) - analisi di correlazione vera tra le 20 strategie, richiesta
dopo che il portafoglio a 20 (portfolio_expanded_24-08.py) ha mostrato
drawdown esplosivo con piu' posizioni concorrenti - segno che molte
strategie non sono indipendenti.

Metodo: bucket giornaliero di R netto per strategia (somma dei net_r di
tutti i trade con quella data di apertura, indipendentemente
dall'esecuzione nel portafoglio - qui misuriamo la correlazione del
SEGNALE, non dell'esecuzione filtrata dal bucket a 2 slot, per capire la
causa a monte), poi correlazione di Pearson a coppie sulla matrice
giorno x strategia (zero dove una strategia non ha trade quel giorno -
approssimazione dichiarata: i giorni senza trade contano come "R=0",
non "dato mancante", perche' vogliamo misurare la co-occorrenza reale
dei giorni di guadagno/perdita, non solo tra i giorni in cui ENTRAMBE
capitano ad avere un trade).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pe", os.path.join(HERE, "portfolio_expanded_24-08.py"))
pe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pe)


def build_daily_matrix(trades):
    strat_names = sorted(set(t["strat"] for t in trades))
    all_dates = sorted(set(t["open_time"].split(" ")[0] for t in trades))
    idx = {d: i for i, d in enumerate(all_dates)}
    mat = {s: [0.0] * len(all_dates) for s in strat_names}
    for t in trades:
        d = t["open_time"].split(" ")[0]
        mat[t["strat"]][idx[d]] += t["net_r"]
    return strat_names, all_dates, mat


def pearson(a, b):
    n = len(a)
    ma = sum(a) / n
    mb = sum(b) / n
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va <= 0 or vb <= 0:
        return None
    return cov / (va ** 0.5 * vb ** 0.5)


def main():
    trades = pe.collect_all_trades("retail_standard")
    strat_names, all_dates, mat = build_daily_matrix(trades)
    n = len(strat_names)
    print(f"{n} strategie, {len(all_dates)} giorni con almeno un trade (qualche strategia)", flush=True)

    corr = {}
    for i in range(n):
        for j in range(i + 1, n):
            a, b = strat_names[i], strat_names[j]
            c = pearson(mat[a], mat[b])
            corr[(a, b)] = c

    pairs = sorted(corr.items(), key=lambda kv: -(kv[1] if kv[1] is not None else -2))
    print("\n=== Coppie piu' correlate (rischio di ridondanza / concentrazione) ===", flush=True)
    for (a, b), c in pairs[:20]:
        print(f"  {a:26s} <-> {b:26s}  r={c:+.3f}", flush=True)

    print("\n=== Coppie piu' NEGATIVAMENTE correlate (vera diversificazione / hedge naturale) ===", flush=True)
    for (a, b), c in pairs[-15:]:
        print(f"  {a:26s} <-> {b:26s}  r={c:+.3f}", flush=True)

    print("\n=== Correlazione media di ciascuna strategia con TUTTE le altre (piu' alta = piu' ridondante) ===", flush=True)
    avg_corr = {}
    for s in strat_names:
        vals = []
        for (a, b), c in corr.items():
            if c is None:
                continue
            if a == s or b == s:
                vals.append(c)
        avg_corr[s] = sum(vals) / len(vals) if vals else None
    for s, v in sorted(avg_corr.items(), key=lambda kv: -(kv[1] if kv[1] is not None else -2)):
        print(f"  {s:26s} corr_media={v:+.3f}" if v is not None else f"  {s:26s} n/a", flush=True)


if __name__ == "__main__":
    main()
