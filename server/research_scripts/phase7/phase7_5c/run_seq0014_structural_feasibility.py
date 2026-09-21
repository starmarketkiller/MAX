#!/usr/bin/env python3
"""Phase 7.5C - esegue il Sequence Structural Feasibility Gate su
SEQ-0014, usando ESCLUSIVAMENTE lo spec gia' congelato e committato in
seq0014_frozen_structural_spec_v1.json - NESSUN parametro e' scelto/
aggiustato qui guardando il risultato.

Outcome-blind: legge SOLO market_state_dataset_p71.csv (feature
CAUSAL_SAFE) - MAI outcomes_v1.csv ne' alcun file di outcome. Solo la
partition development_discovery.

Diagnostica esplicita richiesta (sec.11 della review): raw positive-
state bars -> state episodes (corse contigue) -> state-entry events,
per verificare che la persistenza di regime non sia stata trasformata
in sample size artificiale."""
import os
import statistics
import sys

import pandas as pd

PHASE75C_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE75C_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE75C_DIR, "..", "..", "..", ".."))
PHASE71_DATA = os.path.join(PHASE7_DIR, "phase7_1", "data")

sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_5"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
sys.path.insert(0, PHASE75C_DIR)
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402
from dependence_diagnostics import assign_clusters  # noqa: E402
from sequence_structural_feasibility_gate import evaluate_family_structural_feasibility, ENGINE_VERSION  # noqa: E402
from seq0014_state_entry_detector import compute_in_state, compute_state_entry_rows, compute_state_durations  # noqa: E402

STATE_PATH = os.path.join(PHASE71_DATA, "market_state_dataset_p71.csv")


def bucket_tercile(value, cutpoints):
    if value <= cutpoints["q1_low_med"]:
        return "LOW"
    if value <= cutpoints["q2_med_high"]:
        return "MED"
    return "HIGH"


def main():
    frozen = load_json(os.path.join(PHASE75C_DIR, "seq0014_frozen_structural_spec_v1.json"))["payload"]
    ms_frozen = frozen["matching_spec"]
    discovery_start, discovery_end = ms_frozen["split_boundaries"]["discovery"]
    exclusion_buffer_bars = frozen["proposed_natural_horizon"]
    episode_gap_rule = frozen["episode_gap_rule"]
    discovery_rows = list(range(discovery_start, discovery_end))

    state = pd.read_csv(STATE_PATH, parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)

    # ---- state -> state-entry events, SOLO su development_discovery ----
    de_cutpoints = frozen["state_definition"]["tercile_cutpoints_fit_on_discovery_only"]
    de_by_row = {r: float(state["directional_efficiency"].iloc[r]) for r in discovery_rows}
    in_state_by_row = compute_in_state(de_by_row, cutpoint_low_med=de_cutpoints["q1_low_med"])

    n_raw_positive_state_bars = sum(1 for v in in_state_by_row.values() if v)
    state_durations = compute_state_durations(in_state_by_row)
    event_row_indices = compute_state_entry_rows(in_state_by_row)
    n_state_episodes_contiguous_runs = len(state_durations)

    direction_by_row = {r: "BOTH" for r in event_row_indices}

    # ---- feature di stato per il matching (volatility_state_pre_entry), CAUSAL_SAFE ----
    atr_pct_t_minus_1 = state["atr_percentile"].shift(1)
    vol_cutpoints = ms_frozen["state_feature_definitions"]["volatility_state_pre_entry"][
        "tercile_cutpoints_fit_on_discovery_only"]
    vol_state_by_row = {r: bucket_tercile(atr_pct_t_minus_1.iloc[r], vol_cutpoints) for r in discovery_rows}

    # ---- episodi (STESSA meccanica del gate: assign_clusters, episode_gap_rule) - per l'esclusione di controllo ----
    clusters, _ = assign_clusters(event_row_indices, episode_gap_rule)
    episode_of_row = {r: cid for cid, members in enumerate(clusters) for r in members}

    def control_pool_for(t):
        same_episode = set(clusters[episode_of_row[t]])
        excluded = same_episode | {r for r in discovery_rows if abs(r - t) <= exclusion_buffer_bars}
        return [r for r in discovery_rows if r not in excluded]

    control_pool_by_event_row = {t: control_pool_for(t) for t in event_row_indices}
    control_row_by_id = {r: r for r in discovery_rows}
    control_features_by_id = {r: {"volatility_state_pre_entry": vol_state_by_row[r]} for r in discovery_rows}
    discovery_features_by_row = dict(control_features_by_id)
    event_features_by_row = {r: {"volatility_state_pre_entry": vol_state_by_row[r]} for r in event_row_indices}

    matching_spec = dict(ms_frozen)
    matching_spec["split_boundaries"] = {name: tuple(v) for name, v in ms_frozen["split_boundaries"].items()}

    spec = {
        "sequence_family_id": frozen["sequence_family_id"],
        "detector_frozen": frozen["detector_frozen"],
        "detector_source_ref": frozen["detector_source_ref"],
        "detector_parameters": frozen["detector_provenance"]["parameters"],
        "observation_timing": frozen["observation_timing"],
        "event_direction_policy": frozen["event_direction_policy"],
        "direction_by_row": direction_by_row,
        "episode_gap_rule": frozen["episode_gap_rule"],
        "overlap_policy": frozen["overlap_policy"],
        "proposed_natural_horizon": frozen["proposed_natural_horizon"],
        "proposed_outcome_overlap_embargo_bars": frozen["proposed_outcome_overlap_embargo_bars"],
        "discovery_partition": frozen["discovery_partition"],
        "minimum_evidence_gates": frozen["minimum_evidence_gates"],
        "event_row_indices": event_row_indices,
        "matching_spec": matching_spec,
        "matching_runtime_data": {
            "control_pool": discovery_rows,  # fallback non usato (control_pool_by_event_row ha precedenza)
            "control_pool_by_event_row": control_pool_by_event_row,
            "control_row_by_id": control_row_by_id,
            "control_features_by_id": control_features_by_id,
            "discovery_features_by_row": discovery_features_by_row,
            "event_features_by_row": event_features_by_row,
        },
    }

    result = evaluate_family_structural_feasibility(spec)

    payload = {
        "sequence_family_id": frozen["sequence_family_id"],
        "sequence_ids": frozen["sequence_ids"],
        "frozen_spec_ref": "server/research_scripts/phase7/phase7_5c/seq0014_frozen_structural_spec_v1.json",
        "engine_version": ENGINE_VERSION,
        "no_nexus_outcome_data_accessed": True,
        "no_edge_discovery_performed": True,
        "no_parameter_adjusted_after_seeing_this_result": True,
        "data_provenance": {
            "state_file": "server/research_scripts/phase7/phase7_1/data/market_state_dataset_p71.csv",
            "discovery_row_range": [discovery_start, discovery_end],
        },
        "state_to_event_diagnostic": {
            "description": "raw positive-state bars -> state episodes (corse contigue) -> state-entry events "
                            "- verifica che la persistenza di regime non sia stata trasformata in sample "
                            "size artificiale (sec.11 della richiesta Phase 7.5C).",
            "n_raw_positive_state_bars": n_raw_positive_state_bars,
            "firing_rate_of_state_bars_in_discovery": n_raw_positive_state_bars / len(discovery_rows),
            "n_state_episodes_contiguous_runs": n_state_episodes_contiguous_runs,
            "n_state_entry_events_used": len(event_row_indices),
            "state_duration_bars": {
                "mean": statistics.mean(state_durations) if state_durations else None,
                "median": statistics.median(state_durations) if state_durations else None,
                "min": min(state_durations) if state_durations else None,
                "max": max(state_durations) if state_durations else None,
            },
            "note": "n_state_episodes_contiguous_runs (corse contigue di in_state=True) e "
                    "n_state_entry_events_used (0->1 transitions, identico per costruzione a "
                    "n_state_episodes_contiguous_runs) contano la STESSA cosa da due prospettive - la vera "
                    "domanda e' quante di queste entrate sono ANCORA raggruppate insieme da episode_gap_rule "
                    "(EPISODE_VIEW nel funnel) e quante restano indipendenti dopo l'embargo (INDEPENDENT_VIEW).",
        },
        "gate_result": result,
    }
    out_path = os.path.join(PHASE75C_DIR, "seq0014_structural_feasibility_result_v1.json")
    save_json(out_path, wrap_with_provenance(payload, "phase7/phase7_5c/run_seq0014_structural_feasibility.py"))
    print(f"Scritto {out_path}")
    print(f"n_raw_positive_state_bars={n_raw_positive_state_bars} "
          f"(firing_rate={n_raw_positive_state_bars / len(discovery_rows):.3f})")
    print(f"n_state_entry_events (== state episodes contigue)={len(event_row_indices)}")
    print(f"state_duration_bars: mean={payload['state_to_event_diagnostic']['state_duration_bars']['mean']}, "
          f"median={payload['state_to_event_diagnostic']['state_duration_bars']['median']}")
    print(f"EVENT_VIEW={result['detection_funnel']['EVENT_VIEW']['n']} "
          f"-> EPISODE_VIEW={result['detection_funnel']['EPISODE_VIEW']['n']} "
          f"-> INDEPENDENT_VIEW={result['detection_funnel']['INDEPENDENT_VIEW']['n']}")
    print(f"geometry_verdict={result['geometry_verdict']}")
    print(f"matching.status={result['matching'].get('status')}")
    print(f"FINAL VERDICT={result['verdict']}")


if __name__ == "__main__":
    main()
