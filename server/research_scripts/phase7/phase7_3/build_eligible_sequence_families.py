#!/usr/bin/env python3
"""Phase 7.3 sec.1 - Inventario deterministico delle sequence idonee a
essere formalizzate come prima family tecnica del Sequence Discovery
Engine v1. Criteri (dichiarati PRIMA di guardare qualunque performance,
non ce n'e' comunque nessuna in questa fase):

  READY_FOR_FORMALIZATION + causal-safe (OBSERVABLE_AT_DECISION_TIME) +
  implementabile con dati H4 gia' disponibili (nessun TRIGGER_TF piu'
  fine di H4, nessun note_gap) + non DIRECT_REPEAT_OF_FAILED_IDEA +
  semantic_leakage_status_after_correction == PASS.

Nessuna selezione per performance - questa fase produce l'INVENTARIO,
non la scelta finale di UNA family per una futura discovery reale."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PHASE7_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7")
PHASE73_DIR = os.path.join(PHASE7_DIR, "phase7_3")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

EXISTING_PHASE5_DETECTORS = {
    "MECH-06": "BREAKOUT (build_events.py, esistente)", "MECH-07": "BREAKOUT (condizionale, stesso detector)",
    "MECH-08": "FAILED_BREAKOUT (build_events.py, esistente)",
    "MECH-18": "SWEEP (build_events.py, esistente)", "MECH-19": "SWEEP+RECLAIM (build_events.py, esistente)",
    "MECH-20": "SWEEP (build_events.py, esistente, assenza di RECLAIM)",
}

FEATURE_DEPS = {
    "SEQ-0001": ["directional_efficiency"],
    "SEQ-0009": ["atr", "dist_from_rolling_high_atr", "dist_from_rolling_low_atr", "dist_from_prev_day_high_atr", "dist_from_prev_day_low_atr", "dist_from_prev_week_high_atr", "dist_from_prev_week_low_atr"],
    "SEQ-0014": ["directional_efficiency", "atr_percentile o variance_ratio_proxy (rapporto vol/deriva)"],
    "SEQ-0015": ["atr", "close/open/high/low (true range barra)"],
    "SEQ-0016": ["atr (banda di volatilita' - proxy da definire, es. multiplo di ATR)", "trend_state derivato"],
    "SEQ-0020": ["ema_slope_raw o feature equivalenti a media mobile corta/lunga sul midpoint"],
}


def main():
    seq_doc = json.load(open(os.path.join(PHASE7_DIR, "phase7_2", "market_sequence_registry_v1.json"), encoding="utf-8"))
    sequences = seq_doc["sequences"]

    entries = []
    for s in sequences:
        sid = s["sequence_id"]
        blocking_gaps = []
        if s["implementation_status"] != "READY_FOR_FORMALIZATION":
            blocking_gaps.append(f"implementation_status={s['implementation_status']}")
        if s["causal_observability_status"] != "OBSERVABLE_AT_DECISION_TIME":
            blocking_gaps.append(f"causal_observability_status={s['causal_observability_status']}")
        trigger_tf = (s.get("timeframe_context") or {}).get("TRIGGER_TF")
        if trigger_tf:
            blocking_gaps.append(f"richiede TRIGGER_TF piu' fine di H4: {trigger_tf}")
        if "note_gap" in s:
            blocking_gaps.append(f"note_gap: {s['note_gap']}")
        if s["failure_memory_relation"] == "DIRECT_REPEAT_OF_FAILED_IDEA":
            blocking_gaps.append("failure_memory_relation=DIRECT_REPEAT_OF_FAILED_IDEA")
        if s.get("semantic_leakage_status_after_correction") != "PASS":
            blocking_gaps.append(f"semantic_leakage_status_after_correction={s.get('semantic_leakage_status_after_correction')}")

        eligible = len(blocking_gaps) == 0
        detector_feasibility = "HIGH (detector Phase 5 gia' esistente)" if s["mechanism_id"] in EXISTING_PHASE5_DETECTORS else \
            "MEDIUM (derivabile da feature/OHLC esistenti, nuovo detector da scrivere)"

        entries.append({
            "sequence_id": sid,
            "mechanism_id": s["mechanism_id"],
            "eligible_for_first_technical_family": eligible,
            "readiness_status": s["implementation_status"],
            "blocking_gaps": blocking_gaps,
            "detector_feasibility": detector_feasibility,
            "existing_detector_reference": EXISTING_PHASE5_DETECTORS.get(s["mechanism_id"]),
            "feature_dependencies": FEATURE_DEPS.get(sid, ["da determinare in fase di formalizzazione"]),
            "causal_safety": s["causal_observability_status"],
            "leakage_status": s.get("semantic_leakage_status_after_correction"),
            "failure_memory_relation": s["failure_memory_relation"],
        })

    eligible_entries = [e for e in entries if e["eligible_for_first_technical_family"]]

    payload = {
        "criteria": ["READY_FOR_FORMALIZATION", "causal_observability_status=OBSERVABLE_AT_DECISION_TIME",
                     "nessun TRIGGER_TF piu' fine di H4", "nessun note_gap (VWAP/session/calendar/multi-asset)",
                     "failure_memory_relation != DIRECT_REPEAT_OF_FAILED_IDEA",
                     "semantic_leakage_status_after_correction == PASS"],
        "n_sequences_total": len(entries),
        "n_eligible": len(eligible_entries),
        "eligible_sequence_ids": [e["sequence_id"] for e in eligible_entries],
        "all_sequences": entries,
        "note": "Inventario, non selezione - nessuna sequence e' scelta come 'la prima family' in questo artifact. "
                "SEQ-0009 e' eligible per i criteri LETTERALI sopra ma ha failure_memory_relation=RELATED_TO_PREVIOUS_FAILURE "
                "(componente della famiglia SWEEP/RECLAIM) - inclusa con questa relazione visibile, non esclusa arbitrariamente.",
    }
    save_json(os.path.join(PHASE73_DIR, "phase7_3_eligible_sequence_families_v1.json"), wrap_with_provenance(payload, "phase7/phase7_3/build_eligible_sequence_families.py"))
    print(f"n_eligible={len(eligible_entries)}/{len(entries)}: {[e['sequence_id'] for e in eligible_entries]}")
    for e in eligible_entries:
        print(f"  {e['sequence_id']} ({e['mechanism_id']}) - {e['failure_memory_relation']} - detector: {e['detector_feasibility']}")


if __name__ == "__main__":
    main()
