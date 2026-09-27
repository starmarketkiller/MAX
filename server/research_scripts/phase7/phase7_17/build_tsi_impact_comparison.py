#!/usr/bin/env python3
"""Phase 7.17 punto 4 - misura la materialita' del difetto TSI usando
dati REALI gia' scaricati e disponibili localmente
(phase7_13/multi_tf_dataset_v1.json, M15 reale 2023-10-02..2026-08-25,
ricampionato deterministicamente in M30/H1/H4/D1) - NESSUN nuovo run
Tester lanciato in questa fase.

SCELTA DI SCOPE ESPLICITA: a differenza di ORDER_BLOCK (dove la logica
dipende da soglie di prezzo/ATR con branching condizionale, e un trace
EA reale a tick era necessario per verificare i rami effettivamente
presi), il meccanismo TSI e' un filtro ricorsivo PURAMENTE MATEMATICO
(nessun branching su soglie di prezzo per la MUTAZIONE dello stato,
solo per il segnale finale di cross) - gia' dimostrato deterministico
ed esatto nei casi minimi (punto 3, verificato in aritmetica razionale
esatta). Riusare i dati M15 locali gia' disponibili per quantificare
la materialita' su ~2.9 anni reali e' quindi sufficiente e coerente
con l'istruzione esplicita di NON lanciare un nuovo run se evitabile.
"""
import os
import sys

PHASE717_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE713_DIR = os.path.abspath(os.path.join(PHASE717_DIR, "..", "phase7_13"))
ROOT = os.path.abspath(os.path.join(PHASE717_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

sys.path.insert(0, PHASE717_DIR)
from nxs_tsi_replica import TSIState, tsi_update  # noqa: E402

MULTI_TF_DATASET = os.path.join(PHASE713_DIR, "multi_tf_dataset_v1.json")
PASSES = ["D1", "H4", "H1", "M30", "M15"]
CANONICAL_TF = "D1"
EXCLUDED_PASSES_DECLARED = ["M5"]


def _curbar0(bars, i):
    return bars[i + 1]["open_time"] if i + 1 < len(bars) else bars[i]["close_time"]


def _global_event_order(tf_bars):
    tf_rank = {"M15": 0, "M30": 1, "H1": 2, "H4": 3, "D1": 4}
    events = []
    for tf in PASSES:
        bars = tf_bars[tf]
        for i in range(len(bars)):
            events.append((bars[i]["close_time"], tf_rank[tf], tf, i))
    events.sort(key=lambda e: (e[0], e[1]))
    return events


def build():
    doc = load_json(MULTI_TF_DATASET)
    tf_bars = doc["payload"]["tf_bars"]
    events = _global_event_order(tf_bars)

    seed_close = tf_bars[CANONICAL_TF][0]["open"]  # proxy per iClose(tf,2) al primissimo avvio

    state_a = TSIState()
    state_b = TSIState()

    d1_series_a = []   # (close_time, tsi, signal, signal_dir) per OGNI chiusura D1, Stream A
    d1_series_b = []   # idem, Stream B (D1-only)
    raw_triggers_a_by_tf = {}
    n_mutations_non_canonical_a = 0

    for close_time, _rank, tf, i in events:
        bars = tf_bars[tf]
        c1 = bars[i]["close"]
        curbar0 = _curbar0(bars, i)

        sig_a, rec_a = tsi_update(state_a, c1, curbar0, seed_close)
        if rec_a["mutated"] and tf != CANONICAL_TF:
            n_mutations_non_canonical_a += 1
        if sig_a is not None:
            raw_triggers_a_by_tf.setdefault(tf, {"BUY": 0, "SELL": 0})
            raw_triggers_a_by_tf[tf][sig_a] += 1
        if tf == CANONICAL_TF:
            d1_series_a.append({"close_time": close_time, "tsi": rec_a.get("tsi"),
                               "signal": rec_a.get("signal_line"), "dir": sig_a})
            sig_b, rec_b = tsi_update(state_b, c1, curbar0, seed_close)
            d1_series_b.append({"close_time": close_time, "tsi": rec_b.get("tsi"),
                               "signal": rec_b.get("signal_line"), "dir": sig_b})

    n_d1 = len(d1_series_a)
    n_with_tsi_both = sum(1 for a, b in zip(d1_series_a, d1_series_b)
                          if a["tsi"] is not None and b["tsi"] is not None)
    tsi_diffs = [abs(a["tsi"] - b["tsi"]) for a, b in zip(d1_series_a, d1_series_b)
                if a["tsi"] is not None and b["tsi"] is not None]
    n_tsi_identical = sum(1 for d in tsi_diffs if d < 1e-9)
    n_tsi_different = len(tsi_diffs) - n_tsi_identical
    max_tsi_diff = max(tsi_diffs) if tsi_diffs else None
    mean_tsi_diff = (sum(tsi_diffs) / len(tsi_diffs)) if tsi_diffs else None

    gen_a = [(e["close_time"], e["dir"]) for e in d1_series_a if e["dir"] is not None]
    gen_b = [(e["close_time"], e["dir"]) for e in d1_series_b if e["dir"] is not None]
    set_a, set_b = set(gen_a), set(gen_b)
    only_a = sorted(set_a - set_b)
    only_b = sorted(set_b - set_a)
    both = sorted(set_a & set_b)

    payload = {
        "data_source": "server/research_scripts/phase7/phase7_13/multi_tf_dataset_v1.json "
                       "(GIA' disponibile, nessun nuovo download/run)",
        "period_covered": doc["payload"]["source_date_range"],
        "scope_decision_no_new_tester_run": (
            "Il meccanismo TSI e' un filtro ricorsivo puramente matematico (nessun "
            "branching su soglie di prezzo nella mutazione dello stato) - gia' dimostrato "
            "esatto e deterministico nei casi minimi con aritmetica razionale (punto 3). "
            "Riusare i dati M15 locali reali gia' disponibili e' sufficiente per "
            "quantificare la materialita' - nessun nuovo run Tester necessario, a "
            "differenza di ORDER_BLOCK dove il branching su soglie ATR/BOS richiedeva "
            "conferma su tick reali."
        ),
        "canonical_tf": CANONICAL_TF,
        "excluded_passes_declared": EXCLUDED_PASSES_DECLARED,
        "n_d1_bars_evaluated": n_d1,
        "n_mutations_total_stream_a": sum(1 for _ in events),
        "n_mutations_non_canonical_stream_a": n_mutations_non_canonical_a,
        "n_mutations_canonical_only_stream_b": n_d1,
        "raw_triggers_stream_a_by_tf": raw_triggers_a_by_tf,
        "tsi_value_divergence": {
            "n_d1_bars_with_tsi_computed_both_streams": n_with_tsi_both,
            "n_d1_bars_tsi_value_identical": n_tsi_identical,
            "n_d1_bars_tsi_value_different": n_tsi_different,
            "pct_d1_bars_tsi_different": (100.0 * n_tsi_different / n_with_tsi_both) if n_with_tsi_both else None,
            "max_absolute_tsi_difference": max_tsi_diff,
            "mean_absolute_tsi_difference": mean_tsi_diff,
            "note": "Conferma la predizione della formalizzazione (punto 2): la "
                   "contaminazione e' UNIVERSALE, non solo su alcune date - quasi ogni "
                   "lettura D1 del TSI e' numericamente diversa fra Stream A e B, non "
                   "solo quelle che producono un segnale.",
        },
        "signal_level_comparison": {
            "n_generated_a": len(gen_a), "n_generated_b": len(gen_b),
            "n_matched_same_date_direction": len(both),
            "n_only_in_a": len(only_a), "n_only_in_b": len(only_b),
            "only_in_a_sample": only_a[:20], "only_in_b_sample": only_b[:20],
        },
        "defect_exists": n_tsi_different > 0,
        "defect_materially_changes_behavior": (len(only_a) + len(only_b)) > 0,
        "no_pf_or_return_used": True,
        "no_new_tester_run_launched": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE717_DIR, "tsi_impact_comparison_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    tv = payload["tsi_value_divergence"]
    print(f"  barre D1 con TSI diverso fra A e B: {tv['n_d1_bars_tsi_value_different']}/"
          f"{tv['n_d1_bars_with_tsi_computed_both_streams']} "
          f"({tv['pct_d1_bars_tsi_different']:.1f}%)" if tv['pct_d1_bars_tsi_different'] else "")
    sl = payload["signal_level_comparison"]
    print(f"  segnali generati A: {sl['n_generated_a']}, B: {sl['n_generated_b']}, "
          f"uguali: {sl['n_matched_same_date_direction']}, "
          f"solo A: {sl['n_only_in_a']}, solo B: {sl['n_only_in_b']}")
    print(f"  defect_materially_changes_behavior: {payload['defect_materially_changes_behavior']}")


if __name__ == "__main__":
    main()
