#!/usr/bin/env python3
"""Phase 7.18 - curazione delle tracce diagnostiche raw (troppo grandi
per il commit: l'istrumentazione TSI logga OGNI tick che raggiunge la
posizione della chiamata, non solo le transizioni di barra - vedi nota
operativa nel vault report).

ATTENZIONE (scoperta durante la curazione, non nella prima bozza):
un semplice "1 riga per (close_time_srv, tf)" e' CORRETTO per la
traccia post-fix (0/166 chiavi mostrano piu' di un signal_dir - lo
stato non cambia piu' entro la stessa barra una volta bloccati i TF
non canonici), ma e' SBAGLIATO per la traccia pre-fix: la
contaminazione cross-TF puo' alterare g_tsiState FRA due tick
etichettati D1 della stessa barra apparente, quindi 166/166 chiavi
D1 della traccia pre-fix mostrano PIU' di un signal_dir nella stessa
finestra (fino a 4 valori distinti: WARMUP/NONE/BUY/SELL) - collassare
al solo primo tick avrebbe cancellato evidenza reale del difetto.

Curazione adottata (transition-based, senza perdita per l'analisi a
valle): per ogni chiave (close_time_srv, tf), tiene una riga solo
quando il suo signal_dir DIFFERISCE dall'ultima riga tenuta per quella
stessa chiave - cattura ogni cambio di stato osservabile (compreso il
flip-flop da contaminazione) scartando solo le ripetizioni identiche
consecutive dovute al logging per-tick.
"""
import csv
import os
import sys

PHASE718_DIR = os.path.dirname(os.path.abspath(__file__))

RAW_TO_CURATED = [
    ("nxs_tsi_realtrace_diag_prefix.csv", "nxs_tsi_realtrace_diag_prefix_curated.csv"),
    ("nxs_tsi_realtrace_diag_postfix.csv", "nxs_tsi_realtrace_diag_postfix_curated.csv"),
]

FIELDNAMES = ["close_time_srv", "tf", "canonical_tf", "mutated", "pre_sm2", "pre_sm2Abs",
             "pre_signal", "pre_bars_seen", "post_sm2", "post_sm2Abs", "post_signal",
             "post_bars_seen", "tsi", "signal_line", "signal_dir", "would_be_kept_by_router"]


def curate(raw_path):
    with open(raw_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    last_dir = {}
    curated_rows = []
    for r in rows:
        key = (r["close_time_srv"], r["tf"])
        d = r["signal_dir"]
        if last_dir.get(key) != d:
            curated_rows.append(r)
            last_dir[key] = d
    return len(rows), curated_rows


def main():
    for raw_name, curated_name in RAW_TO_CURATED:
        raw_path = os.path.join(PHASE718_DIR, raw_name)
        if not os.path.exists(raw_path):
            print(f"SALTATO (raw non presente): {raw_name}")
            continue
        n_raw, curated_rows = curate(raw_path)
        curated_path = os.path.join(PHASE718_DIR, curated_name)
        with open(curated_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDNAMES)
            w.writeheader()
            for r in curated_rows:
                w.writerow(r)
        print(f"{raw_name}: {n_raw} righe raw -> {len(curated_rows)} righe curate ({curated_name})")


if __name__ == "__main__":
    main()
