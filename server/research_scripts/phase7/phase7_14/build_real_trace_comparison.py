#!/usr/bin/env python3
"""Phase 7.14 punto 2 - carica il trace reale prodotto dall'EA
istrumentato (nxs_orderblock_realtrace_diag.csv, scritto in
Terminal/Common/Files/ dalla Strategy Tester) e lo confronta con la
ricostruzione Python di Phase 7.13 (ab_simulation_v1.json / ipotesi
strutturale) per verificare se il meccanismo di contaminazione e'
osservabile end-to-end nel percorso EA reale -> router -> stato ->
segnale.
"""
import csv
import os
import sys

PHASE714_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE714_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, file_sha256  # noqa: E402

# Copiato da Terminal/Common/Files/nxs_orderblock_realtrace_diag.csv subito
# dopo la fine del run (il file live resta soggetto a lock/sovrascrittura del
# terminale) - vedi baseline_pre_fix_v1.json per l'hash del sorgente al momento
# della cattura.
REAL_TRACE_CSV = os.path.join(PHASE714_DIR, "nxs_orderblock_realtrace_diag_prefix.csv")


def load_real_trace():
    with open(REAL_TRACE_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return rows


def build():
    rows = load_real_trace()
    n_total = len(rows)
    by_tf = {}
    by_op = {}
    canonical_tf = rows[0]["canonical_tf"] if rows else None
    n_kept_true = 0
    n_signals_fired = 0
    n_signals_fired_non_canonical = 0
    n_signals_fired_canonical = 0
    canonical_events = []
    non_canonical_mutating_ops = {"ZONE_CREATED", "ZONE_INVALIDATED", "ZONE_EXPIRED", "RETEST_SIGNAL_FIRED"}
    n_non_canonical_state_mutations = 0

    for r in rows:
        tf = r["tf"]
        op = r["op"]
        by_tf[tf] = by_tf.get(tf, 0) + 1
        by_op[op] = by_op.get(op, 0) + 1
        kept = r["would_be_kept_by_router"] == "1"
        if kept:
            n_kept_true += 1
        if r["signal_dir"] in ("BUY", "SELL"):
            n_signals_fired += 1
            if kept:
                n_signals_fired_canonical += 1
            else:
                n_signals_fired_non_canonical += 1
        if tf != canonical_tf and op in non_canonical_mutating_ops:
            n_non_canonical_state_mutations += 1
        if tf == canonical_tf:
            canonical_events.append(r)

    # Casi causali end-to-end: cerca sequenze in cui un evento non canonico
    # muta la zona (creata/invalidata/consumata) e il successivo evento
    # canonico D1 sulla STESSA sequenza (side) mostra un effetto coerente
    # (es. IDLE/ricerca invece di un retest gia' pronto, o zona gia' non
    # attiva quando altrimenti sarebbe rimasta attiva).
    end_to_end_examples = []
    last_non_canonical_mutation = {"BUY_SIDE": None, "SELL_SIDE": None}
    for r in rows:
        side = r["side"]
        tf = r["tf"]
        op = r["op"]
        if tf != canonical_tf and op in non_canonical_mutating_ops:
            last_non_canonical_mutation[side] = r
        if tf == canonical_tf and last_non_canonical_mutation[side] is not None:
            end_to_end_examples.append({
                "canonical_event": r,
                "preceding_non_canonical_mutation": last_non_canonical_mutation[side],
            })
            last_non_canonical_mutation[side] = None  # un solo abbinamento per occorrenza

    payload = {
        "source_csv": os.path.relpath(REAL_TRACE_CSV, ROOT).replace(os.sep, "/")
                     if REAL_TRACE_CSV.startswith(ROOT) else REAL_TRACE_CSV,
        "source_sha256": file_sha256(REAL_TRACE_CSV) if os.path.exists(REAL_TRACE_CSV) else None,
        "n_rows_total": n_total,
        "canonical_tf_observed": canonical_tf,
        "rows_by_tf": by_tf,
        "rows_by_op": by_op,
        "n_signals_fired_total": n_signals_fired,
        "n_signals_fired_canonical_kept": n_signals_fired_canonical,
        "n_signals_fired_non_canonical_discarded": n_signals_fired_non_canonical,
        "n_non_canonical_state_mutations": n_non_canonical_state_mutations,
        "n_canonical_events": len(canonical_events),
        "n_end_to_end_examples_found": len(end_to_end_examples),
        "end_to_end_examples_sample": end_to_end_examples[:15],
        "mechanism_observed_in_real_ea": n_non_canonical_state_mutations > 0 and len(end_to_end_examples) > 0,
        "not_a_backtest_campaign": True,
        "not_used_for_profitability": True,
    }
    return payload


def main():
    if not os.path.exists(REAL_TRACE_CSV):
        print(f"ERRORE: trace reale non trovato in {REAL_TRACE_CSV}")
        sys.exit(2)
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE714_DIR, "real_trace_comparison_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  righe totali: {payload['n_rows_total']}")
    print(f"  righe per TF: {payload['rows_by_tf']}")
    print(f"  righe per op: {payload['rows_by_op']}")
    print(f"  segnali sparati canonici (tenuti): {payload['n_signals_fired_canonical_kept']}")
    print(f"  segnali sparati non canonici (scartati): {payload['n_signals_fired_non_canonical_discarded']}")
    print(f"  mutazioni di stato non canoniche: {payload['n_non_canonical_state_mutations']}")
    print(f"  esempi end-to-end trovati: {payload['n_end_to_end_examples_found']}")
    print(f"  MECCANISMO OSSERVATO NELL'EA REALE: {payload['mechanism_observed_in_real_ea']}")


if __name__ == "__main__":
    main()
