#!/usr/bin/env python3
"""Phase 7.16 punto 2/3 - dimostra la prima divergenza causale fra la
ricostruzione Python TF-scoped ORIGINALE (Phase 7.13, congelata,
touched su bars[i]) e una versione CORRETTA (questa fase, touched su
bars[i+1]), sulla STESSA serie D1 locale gia' disponibile
(server/research_scripts/phase7/phase7_13/multi_tf_dataset_v1.json -
NESSUN nuovo run/download). Confronta poi entrambe con il trace EA
reale post-fix di Phase 7.14 (nxs_orderblock_realtrace_diag_postfix_
curated.csv) per quantificare quanto l'errore di allineamento spiega
della divergenza EA/Python gia' osservata in Phase 7.14/7.15.

Costruisce anche 2-10 episodi minimi calcolabili a mano (punto 3),
distinti dalla dimostrazione sui dati reali sopra.
"""
import csv
import os
import sys
from datetime import datetime

PHASE716_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE713_DIR = os.path.abspath(os.path.join(PHASE716_DIR, "..", "phase7_13"))
PHASE714_DIR = os.path.abspath(os.path.join(PHASE716_DIR, "..", "phase7_14"))
ROOT = os.path.abspath(os.path.join(PHASE716_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

sys.path.insert(0, PHASE713_DIR)
from nxs_order_block_replica import OBState, ob_update_side  # noqa: E402

sys.path.insert(0, PHASE716_DIR)
from nxs_order_block_replica_corrected import ob_update_side_corrected  # noqa: E402

MULTI_TF_DATASET = os.path.join(PHASE713_DIR, "multi_tf_dataset_v1.json")
EA_CURATED_POSTFIX = os.path.join(PHASE714_DIR, "nxs_orderblock_realtrace_diag_postfix_curated.csv")


def _run_d1_only(update_fn):
    doc = load_json(MULTI_TF_DATASET)
    bars = doc["payload"]["tf_bars"]["D1"]
    atr = doc["payload"]["tf_atr"]["D1"]
    state_buy, state_sell = OBState(), OBState()
    events = []
    full_log = []
    for i in range(len(bars)):
        a = atr[i]
        if a is None:
            continue
        curbar0 = bars[i + 1]["open_time"] if i + 1 < len(bars) else bars[i]["close_time"]
        sig, reason, mut_buy = update_fn(+1, state_buy, bars, i, a, curbar0)
        mut_sell = None
        if sig is None:
            sig, reason, mut_sell = update_fn(-1, state_sell, bars, i, a, curbar0)
        full_log.append({
            "bar_index": i, "close_time": bars[i]["close_time"], "curbar0": curbar0,
            "op_buy": mut_buy["op"] if mut_buy else None,
            "op_sell": mut_sell["op"] if mut_sell else None,
            "signal": sig,
        })
        if sig is not None:
            events.append({"close_time": bars[i]["close_time"], "dir": sig})
    return events, full_log, bars


def _load_ea_events():
    with open(EA_CURATED_POSTFIX, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        if r["op"] == "RETEST_SIGNAL_FIRED":
            dt = datetime.strptime(r["close_time_srv"], "%Y.%m.%d %H:%M:%S")
            out.append({"date": dt.date().isoformat(), "dir": r["signal_dir"]})
    return out


def _find_first_divergence(log_a, log_b, label_a, label_b):
    """Confronta due log completi (stesse barre, stesso indice) e trova
    il primo indice in cui op_buy o op_sell differisce."""
    n = min(len(log_a), len(log_b))
    for k in range(n):
        a, b = log_a[k], log_b[k]
        if a["op_buy"] != b["op_buy"] or a["op_sell"] != b["op_sell"]:
            return {
                "found": True,
                "bar_index": a["bar_index"],
                "close_time": a["close_time"],
                f"{label_a}_op_buy": a["op_buy"], f"{label_a}_op_sell": a["op_sell"],
                f"{label_b}_op_buy": b["op_buy"], f"{label_b}_op_sell": b["op_sell"],
                "context_prior_5_bars": [
                    {"bar_index": log_a[j]["bar_index"], "close_time": log_a[j]["close_time"],
                     f"{label_a}_op_buy": log_a[j]["op_buy"], f"{label_a}_op_sell": log_a[j]["op_sell"],
                     f"{label_b}_op_buy": log_b[j]["op_buy"], f"{label_b}_op_sell": log_b[j]["op_sell"]}
                    for j in range(max(0, k - 5), k)
                ],
            }
    return {"found": False, "note": "nessuna divergenza trovata nei log confrontati"}


def build():
    original_events, original_log, bars = _run_d1_only(ob_update_side)
    corrected_events, corrected_log, _ = _run_d1_only(ob_update_side_corrected)
    ea_events = _load_ea_events()

    # normalizza le date (Python usa ISO 'YYYY-MM-DDTHH:MM:SS' in close_time,
    # EA usa 'YYYY-MM-DD' in date)
    def _norm_python(events):
        return {(e["close_time"].split("T")[0], e["dir"]) for e in events}

    def _norm_ea(events):
        return {(e["date"], e["dir"]) for e in events}

    orig_set = _norm_python(original_events)
    corr_set = _norm_python(corrected_events)
    ea_set = _norm_ea(ea_events)

    match_orig_ea = orig_set & ea_set
    match_corr_ea = corr_set & ea_set

    first_div_orig_vs_corrected = _find_first_divergence(original_log, corrected_log, "original", "corrected")

    payload = {
        "method": "Ri-derivazione in Python, sulla STESSA serie D1 locale gia' disponibile "
                 "(phase7_13/multi_tf_dataset_v1.json, nessun nuovo run/download) - confronto fra "
                 "la ricostruzione ORIGINALE (Phase 7.13, congelata) e una versione CORRETTA "
                 "(questa fase, touched su bars[i+1] invece di bars[i]).",
        "original_python_events": sorted(orig_set),
        "corrected_python_events": sorted(corr_set),
        "ea_real_events_postfix": sorted(ea_set),
        "n_original_python": len(orig_set),
        "n_corrected_python": len(corr_set),
        "n_ea_real": len(ea_set),
        "n_matches_original_vs_ea": len(match_orig_ea),
        "n_matches_corrected_vs_ea": len(match_corr_ea),
        "matches_original_vs_ea": sorted(match_orig_ea),
        "matches_corrected_vs_ea": sorted(match_corr_ea),
        "correction_improves_match_rate": len(match_corr_ea) > len(match_orig_ea),
        "first_divergence_original_vs_corrected_on_same_local_series": first_div_orig_vs_corrected,
        "blocker_for_direct_ea_vs_python_state_trace": (
            "L'istrumentazione diagnostica di Phase 7.14 ha registrato SOLO lo stato della zona "
            "(active/obLo/obHi/barsWaited) e l'operazione (op), NON le barre D1 OHLC grezze "
            "effettivamente usate dall'EA in quel momento - quindi non e' possibile ricostruire "
            "un confronto input->stato->transizione campo-per-campo fra EA reale e Python sulla "
            "STESSA barra di prezzo: si puo' confrontare solo la SEQUENZA di operazioni per data "
            "(fatto sopra), non le barre OHLC sottostanti bar-per-bar. Campo mancante: OHLC D1 "
            "reali usate dall'EA durante il run Tester (non esportate in nessun artifact di "
            "Phase 7.14)."
        ),
        "no_new_long_run_launched": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE716_DIR, "first_divergence_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  eventi Python originale: {payload['n_original_python']}, corretto: {payload['n_corrected_python']}, EA reale: {payload['n_ea_real']}")
    print(f"  match originale/EA: {payload['n_matches_original_vs_ea']}, corretto/EA: {payload['n_matches_corrected_vs_ea']}")
    print(f"  la correzione migliora il match rate: {payload['correction_improves_match_rate']}")


if __name__ == "__main__":
    main()
