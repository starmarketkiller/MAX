#!/usr/bin/env python3
"""Phase 7.1 - Calcolo statistico di un candidato RECLAIM (BOTH/BUY/SELL)
su UNO split, usando Baseline Engine v4 (reale) + le funzioni di
outcome/probabilita' GIA' validate e riusate da Phase 5/H006
(atr_outcome_for_bar, wl_censored, probability_record, wilson_ci95) -
nessuna reimplementazione della matematica di base, solo il layer di
matching sostituito con l'engine v2.

Convenzione IDENTICA a H006 (Phase 6): il baseline non e' "l'altra
direzione osservata" - e' "cosa sarebbe successo prendendo la STESSA
direzione dell'evento su barre di controllo comparabili" (hypothetical
direction). Per questo ogni controllo e' valutato con
atr_outcome_for_bar(control_row, EVENT_direction, ...), e nel filtro
direction-aware di BaselineEngineV4 control_direction_by_id e' sempre
= event_direction (nessun controllo viene scartato per "direzione
sbagliata" - la direzione e' incorporata nel calcolo dell'outcome, non
nella selezione del controllo).
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase5"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_1"))

from edge_discovery import atr_outcome_for_bar  # noqa: E402
from stats_utils import probability_record, wilson_ci95  # noqa: E402
from baseline_engine_v4 import BaselineEngineV4  # noqa: E402
from dependence_diagnostics_v2 import compare_event_vs_episode_view  # noqa: E402
from cross_split_safety import assign_split  # noqa: E402

THRESHOLD_KEY = "outcome_1.0"
HORIZON = 40
CATEGORICAL_DIMS = ["volatility_state", "trend_state"]
NN_DIMS = ["directional_efficiency", "position_in_rolling_range", "roc"]


def categorize(value, low, high):
    if value <= low:
        return "LOW"
    if value > high:
        return "HIGH"
    return "MED"


def wl_censored(outcomes, key):
    wins = sum(1 for o in outcomes if o[key] == "TARGET_FIRST")
    losses = sum(1 for o in outcomes if o[key] == "STOP_FIRST")
    censored = sum(1 for o in outcomes if o[key] == "CENSORED")
    return wins, losses, censored


def mean_mfe(outcomes):
    return float(np.mean([o["mfe_ATR"] for o in outcomes])) if outcomes else None


def build_feature_row(state_row, frozen_params):
    vol_low = frozen_params["categorical_terciles"]["volatility_state"]["low_boundary"]
    vol_high = frozen_params["categorical_terciles"]["volatility_state"]["high_boundary"]
    trend_low = frozen_params["categorical_terciles"]["trend_state"]["low_boundary"]
    trend_high = frozen_params["categorical_terciles"]["trend_state"]["high_boundary"]
    return {
        "volatility_state": categorize(state_row["atr_percentile"], vol_low, vol_high),
        "trend_state": categorize(state_row["ema_slope_atr_norm"], trend_low, trend_high),
        "directional_efficiency": state_row["directional_efficiency"],
        "position_in_rolling_range": state_row["position_in_rolling_range"],
        "roc": state_row["roc"],
    }


def compute_candidate_stats(split_name, direction_filter, events_df, state_df, df, atr_col,
                             frozen_params, split_boundaries_idx, excluded_from_baseline,
                             materiality_threshold=0.15):
    """direction_filter: 'BOTH' | 'BUY' | 'SELL'. Ritorna un dict completo
    con event/baseline probability, DeltaP, CI, dependence diagnostics,
    match quality, pronto per le gate."""
    engine = BaselineEngineV4(match_dimensions=CATEGORICAL_DIMS + NN_DIMS, k=frozen_params["k"],
                               split_boundaries=split_boundaries_idx, minimum_control_count=20)
    engine._norm_params = {f: (frozen_params["nn_standardization"][f]["mean"], frozen_params["nn_standardization"][f]["std"])
                            for f in NN_DIMS}

    reclaim = events_df[events_df["event_family"] == "RECLAIM"].dropna(subset=["confirmed_at_row_index", "direction"]).copy()
    reclaim["confirmed_at_row_index"] = reclaim["confirmed_at_row_index"].astype(int)
    reclaim["direction"] = reclaim["direction"].astype(int)
    reclaim = reclaim[reclaim["confirmed_at_row_index"].apply(lambda i: assign_split(i, split_boundaries_idx) == split_name)]
    if direction_filter == "BUY":
        reclaim = reclaim[reclaim["direction"] == 1]
    elif direction_filter == "SELL":
        reclaim = reclaim[reclaim["direction"] == -1]

    control_pool_all = [i for i in state_df.index
                         if assign_split(i, split_boundaries_idx) == split_name
                         and i not in excluded_from_baseline]

    event_outcomes, event_rows, event_dirs, event_outcome_by_row = [], [], {}, {}
    match_records = []
    baseline_outcomes_all = []

    for _, ev in reclaim.iterrows():
        row_idx = int(ev["confirmed_at_row_index"])
        direction = int(ev["direction"])
        o = atr_outcome_for_bar(row_idx, direction, df, atr_col, horizon=HORIZON)
        if o is None:
            continue
        event_outcomes.append(o)
        event_rows.append(row_idx)
        event_dirs[row_idx] = direction
        event_outcome_by_row[row_idx] = 1 if o[THRESHOLD_KEY] == "TARGET_FIRST" else 0

        if pd.isna(state_df.loc[row_idx, "atr_percentile"]) or pd.isna(state_df.loc[row_idx, "ema_slope_atr_norm"]):
            continue
        event_feat = build_feature_row(state_df.loc[row_idx], frozen_params)
        control_row_by_id = {c: c for c in control_pool_all}
        control_direction_by_id = {c: direction for c in control_pool_all}  # hypothetical direction, vedi docstring
        control_features_by_id = {}
        valid_controls = []
        for c in control_pool_all:
            row = state_df.loc[c]
            if pd.isna(row["atr_percentile"]) or pd.isna(row["ema_slope_atr_norm"]) or any(pd.isna(row[f]) for f in NN_DIMS):
                continue
            control_features_by_id[c] = build_feature_row(row, frozen_params)
            valid_controls.append(c)

        result = engine.match(f"RECLAIM-{row_idx}", row_idx, direction, event_feat,
                               valid_controls, control_row_by_id, control_direction_by_id, control_features_by_id)
        match_records.append(result)
        for m in result["matches"]:
            control_row = m["control_id"]
            bl_o = atr_outcome_for_bar(control_row, direction, df, atr_col, horizon=HORIZON)
            if bl_o:
                baseline_outcomes_all.append(bl_o)

    n_events = len(event_outcomes)
    ew, el, ec = wl_censored(event_outcomes, THRESHOLD_KEY)
    bw, bl_, bc = wl_censored(baseline_outcomes_all, THRESHOLD_KEY)
    event_prob = probability_record(ew, el, ec)
    baseline_prob = probability_record(bw, bl_, bc)
    delta_p = (event_prob["observed_p"] - baseline_prob["observed_p"]) if (event_prob["observed_p"] is not None and baseline_prob["observed_p"] is not None) else None
    delta_e = (mean_mfe(event_outcomes) - mean_mfe(baseline_outcomes_all)) if (event_outcomes and baseline_outcomes_all) else None
    ci_non_overlap = None
    if event_prob["wilson_ci95_low"] is not None and baseline_prob["wilson_ci95_high"] is not None:
        ci_non_overlap = event_prob["wilson_ci95_low"] > baseline_prob["wilson_ci95_high"]

    quality_counts = {"GOOD": 0, "FAIR": 0, "POOR": 0}
    controls_used_total, controls_available_list = 0, []
    n_rejected_insufficient_pool = 0
    for r in match_records:
        controls_available_list.append(r["controls_available"])
        controls_used_total += r["controls_used"]
        if r["status"] == "REJECTED_INSUFFICIENT_POOL":
            n_rejected_insufficient_pool += 1
        for m in r["matches"]:
            quality_counts[m["match_quality"]] += 1

    dep_result = None
    if event_rows:
        dep_result = compare_event_vs_episode_view(
            event_rows, event_dirs, event_outcome_by_row,
            materiality_threshold_delta_p=materiality_threshold,
            baseline_p_func=lambda rows, dirs: baseline_prob["observed_p"],
        )

    return {
        "split": split_name, "direction_filter": direction_filter,
        "n_events": n_events, "n_baseline_pool": len(baseline_outcomes_all),
        "n_rejected_insufficient_pool": n_rejected_insufficient_pool,
        "match_quality_counts": quality_counts,
        "controls_available_min": min(controls_available_list) if controls_available_list else 0,
        "controls_available_mean": (sum(controls_available_list) / len(controls_available_list)) if controls_available_list else 0,
        "event_probability": event_prob, "baseline_probability": baseline_prob,
        "delta_p": delta_p, "delta_e_mfe_atr": delta_e, "ci95_non_overlapping": ci_non_overlap,
        "dependence": dep_result,
        "event_outcomes": event_outcomes,
    }
