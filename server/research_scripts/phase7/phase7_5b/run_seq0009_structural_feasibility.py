#!/usr/bin/env python3
"""Phase 7.5B - esegue il Sequence Structural Feasibility Gate (Phase
7.5A) su SEQ-0009, usando ESCLUSIVAMENTE lo spec gia' congelato e
committato in seq0009_frozen_structural_spec_v1.json - NESSUN
parametro e' scelto/aggiustato qui guardando il risultato.

Outcome-blind: legge SOLO xauusd_h4_bars_p71.csv (OHLC) e
market_state_dataset_p71.csv (feature CAUSAL_SAFE) - MAI outcomes_v1.csv
ne' alcun file di outcome. Solo la partition development_discovery."""
import os
import sys

import pandas as pd

PHASE75B_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE75B_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE75B_DIR, "..", "..", "..", ".."))
PHASE71_DATA = os.path.join(PHASE7_DIR, "phase7_1", "data")

sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_5"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402
from dependence_diagnostics import assign_clusters  # noqa: E402
from sequence_structural_feasibility_gate import evaluate_family_structural_feasibility, ENGINE_VERSION  # noqa: E402

EVENTS_PATH = os.path.join(PHASE71_DATA, "events_p71.csv")
STATE_PATH = os.path.join(PHASE71_DATA, "market_state_dataset_p71.csv")
SWEPT_SIDE_TO_DIRECTION = {"HIGH": "SELL", "LOW": "BUY"}


def bucket_tercile(value, cutpoints):
    if value <= cutpoints["q1_low_med"]:
        return "LOW"
    if value <= cutpoints["q2_med_high"]:
        return "MED"
    return "HIGH"


def main():
    frozen = load_json(os.path.join(PHASE75B_DIR, "seq0009_frozen_structural_spec_v1.json"))["payload"]
    ms_frozen = frozen["matching_spec"]
    discovery_start, discovery_end = ms_frozen["split_boundaries"]["discovery"]
    exclusion_buffer_bars = frozen["proposed_natural_horizon"]
    episode_gap_rule = frozen["episode_gap_rule"]

    # ---- eventi grezzi (row_index/direction), SOLO struttura, MAI outcome ----
    ev = pd.read_csv(EVENTS_PATH)
    sweep = ev[ev["event_family"] == "SWEEP"]
    sweep_discovery = sweep[(sweep["row_index"] >= discovery_start) & (sweep["row_index"] < discovery_end)]

    dup_rows = set(sweep_discovery["row_index"][sweep_discovery["row_index"].duplicated(keep=False)])
    kept = sweep_discovery[~sweep_discovery["row_index"].isin(dup_rows)]
    n_excluded_ambiguous = sweep_discovery["row_index"].isin(dup_rows).sum()

    event_row_indices = sorted(int(r) for r in kept["row_index"].unique())
    direction_by_row = {int(row["row_index"]): SWEPT_SIDE_TO_DIRECTION[row["swept_side"]]
                         for _, row in kept.iterrows()}

    # ---- feature di stato (volatility_state_pre_event), CAUSAL_SAFE, SOLO market_state ----
    state = pd.read_csv(STATE_PATH, parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    atr_pct_t_minus_1 = state["atr_percentile"].shift(1)
    cutpoints = frozen["matching_spec"]["state_feature_definitions"]["volatility_state_pre_event"][
        "tercile_cutpoints_fit_on_discovery_only"]

    discovery_rows = list(range(discovery_start, discovery_end))
    vol_state_by_row = {r: bucket_tercile(atr_pct_t_minus_1.iloc[r], cutpoints) for r in discovery_rows}

    # ---- episodi (STESSA meccanica del gate: assign_clusters, episode_gap_rule) - per l'esclusione di controllo ----
    clusters, _ = assign_clusters(event_row_indices, episode_gap_rule)
    episode_of_row = {r: cid for cid, members in enumerate(clusters) for r in members}

    def control_pool_for(t):
        same_episode = set(clusters[episode_of_row[t]])
        excluded = same_episode | {r for r in discovery_rows if abs(r - t) <= exclusion_buffer_bars}
        return [r for r in discovery_rows if r not in excluded]

    control_pool_by_event_row = {t: control_pool_for(t) for t in event_row_indices}
    control_row_by_id = {r: r for r in discovery_rows}
    control_features_by_id = {r: {"volatility_state_pre_event": vol_state_by_row[r]} for r in discovery_rows}
    discovery_features_by_row = dict(control_features_by_id)
    event_features_by_row = {r: {"volatility_state_pre_event": vol_state_by_row[r]} for r in event_row_indices}

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
        "frozen_spec_ref": "server/research_scripts/phase7/phase7_5b/seq0009_frozen_structural_spec_v1.json",
        "engine_version": ENGINE_VERSION,
        "no_nexus_outcome_data_accessed": True,
        "no_edge_discovery_performed": True,
        "no_parameter_adjusted_after_seeing_this_result": True,
        "data_provenance": {
            "bars_file": "server/research_scripts/phase7/phase7_1/data/xauusd_h4_bars_p71.csv",
            "state_file": "server/research_scripts/phase7/phase7_1/data/market_state_dataset_p71.csv",
            "events_file": "server/research_scripts/phase7/phase7_1/data/events_p71.csv",
            "discovery_row_range": [discovery_start, discovery_end],
        },
        "raw_sweep_events_in_discovery": {
            "n_total_raw_including_ambiguous": int(len(sweep_discovery)),
            "n_ambiguous_double_sweep_excluded": int(n_excluded_ambiguous),
            "n_used": len(event_row_indices),
            "n_high_swept_sell": sum(1 for d in direction_by_row.values() if d == "SELL"),
            "n_low_swept_buy": sum(1 for d in direction_by_row.values() if d == "BUY"),
        },
        "gate_result": result,
    }
    out_path = os.path.join(PHASE75B_DIR, "seq0009_structural_feasibility_result_v1.json")
    save_json(out_path, wrap_with_provenance(payload, "phase7/phase7_5b/run_seq0009_structural_feasibility.py"))
    print(f"Scritto {out_path}")
    print(f"n raw SWEEP in discovery (post esclusione ambigui): {len(event_row_indices)}")
    print(f"EVENT_VIEW={result['detection_funnel']['EVENT_VIEW']['n']} "
          f"-> EPISODE_VIEW={result['detection_funnel']['EPISODE_VIEW']['n']} "
          f"-> INDEPENDENT_VIEW={result['detection_funnel']['INDEPENDENT_VIEW']['n']}")
    print(f"geometry_verdict={result['geometry_verdict']}")
    print(f"matching.status={result['matching'].get('status')}")
    print(f"FINAL VERDICT={result['verdict']}")


if __name__ == "__main__":
    main()
