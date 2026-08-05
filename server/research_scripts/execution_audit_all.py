#!/usr/bin/env python3
"""
04/08 (17) - Estende execution_audit.py a TUTTE le strategie del motore
(non solo il pilota TURTLE_SOUP), su richiesta esplicita dell'utente
("Estendiamo"). Stesso metodo, stessa disciplina - un audit per
strategia x timeframe, salvato su file JSON per non perdere il lavoro se
il run viene interrotto.

Esegui dalla root del repo: python3 server/research_scripts/execution_audit_all.py
"""
import json
import sys
import time
from collections import Counter

sys.path.insert(0, "server")
sys.path.insert(0, "server/research_scripts")
import backtest as bt
from execution_audit import execution_audit

TFS = ["4h", "1h", "1d", "1wk"]
OUT_PATH = "server/data_cache/execution_audit_all.json"


def _json_safe(r):
    out = dict(r)
    out["reasons"] = dict(r["reasons"])
    out["entry_quality_dist"] = {str(k): v for k, v in r["entry_quality_dist"].items()}
    out.pop("entries", None)   # dettaglio per-trade non serve nel riepilogo, tenerlo gonfierebbe il file
    return out


def main():
    strategies = sorted(bt.STRATEGIES.keys())
    results = {}
    t0 = time.time()
    for si, strat in enumerate(strategies, 1):
        results[strat] = {}
        for tf in TFS:
            try:
                r = execution_audit(strat, tf)
                results[strat][tf] = _json_safe(r)
            except Exception as e:
                results[strat][tf] = {"error": str(e)[:200]}
        with open(OUT_PATH, "w") as f:
            json.dump(results, f, indent=2)
        print(f"[{si}/{len(strategies)}] {strat} fatto ({time.time()-t0:.0f}s)", flush=True)
    print(f"Completato in {time.time()-t0:.0f}s, scritto {OUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
