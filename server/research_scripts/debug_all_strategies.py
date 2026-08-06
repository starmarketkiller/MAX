#!/usr/bin/env python3
"""
06/08 - debug sistematico: per ognuna delle 40 strategie con implementazione
Python, conta quante volte la formula GREZZA (sig_*(c, ind, i) != 0, prima di
qualunque filtro: htf_filter, session_filter, confirm_bars, cooldown, singola
posizione aperta) scatta su ciascun timeframe D1/H4/H1 - poi lancia un
run_backtest reale sul timeframe con piu' segnali grezzi e riporta quanti di
quei segnali sono diventati trade davvero. La differenza fra "segnali grezzi"
e "trade reali" isola la causa:

- segnali grezzi ~0 su tutti i TF -> la formula stessa non ha condizioni
  d'ingresso sufficienti per questo strumento/periodo (raro genuinamente, o
  bug nella formula - da leggere caso per caso).
- segnali grezzi alti ma trade reali molto piu' bassi -> non e' la formula,
  e' la gestione posizione (una sola posizione alla volta: un segnale che
  arriva mentre la strategia e' gia' in trade viene scartato, non e' un
  bug, e' il limite dichiarato del motore single-position).
- errore/eccezione -> problema di cablaggio (chiave ind[] mancante, ecc.),
  non di edge.

Esegui dalla root del repo: python3 server/research_scripts/debug_all_strategies.py
"""
import sys
sys.path.insert(0, "server")
import backtest as bt

COSTS = bt.COST_PRESETS["retail_standard"]
TFS = ("1d", "4h", "1h")


def main():
    cache = {}   # tf -> (candles, ind)

    def get_prepped(tf):
        if tf not in cache:
            c, src = bt._fetch_real("XAUUSD", tf, 800)
            cache[tf] = (c, bt._prep(c), src)
        return cache[tf]

    rows = []
    for strat in sorted(bt.STRATEGIES):
        sig_fn = bt.STRATEGIES[strat]
        raw_counts = {}
        err = None
        for tf in TFS:
            try:
                c, ind, src = get_prepped(tf)
                raw = 0
                for i in range(len(c)):
                    try:
                        if sig_fn(c, ind, i) != 0:
                            raw += 1
                    except Exception as e:
                        err = f"{tf}@{i}: {str(e)[:100]}"
                        break
                raw_counts[tf] = raw
            except Exception as e:
                err = f"{tf} prep: {str(e)[:100]}"
                raw_counts[tf] = -1
            if err:
                break

        best_tf = max(raw_counts, key=raw_counts.get) if raw_counts else None
        real_trades = None
        real_pf = None
        if not err and best_tf and raw_counts[best_tf] > 0:
            try:
                r = bt.run_backtest(symbol="XAUUSD", strategy=strat, timeframe=best_tf, **COSTS)
                real_trades = r["trades"]
                real_pf = r["profit_factor"]
            except Exception as e:
                err = f"run_backtest: {str(e)[:100]}"

        rows.append({"strat": strat, "raw": raw_counts, "best_tf": best_tf,
                    "real_trades": real_trades, "real_pf": real_pf, "err": err})
        print(f"[{strat}] fatto", flush=True)

    print("\n" + "=" * 130)
    print(f"{'Strategia':<26}{'raw_1d':>8}{'raw_4h':>8}{'raw_1h':>8}{'best_tf':>9}"
          f"{'trade_reali':>13}{'PF':>7}  Diagnosi")
    for r in rows:
        raw = r["raw"]
        r1d, r4h, r1h = raw.get("1d", "-"), raw.get("4h", "-"), raw.get("1h", "-")
        if r["err"]:
            diag = f"ERRORE: {r['err']}"
        elif r["real_trades"] is None:
            diag = "nessun segnale grezzo su nessun TF (formula non scatta mai)"
        elif r["real_trades"] == 0:
            diag = "segnali grezzi presenti ma 0 trade reali -> gestione posizione, non formula"
        else:
            best_raw = raw.get(r["best_tf"], 0)
            ratio = r["real_trades"] / best_raw if best_raw else 0
            if ratio < 0.3:
                diag = f"solo {ratio*100:.0f}% dei segnali grezzi diventa trade -> molto filtrato da posizione singola"
            else:
                diag = "normale"
        pf_s = f"{r['real_pf']:.2f}" if r["real_pf"] is not None else "  n/a"
        tr_s = str(r["real_trades"]) if r["real_trades"] is not None else "  n/a"
        print(f"{r['strat']:<26}{r1d!s:>8}{r4h!s:>8}{r1h!s:>8}{(r['best_tf'] or '-'):>9}"
              f"{tr_s:>13}{pf_s:>7}  {diag}")
    print("=" * 130)


if __name__ == "__main__":
    main()
