#!/usr/bin/env python3
"""
13/08 - TURTLE_SOUP_CHOCH era "promettente, non confermato" sulla nota vault
"Strategie/Turtle Soup.md" (11/08): su 4h walk-forward 4/5 e drawdown
dimezzato/triplicato-in-meno rispetto al baseline flat, ma su 1h (il vero TF
di profilo in MQL5) non migliora, e la finestra di lookback (5 barre) non e'
mai stata sweepata.

Prima di un'altra griglia di uscita, due domande sull'ENTRY stessa (non
sull'uscita): l'ingresso a mercato sulla barra del CHoCH puo' essere lontano
dalla zona di sweep su cui e' ancorato lo SL (TURTLE_SOUP_CHOCH_NEAR: filtra
per prossimita'), e il filtro body-forte oggi vale solo sulla barra storica
del sweep, mai su quella del CHoCH stesso (TURTLE_SOUP_CHOCH_DBLBODY: doppia
conferma). Vedi i due nuovi sig_* in backtest.py per l'implementazione.

Metodo identico a exit_optimizer_grid.py: baseline vs varianti su IS, solo i
sopravvissuti al filtro IS vanno a OOS, il migliore per OOS viene riverificato
con walk-forward a 5 finestre prima di qualunque conclusione. Sweep aggiuntivo
sulla finestra di lookback (3/5/7/10 barre) per ciascuna variante.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL = "XAUUSD"
BARS = 110000
IS_RANGE, OOS_RANGE = (0.0, 0.6), (0.6, 1.0)
N_WINDOWS = 5
TFS = ["4h", "1h"]
VARIANTS = ["TURTLE_SOUP_CHOCH", "TURTLE_SOUP_CHOCH_NEAR", "TURTLE_SOUP_CHOCH_DBLBODY"]
LOOKBACK_GRID = [3, 5, 7, 10]

MIN_IS_PF = 1.10
MIN_IS_TRADES = 30   # 4h/1h campionano meno di 30m/M15 - soglia piu' bassa di CRT/FVG_CONT


def call(tf, strat, bar_range):
    return bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                            risk_pct=1.0, bars=BARS, bar_range=bar_range)


def walk_forward(tf, strat):
    out = []
    for w in range(N_WINDOWS):
        br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
        r = call(tf, strat, br)
        out.append((r.get("profit_factor"), r.get("trades")))
    return out


def main():
    print("NEXUS - TURTLE_SOUP_CHOCH: varianti di ENTRY + finestra di lookback", flush=True)
    for tf in TFS:
        print(f"\n{'='*72}\nTF={tf}\n{'='*72}", flush=True)
        base_oos = call(tf, "TURTLE_SOUP", OOS_RANGE)
        print(f"BASELINE (TURTLE_SOUP, senza CHoCH) OOS: pf={base_oos.get('profit_factor')} "
              f"n={base_oos.get('trades')} dd={base_oos.get('max_dd_pct')}%", flush=True)

        best = None
        for variant in VARIANTS:
            for lookback in LOOKBACK_GRID:
                bt._TURTLE_SOUP_CHOCH_LOOKBACK = lookback
                is_r = call(tf, variant, IS_RANGE)
                pf_is = is_r.get("profit_factor") or 0
                if pf_is <= MIN_IS_PF or is_r.get("trades", 0) <= MIN_IS_TRADES:
                    continue
                oos_r = call(tf, variant, OOS_RANGE)
                pf_oos = oos_r.get("profit_factor") or 0
                print(f"  {variant:<28} lookback={lookback:>2} -> "
                      f"IS pf={pf_is} n={is_r.get('trades')} | "
                      f"OOS pf={pf_oos} n={oos_r.get('trades')} dd={oos_r.get('max_dd_pct')}%", flush=True)
                if pf_oos > (base_oos.get("profit_factor") or 0) and (best is None or pf_oos > best["oos_pf"]):
                    best = {"variant": variant, "lookback": lookback, "oos_pf": pf_oos,
                            "oos_n": oos_r.get("trades"), "oos_dd": oos_r.get("max_dd_pct"),
                            "is_pf": pf_is, "is_n": is_r.get("trades")}

        if not best:
            print("-- Nessuna variante batte TURTLE_SOUP base OOS sopravvivendo al filtro IS.", flush=True)
            continue
        print(f"-- MIGLIOR CANDIDATO: {best}", flush=True)
        bt._TURTLE_SOUP_CHOCH_LOOKBACK = best["lookback"]
        print("-- walk-forward di verifica (5 finestre) candidato vs baseline vs CHoCH originale (lookback=5)...", flush=True)
        wf_cand = walk_forward(tf, best["variant"])
        wf_base = walk_forward(tf, "TURTLE_SOUP")
        bt._TURTLE_SOUP_CHOCH_LOOKBACK = 5
        wf_choch_orig = walk_forward(tf, "TURTLE_SOUP_CHOCH")
        print("   candidato:      " + "  |  ".join(f"{pf}/{n}" for pf, n in wf_cand), flush=True)
        print("   baseline (base):" + "  |  ".join(f"{pf}/{n}" for pf, n in wf_base), flush=True)
        print("   CHoCH originale:" + "  |  ".join(f"{pf}/{n}" for pf, n in wf_choch_orig), flush=True)


if __name__ == "__main__":
    main()
