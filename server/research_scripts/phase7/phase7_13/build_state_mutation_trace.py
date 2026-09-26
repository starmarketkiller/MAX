#!/usr/bin/env python3
"""Phase 7.13 punto 3 - trace completo dello stato per un piccolo
numero di casi reali selezionati (non l'intera serie, che sarebbe
enorme e illeggibile): per ciascun caso, ricostruiamo la timeline
COMPLETA fra due chiusure D1 consecutive mostrando ogni passaggio non
canonico che ha toccato lo stato nel mezzo, con:
  timestamp, TF chiamante, TF canonico, stato prima, operazione di
  mutazione, stato dopo, segnale prodotto, segnale accettato/scartato,
  motivo del gate, evento canonico successivo influenzato.

Ripete la simulazione di build_ab_simulation.py (stesso stato Stream A)
ma con logging ESAUSTIVO (non solo ai passaggi D1) per poter estrarre
le sotto-timeline dei casi scelti.
"""
import os
import sys

PHASE713_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE713_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

sys.path.insert(0, PHASE713_DIR)
from nxs_order_block_replica import OBState, ob_update_side  # noqa: E402
from build_ab_simulation import PASSES, CANONICAL_TF, _curbar0_time, _global_event_order  # noqa: E402

# Casi scelti da ab_simulation_v1.json: 2 segnali D1 genuini soppressi
# (only_in_b) e 1 segnale D1 creato SOLO dalla contaminazione (only_in_a).
CASES = [
    {"kind": "SUPPRESSED_GENUINE_D1_SIGNAL", "target_close_time": "2024-02-23T01:00:00", "side": "sell"},
    {"kind": "SUPPRESSED_GENUINE_D1_SIGNAL", "target_close_time": "2024-07-29T01:00:00", "side": "buy"},
    {"kind": "CONTAMINATION_CREATED_D1_SIGNAL", "target_close_time": "2023-11-01T01:00:00", "side": "sell"},
]

NOISY_OPS = {"NONE_NOT_NEW_BAR", "WAITING_NO_TOUCH", "TOUCHED_NO_REJECTION", "SEARCH_DISPLACEMENT_NO_MATCH"}


def _run_full_trace():
    doc = load_json(os.path.join(PHASE713_DIR, "multi_tf_dataset_v1.json"))
    data = doc["payload"]
    tf_bars, tf_atr = data["tf_bars"], data["tf_atr"]
    events = _global_event_order(tf_bars)
    state_buy, state_sell = OBState(), OBState()
    full_log = []
    for close_time, _rank, tf, i in events:
        bars = tf_bars[tf]
        atr = tf_atr[tf][i]
        if atr is None:
            continue
        curbar0 = _curbar0_time(bars, i)
        sig_dir, reason, mut_buy = ob_update_side(+1, state_buy, bars, i, atr, curbar0)
        mut_sell = None
        if sig_dir is None:
            sig_dir, reason, mut_sell = ob_update_side(-1, state_sell, bars, i, atr, curbar0)
        accepted = (tf == CANONICAL_TF) and sig_dir is not None
        discarded = (tf != CANONICAL_TF) and sig_dir is not None
        full_log.append({
            "close_time": close_time, "tf_chiamante": tf, "tf_canonico": CANONICAL_TF,
            "op_buy": mut_buy["op"] if mut_buy else None,
            "op_sell": mut_sell["op"] if mut_sell else None,
            "pre_buy": mut_buy["pre"] if mut_buy else None, "post_buy": mut_buy.get("post") if mut_buy else None,
            "pre_sell": mut_sell["pre"] if mut_sell else None, "post_sell": mut_sell.get("post") if mut_sell else None,
            "segnale_prodotto": sig_dir, "segnale_motivo": reason,
            "accettato": accepted,
            "scartato": discarded,
            "motivo_gate": ("nessuno (passaggio canonico D1)" if tf == CANONICAL_TF else
                            f"NXS_Profile_TF('ORDER_BLOCK')==D1 != passaggio {tf} "
                            f"(NEXUS_EA_v2.mq5:710) - scartato anche se un raw trigger e' stato prodotto") if sig_dir else None,
        })
    return full_log


def build():
    full_log = _run_full_trace()
    by_time = {e["close_time"]: idx for idx, e in enumerate(full_log)}
    d1_times = sorted(t for t, idx in by_time.items() if full_log[idx]["tf_chiamante"] == CANONICAL_TF)

    case_traces = []
    for case in CASES:
        target = case["target_close_time"]
        if target not in d1_times:
            case_traces.append({**case, "error": "close_time D1 non trovato nella serie derivata"})
            continue
        pos = d1_times.index(target)
        window_start = d1_times[pos - 1] if pos > 0 else None
        window_events = [e for e in full_log if (window_start is None or e["close_time"] > window_start)
                         and e["close_time"] <= target]
        side = case["side"]
        relevant = [e for e in window_events
                   if e[f"op_{side}"] not in (None,) and e[f"op_{side}"] not in NOISY_OPS
                   or e["close_time"] == target]
        # sempre includere l'evento target anche se il suo op e' "rumoroso" (es. SEARCH_DISPLACEMENT_NO_MATCH)
        target_event = next(e for e in window_events if e["close_time"] == target)
        if target_event not in relevant:
            relevant.append(target_event)
        relevant_sorted = sorted(relevant, key=lambda e: e["close_time"])
        case_traces.append({
            **case,
            "window_start_prev_d1_close": window_start,
            "window_end_target_d1_close": target,
            "n_events_in_window_all_tf": len(window_events),
            "n_events_relevant_state_changing": len(relevant_sorted),
            "timeline": relevant_sorted,
            "effetto_su_evento_canonico_successivo":
                f"la chiusura D1 target ({target}, lato {side}) e' l'evento canonico influenzato da "
                f"qualunque mutazione non canonica presente nella timeline sopra - vedi op_{side} "
                f"dell'ultimo evento non-D1 prima del target",
        })

    payload = {
        "method": "ri-esecuzione di Stream A con logging esaustivo (ogni passaggio, non solo D1), "
                 "poi estrazione della sotto-timeline fra la chiusura D1 precedente e quella target "
                 "per i casi scelti da ab_simulation_v1.json (only_in_a/only_in_b)",
        "noisy_ops_filtered_from_timeline_for_readability": sorted(NOISY_OPS),
        "cases": case_traces,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE713_DIR, "state_mutation_trace_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    for c in payload["cases"]:
        if "error" in c:
            print(f"  CASO {c['kind']} @ {c['target_close_time']}: ERRORE {c['error']}")
        else:
            print(f"  CASO {c['kind']} @ {c['target_close_time']} (lato {c['side']}): "
                  f"{c['n_events_relevant_state_changing']} eventi rilevanti su {c['n_events_in_window_all_tf']} totali nella finestra")


if __name__ == "__main__":
    main()
