#!/usr/bin/env python3
"""Phase 7.21 punto 5 - execution realism: signal -> order -> fill ->
exit, quanto l'esecuzione degrada l'edge teorico. Blocked e broker
reject NON spariscono - riportati esplicitamente a ogni stadio.

Tre livelli, metrica consistente (fwd_return_60d1 direction-adjusted,
in price units = $ a lotto fisso 0.01) per i primi due, $ NETTO REALE
per l'ultimo (unico stadio con P&L vero):
- SIGNAL_EDGE: tutti i 67 segnali generati dal trace live (population_
  source=LIVE_TRACE_GENERATED) - ESCLUSI gli 8 OFFLINE_ISOLATED_
  RECONSTRUCTION_ONLY (mai generati dall'EA live, categoria di
  riconciliazione separata gia' documentata in Phase 7.9H, non un vero
  segnale eseguibile).
- EXECUTABLE_EDGE: solo i 56 che hanno superato gli execution gates
  (avrebbero potuto essere inviati all'ordine).
- REALIZED_EDGE: i 47 realmente riempiti (net P&L reale)."""
import os
import statistics
import sys

PHASE721_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE721_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE721_DIR)
from nxs_breakoutacc_dataset_loader import load_all_events, net_pnl  # noqa: E402

HORIZON = "fwd_return_60d1_price_units"


def _direction_adjusted_return(e, measurement_key="measurement_A_post_signal_path"):
    m = e.get(measurement_key)
    if not m or m.get("status") != "FULL_COVERAGE":
        return None
    raw = m["horizons"][HORIZON]
    return raw * e["direction"]  # positivo = movimento a favore della direzione del segnale


def build():
    events, _ = load_all_events()

    live_generated = [e for e in events if e["population_source"] == "LIVE_TRACE_GENERATED"]
    offline_only = [e for e in events if e["population_source"] == "OFFLINE_ISOLATED_RECONSTRUCTION_ONLY"]
    executable = [e for e in live_generated if e["execution_gates_stage"] == "PASS"]
    blocked = [e for e in live_generated if e["execution_gates_stage"] == "BLOCKED"]
    sent = [e for e in live_generated if e["order_stage"] == "SENT"]
    rejected = [e for e in live_generated if e["order_stage"] == "SENT_REJECTED"]
    opened = [e for e in live_generated if e["funnel_terminal_stage"] == "OPENED"]

    def _summary(evs, key="measurement_A_post_signal_path"):
        vals = [v for v in (_direction_adjusted_return(e, key) for e in evs) if v is not None]
        return {"n": len(evs), "n_with_full_coverage": len(vals),
               "mean_direction_adjusted_fwd_return_60d1": statistics.mean(vals) if vals else None,
               "median": statistics.median(vals) if vals else None,
               "pct_favorable": (sum(1 for v in vals if v > 0) / len(vals)) if vals else None}

    signal_edge = _summary(live_generated)
    executable_edge = _summary(executable)
    realized_nets = [net_pnl(e) for e in opened]
    realized_edge = {"n": len(opened), "mean_net_usd_at_0_01_lot": statistics.mean(realized_nets),
                     "total_net_usd": sum(realized_nets),
                     "pct_favorable_win_rate": sum(1 for p in realized_nets if p > 0) / len(opened)}

    payload = {
        "funnel_counts": {
            "raw_acceptance_events_total_75": 75,
            "offline_reconstruction_only_excluded_from_this_analysis_8":
                "population_source=OFFLINE_ISOLATED_RECONSTRUCTION_ONLY - mai generati dal trace EA "
                "live, categoria di riconciliazione separata (Phase 7.9H) - riportati qui ma non "
                "usati nella catena signal->order->fill (non hanno un signal_id reale).",
            "live_trace_generated_67": len(live_generated),
            "blocked_by_execution_gates_11": len(blocked),
            "executable_passed_gates_56": len(executable),
            "order_sent_47_plus_rejected_9": {"sent_and_filled": len(sent), "sent_rejected": len(rejected)},
            "opened_with_real_pnl_47": len(opened),
        },
        "blocked_and_rejected_not_dropped": {
            "blocked_events_direction_adjusted_signal_quality": _summary(blocked),
            "rejected_events_direction_adjusted_signal_quality": _summary(rejected),
            "note": "Il segnale sottostante di blocked/rejected NON e' sistematicamente peggiore di "
                   "quello eseguito (confronta pct_favorable qui con signal_edge sotto) - i gate "
                   "execution/broker non sembrano selezionare per qualita' del segnale, sono "
                   "vincoli operativi (posizione gia' aperta, protezioni, rifiuto broker).",
        },
        "signal_edge": {**signal_edge, "definition": "Tutti i 67 segnali generati dal trace EA live, "
                       "movimento forward a 60 barre D1 aggiustato per direzione (price units = $ a "
                       "lotto fisso 0.01) - edge TEORICO se ogni segnale fosse tradeable senza "
                       "nessun gate/esecuzione."},
        "executable_edge": {**executable_edge, "definition": "Solo i 56 segnali che hanno superato "
                            "gli execution gates - edge teorico SE ogni ordine inviato fosse sempre "
                            "riempito senza rifiuti broker."},
        "realized_edge": {**realized_edge, "definition": "I 47 realmente riempiti - P&L netto REALE "
                          "(non un proxy di movimento prezzo) - l'unico numero economicamente vero."},
        "degradation_note": "signal_edge ed executable_edge usano un PROXY di movimento prezzo "
                            "(non $ P&L reale, nessun SL/TP applicato) - NON direttamente comparabili "
                            "in valore assoluto a realized_edge (che e' $ P&L reale con SL/TP reali). "
                            "Il confronto valido e' qualitativo: se pct_favorable cala forte da "
                            "signal a executable, i gate stanno scartando segnali buoni; se resta "
                            "stabile, i gate sono operativi/neutrali - qui resta stabile.",
        "known_execution_simplification": "Zero slippage segnale->fill osservato su TUTTI i 47 "
            "eventi (vedi cost_stress_v1.json) - artefatto noto del motore Strategy Tester in "
            "Research Mode, non evidenza che l'esecuzione reale sarebbe priva di slippage.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE721_DIR, "execution_realism_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  signal_edge pct_favorable: {payload['signal_edge']['pct_favorable']:.2f}")
    print(f"  executable_edge pct_favorable: {payload['executable_edge']['pct_favorable']:.2f}")
    print(f"  realized_edge win_rate: {payload['realized_edge']['pct_favorable_win_rate']:.2f}")


if __name__ == "__main__":
    main()
