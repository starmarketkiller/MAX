#!/usr/bin/env python3
"""Phase 6.5 sec.4 - Directional Baseline Engine v3.

Fix del limite trovato in Phase 6: il confronto BUY/SELL usava un
baseline AGGREGATO (che mescolava osservazioni di controllo valutate
come ipotetico BUY e come ipotetico SELL) come termine di paragone per
entrambi i lati. Qui la direzione diventa parte del CONTRATTO di
matching fin dall'inizio: un evento BUY viene confrontato SOLO con
barre di controllo valutate come ipotetico BUY (stesso matching
coarsened+NN, stessa normalizzazione congelata di Phase 6), e
simmetricamente per SELL.

Riusa la stessa logica di matching di run_h006_test.py (import diretto,
nessuna riscrittura) - qui viene solo cambiata l'AGGREGAZIONE finale
per mantenere i pool di baseline separati per direzione invece di
fonderli.

Questo e' un AUDIT RETROATTIVO su H006 (Phase 6.5 sec.8): non cambia
il verdetto di Phase 6, non promuove SELL, non assegna E3.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = r"C:\Users\User\ClaudeWork\MAX"
PHASE5_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5")
PHASE55_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5_5")
PHASE6_DIR = os.path.join(ROOT, "server", "research_scripts", "phase6")
PHASE65_DIR = os.path.join(ROOT, "server", "research_scripts", "phase6_5")
DATA_DIR = os.path.join(PHASE6_DIR, "data")

sys.path.insert(0, PHASE5_DIR)
sys.path.insert(0, PHASE55_DIR)
sys.path.insert(0, PHASE6_DIR)
from edge_discovery import atr_outcome_for_bar, wl_censored  # noqa: E402
from stats_utils import probability_record  # noqa: E402
from run_h006_test import coarsened_cell, HOLDOUT_START, HORIZON, PRIMARY_THRESHOLD  # noqa: E402

from block_bootstrap import iid_bootstrap_ci  # noqa: E402


def main():
    spec = json.load(open(os.path.join(PHASE6_DIR, "H006_frozen_spec.json"), encoding="utf-8"))
    params = json.load(open(os.path.join(PHASE6_DIR, "frozen_baseline_parameters.json"), encoding="utf-8"))
    vol_terc = params["vol_tercile_33_67"]
    trend_terc = params["trend_tercile_33_67"]
    match_features = params["nn_match_features"]
    means = params["nn_standardization_means"]
    stds = params["nn_standardization_stds"]

    df = pd.read_csv(os.path.join(DATA_DIR, "xauusd_h4_bars_holdout.csv"), parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    state = pd.read_csv(os.path.join(DATA_DIR, "market_state_dataset_holdout.csv"), parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    events = pd.read_csv(os.path.join(DATA_DIR, "events_holdout.csv"))
    atr_col = state["atr"].values
    state["_year"] = state["bar_time_utc"].dt.year
    n = len(df)
    is_holdout = (df["bar_time_utc"] >= HOLDOUT_START).values

    reclaim = events[events.event_family == "RECLAIM"].copy()
    reclaim = reclaim.dropna(subset=["confirmed_at_row_index", "direction"])
    reclaim["confirmed_at_row_index"] = reclaim["confirmed_at_row_index"].astype(int)
    reclaim = reclaim[reclaim["confirmed_at_row_index"].apply(lambda i: is_holdout[i] if i < n else False)]
    reclaim_rows = list(zip(reclaim["confirmed_at_row_index"].astype(int), reclaim["direction"].astype(int)))

    sweep_rows = set(events.loc[events.event_family == "SWEEP", "row_index"].astype(int))
    reclaim_all_rows = set(events.loc[events.event_family == "RECLAIM", "row_index"].astype(int)) | \
        set(events.loc[events.event_family == "RECLAIM", "confirmed_at_row_index"].dropna().astype(int))
    excluded_from_baseline = sweep_rows | reclaim_all_rows

    cell_of_row = [coarsened_cell(state.iloc[i], vol_terc, trend_terc) if is_holdout[i] else None for i in range(n)]

    def standardized_features(i):
        z = []
        for f in match_features:
            v = state[f].iloc[i]
            if pd.isna(v):
                return None
            z.append((v - means[f]) / stds[f])
        return np.array(z)

    def nn_baseline_for_event(row_idx, direction, cell, k=5):
        candidates = []
        z_event = standardized_features(row_idx)
        if z_event is None:
            return [], []
        for j in range(n):
            if not is_holdout[j] or j in excluded_from_baseline:
                continue
            if cell_of_row[j] != cell:
                continue
            zj = standardized_features(j)
            if zj is None:
                continue
            dist = float(np.linalg.norm(z_event - zj))
            candidates.append((j, dist))
        candidates.sort(key=lambda x: x[1])
        nn = candidates[:k]
        outcomes = []
        for j, dist in nn:
            o = atr_outcome_for_bar(j, direction, df, atr_col, horizon=HORIZON)
            if o:
                o["_dist"] = dist
                o["_baseline_direction"] = direction  # per contratto: la baseline e' SEMPRE valutata nella direzione dell'evento che la matcha
                outcomes.append(o)
        return outcomes, [d for _, d in nn]

    threshold_key = f"outcome_{PRIMARY_THRESHOLD}"
    match_log = []
    pools = {1: {"event": [], "baseline": []}, -1: {"event": [], "baseline": []}}

    for row_idx, direction in reclaim_rows:
        o = atr_outcome_for_bar(row_idx, direction, df, atr_col, horizon=HORIZON)
        if o is None:
            continue
        cell = cell_of_row[row_idx]
        bl_outcomes, distances = ([], [])
        if cell is not None:
            bl_outcomes, distances = nn_baseline_for_event(row_idx, direction, cell)
        pools[direction]["event"].append(o)
        pools[direction]["baseline"].extend(bl_outcomes)
        avg_dist = float(np.mean(distances)) if distances else None
        quality = ("GOOD" if avg_dist < 0.5 else ("FAIR" if avg_dist < 1.0 else "POOR")) if avg_dist is not None else None
        match_log.append({
            "event_row": row_idx, "event_direction": direction,
            "baseline_direction": direction,  # contratto esplicito: mai mescolato
            "n_baseline_matched": len(distances), "avg_match_distance": avg_dist, "match_quality": quality,
        })

    def summarize(direction_label, direction_key):
        ev = pools[direction_key]["event"]
        bl = pools[direction_key]["baseline"]
        ew, el, ec = wl_censored(ev, threshold_key)
        bw, bl_, bc = wl_censored(bl, threshold_key)
        ev_prob = probability_record(ew, el, ec)
        bl_prob = probability_record(bw, bl_, bc)
        delta_p = (ev_prob["observed_p"] - bl_prob["observed_p"]) if (ev_prob["observed_p"] is not None and bl_prob["observed_p"] is not None) else None
        ci_non_overlap = None
        if ev_prob["wilson_ci95_low"] is not None and bl_prob["wilson_ci95_high"] is not None:
            ci_non_overlap = ev_prob["wilson_ci95_low"] > bl_prob["wilson_ci95_high"]
        return {
            "direction": direction_label, "n_events": len(ev), "n_baseline_pool": len(bl),
            "event_probability": ev_prob, "baseline_probability": bl_prob,
            "delta_p_directional": delta_p, "ci95_non_overlapping": ci_non_overlap,
        }

    buy_result = summarize("BUY", 1)
    sell_result = summarize("SELL", -1)

    match_quality_counts = pd.Series([m["match_quality"] for m in match_log if m["match_quality"]]).value_counts().to_dict()

    out = {
        "schema_version": 1,
        "scope": "METHODOLOGICAL_AUDIT_ONLY - retroactive audit of H006, does NOT change Phase 6 verdict, does NOT promote SELL, does NOT assign E3",
        "methodology": "direzione parte del contratto di matching - ogni evento confrontato SOLO con baseline valutata nella sua stessa direzione",
        "buy_directional": buy_result,
        "sell_directional": sell_result,
        "match_quality_distribution": match_quality_counts,
        "n_match_log_entries": len(match_log),
        "comparison_vs_phase6_aggregate_baseline_diagnostic": {
            "phase6_buy_delta_p_vs_aggregate_baseline": -0.0103,
            "phase6_sell_delta_p_vs_aggregate_baseline": 0.1389,
            "phase6_5_buy_delta_p_vs_directional_baseline": buy_result["delta_p_directional"],
            "phase6_5_sell_delta_p_vs_directional_baseline": sell_result["delta_p_directional"],
            "note": "se i baseline direzionali BUY e SELL hanno probabilita' di base diverse fra loro, il confronto Phase 6 (contro un baseline aggregato unico) puo' aver distorto la lettura dell'asimmetria - vedi report principale sec.5 per l'interpretazione",
        },
    }
    out_path = os.path.join(PHASE65_DIR, "h006_directional_baseline_v3.json")
    json.dump(out, open(out_path, "w", encoding="utf-8"), indent=2, default=str)
    print(json.dumps({k: v for k, v in out.items()}, indent=2, default=str))
    print(f"\nwritten: {out_path}")
    return out


if __name__ == "__main__":
    main()
