#!/usr/bin/env python3
"""
10/08 (9) - verifica sistematica dell'ipotesi "molte strategie fanno
piu' trade e performano meglio su timeframe piu' bassi": IS/OOS per
tutte le 35 strategie su 15m/30m/1h/4h/1d, con bars alto (motore
post-fix del tetto 2500 - vedi NEXUS EA - MALAYSIAN_SNR Porting Tier 1,
sezione bug bars/_fetch_dukascopy). Non ancora fatto con questa
disciplina completa: gli scan multi-TF di ieri mattina (prima del fix)
erano limitati dal tetto silenzioso su 15m/30m/1h.

Due domande distinte, non una sola:
1. Frequenza: il conteggio trade cresce sui TF piu' bassi? (atteso: si',
   quasi sempre - piu' barre nello stesso periodo di calendario)
2. Qualita': il PF out-of-sample migliora, resta uguale o peggiora sui
   TF piu' bassi? (la vera domanda - piu' trade non e' automaticamente
   "meglio", puo' anche solo essere piu' rumore)
"""
import sys
import os
import time
import json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ensemble_engine_search as e

SYMBOL = "XAUUSD"
TFS = ["15m", "30m", "1h", "4h", "1d"]
BARS = 70000
MIN_TRADES = 8


def main():
    pool = e.pool_for(SYMBOL)
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "multitf_scan_full_results.json")
    results = {}
    # 10/08 (11) - salvataggio incrementale dopo OGNI timeframe: la prima
    # esecuzione e' stata uccisa da un timeout esterno (timeout 1100) a meta'
    # del secondo TF, perdendo il lavoro del primo (15m, 904s) perche' il
    # JSON veniva scritto solo a fine funzione. Ora ogni TF completato viene
    # salvato subito, cosi' un'interruzione a meta' non perde i TF gia' fatti.
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding="utf-8") as f:
                prev = json.load(f)
            results = prev.get("by_tf", {})
        except Exception:
            results = {}
    for tf in TFS:
        if tf in results:
            print(f"=== {tf} gia' presente nel salvataggio precedente, salto ===", flush=True)
            continue
        t0 = time.time()
        base = e.baseline_all(pool, SYMBOL, tf, BARS)
        results[tf] = base
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"by_tf": results, "summary": []}, f, indent=2)
        print(f"=== {tf} fatto in {time.time()-t0:.0f}s (salvato) ===", flush=True)

    # per strategia: quale TF ha l'OOS PF migliore con campione credibile (>=15 trade)
    print(f"\n{'Strategia':<26}{'TF migliore (OOS)':<10}{'OOS PF':>8}{'OOS n':>7}   "
          f"{'trend frequenza 15m->1d':<30}")
    summary = []
    for strat in pool:
        rows = {}
        for tf in TFS:
            row = next((r for r in results[tf] if r["strategy"] == strat), None)
            if row:
                rows[tf] = row
        best_tf, best = None, None
        for tf, row in rows.items():
            oos = row.get("oos", {})
            if oos.get("trades", 0) < 15 or oos.get("pf") is None:
                continue
            if best is None or oos["pf"] > best["oos"]["pf"]:
                best_tf, best = tf, row
        freq_trend = " -> ".join(str(rows[tf].get("oos", {}).get("trades", 0)) for tf in TFS if tf in rows)
        if best:
            print(f"{strat:<26}{best_tf:<10}{best['oos']['pf']:>8}{best['oos']['trades']:>7}   {freq_trend:<30}")
            summary.append({"strategy": strat, "best_tf": best_tf, "oos": best["oos"], "freq_trend": freq_trend})
        else:
            print(f"{strat:<26}{'--':<10}{'nessun TF con campione OOS credibile':<38}{freq_trend:<30}")
            summary.append({"strategy": strat, "best_tf": None, "freq_trend": freq_trend})

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"by_tf": results, "summary": summary}, f, indent=2)
    print(f"\nSalvato: {out_path}")


if __name__ == "__main__":
    main()
