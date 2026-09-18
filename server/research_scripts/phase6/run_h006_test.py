#!/usr/bin/env python3
"""Phase 6 - H006 True Holdout Test.

Applica la definizione CONGELATA (H006_frozen_spec.json,
frozen_baseline_parameters.json, true_holdout_declaration.json - tutti
scritti PRIMA di guardare questo dataset) al periodo di holdout
2022-02-04..2023-02-03. Nessuna soglia ricalcolata qui: tutto quello
che serve a "cosa conta come stato simile" viene importato dai file
frozen, mai ridedotto dal holdout stesso.

Ordine di esecuzione (rispettato esattamente, come da vincolo esplicito
della fase): 1) risultato primario e verdetto PASS/BORDERLINE/FAIL
CONGELATI e stampati/salvati PRIMA di 2) qualunque diagnostica di
robustezza (BUY/SELL, regime, sottoperiodo, outlier trim, bootstrap,
clustering) - i diagnostici non possono retroattivamente cambiare il
verdetto.
"""
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = r"C:\Users\User\ClaudeWork\MAX"
PHASE5_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5")
PHASE55_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5_5")
PHASE6_DIR = os.path.join(ROOT, "server", "research_scripts", "phase6")
DATA_DIR = os.path.join(PHASE6_DIR, "data")

sys.path.insert(0, PHASE5_DIR)
sys.path.insert(0, PHASE55_DIR)
from edge_discovery import atr_outcome_for_bar, wl_censored, mean_mfe, outlier_robustness_check  # noqa: E402
from stats_utils import probability_record, wilson_ci95  # noqa: E402

HOLDOUT_START = datetime(2022, 2, 4, tzinfo=timezone.utc)
HORIZON = 40
PRIMARY_THRESHOLD = 1.0


def load_frozen():
    spec = json.load(open(os.path.join(PHASE6_DIR, "H006_frozen_spec.json"), encoding="utf-8"))
    params = json.load(open(os.path.join(PHASE6_DIR, "frozen_baseline_parameters.json"), encoding="utf-8"))
    return spec, params


def coarsened_cell(row, vol_terc, trend_terc):
    v, t = row["atr_percentile"], row["ema_slope_atr_norm"]
    if pd.isna(v) or pd.isna(t):
        return None
    vb = "LOW" if v <= vol_terc[0] else ("HIGH" if v > vol_terc[1] else "MED")
    tb = "DOWN" if t <= trend_terc[0] else ("UP" if t > trend_terc[1] else "FLAT")
    return (vb, tb, int(row["_year"]))


def main():
    spec, params = load_frozen()
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
    print(f"[H006] total bars={n} holdout_bars={is_holdout.sum()} buffer_bars={(~is_holdout).sum()}")

    # --- eventi RECLAIM, SOLO quelli confermati dentro il periodo di holdout ---
    reclaim = events[events.event_family == "RECLAIM"].copy()
    reclaim = reclaim.dropna(subset=["confirmed_at_row_index", "direction"])
    reclaim["confirmed_at_row_index"] = reclaim["confirmed_at_row_index"].astype(int)
    reclaim = reclaim[reclaim["confirmed_at_row_index"].apply(lambda i: is_holdout[i] if i < n else False)]
    reclaim_rows = list(zip(reclaim["confirmed_at_row_index"].astype(int), reclaim["direction"].astype(int)))
    print(f"[H006] RECLAIM events confirmed inside holdout window: {len(reclaim_rows)}")

    # righe escluse dal pool di baseline: qualunque barra che sia essa stessa
    # un evento SWEEP o RECLAIM (stessa regola di Phase 5), E fuori dal
    # periodo di holdout (il pool di controllo deve essere contemporaneo)
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
                outcomes.append(o)
        return outcomes, [d for _, d in nn]

    threshold_key = f"outcome_{PRIMARY_THRESHOLD}"
    event_outcomes = []
    baseline_outcomes_all = []
    match_records = []
    for row_idx, direction in reclaim_rows:
        o = atr_outcome_for_bar(row_idx, direction, df, atr_col, horizon=HORIZON)
        if o is None:
            continue
        o["_direction"] = direction
        o["_row"] = row_idx
        event_outcomes.append(o)

        cell = cell_of_row[row_idx]
        bl_outcomes, distances = ([], [])
        if cell is not None:
            bl_outcomes, distances = nn_baseline_for_event(row_idx, direction, cell)
        baseline_outcomes_all.extend(bl_outcomes)
        avg_dist = float(np.mean(distances)) if distances else None
        quality = None
        if avg_dist is not None:
            quality = "GOOD" if avg_dist < 0.5 else ("FAIR" if avg_dist < 1.0 else "POOR")
        match_records.append({
            "event_row": row_idx, "direction": direction, "cell": cell,
            "n_matched": len(distances), "avg_distance": avg_dist, "match_quality": quality,
        })

    n_events = len(event_outcomes)
    quality_counts = pd.Series([m["match_quality"] for m in match_records if m["match_quality"]]).value_counts().to_dict()

    # ================= PRIMARY RESULT (locked BEFORE robustness diagnostics) =================
    ew, el, ec = wl_censored(event_outcomes, threshold_key)
    bw, bl_, bc = wl_censored(baseline_outcomes_all, threshold_key)
    event_prob = probability_record(ew, el, ec)
    baseline_prob = probability_record(bw, bl_, bc)
    delta_p = (event_prob["observed_p"] - baseline_prob["observed_p"]) if (event_prob["observed_p"] is not None and baseline_prob["observed_p"] is not None) else None
    delta_e = (mean_mfe(event_outcomes) - mean_mfe(baseline_outcomes_all)) if (event_outcomes and baseline_outcomes_all) else None
    ci_non_overlap = None
    if event_prob["wilson_ci95_low"] is not None and baseline_prob["wilson_ci95_high"] is not None:
        ci_non_overlap = event_prob["wilson_ci95_low"] > baseline_prob["wilson_ci95_high"]

    # BUY/SELL per required_direction_consistency (confrontati contro lo
    # stesso baseline aggregato - il pool di baseline non e' separato per
    # lato in questa v1, coerente con come Phase 5 trattava BUY/SELL come
    # confronto contro lo stesso pool complessivo salvo dove esplicitamente
    # ripartito per direzione)
    buy_outcomes = [o for o in event_outcomes if o["_direction"] == 1]
    sell_outcomes = [o for o in event_outcomes if o["_direction"] == -1]
    baseline_p_overall = baseline_prob["observed_p"]

    def side_delta(outcomes):
        w, l, c = wl_censored(outcomes, threshold_key)
        pr = probability_record(w, l, c)
        dp = (pr["observed_p"] - baseline_p_overall) if (pr["observed_p"] is not None and baseline_p_overall is not None) else None
        return {"n": w + l, "observed_p": pr["observed_p"], "delta_p_vs_overall_baseline": dp, "prob_record": pr}

    buy_result = side_delta(buy_outcomes)
    sell_result = side_delta(sell_outcomes)

    direction_consistency_ok = None
    if delta_p is not None and buy_result["delta_p_vs_overall_baseline"] is not None and sell_result["delta_p_vs_overall_baseline"] is not None:
        agg_sign = delta_p > 0
        direction_consistency_ok = (buy_result["delta_p_vs_overall_baseline"] > 0) == agg_sign and \
                                    (sell_result["delta_p_vs_overall_baseline"] > 0) == agg_sign

    crit = spec["pass_fail_criteria_FROZEN"]
    min_effect = spec["minimum_material_effect"]["delta_p_minimum"]
    min_n = spec["minimum_sample"]["n_minimum"]

    if delta_p is None:
        verdict = "FAIL"
        verdict_reason = "delta_p non calcolabile (dati insufficienti)"
    elif delta_p <= 0:
        verdict = "FAIL"
        verdict_reason = f"DeltaP_holdout={delta_p:.4f} <= 0"
    elif delta_p >= min_effect and ci_non_overlap and n_events >= min_n and direction_consistency_ok:
        verdict = "PASS"
        verdict_reason = f"DeltaP={delta_p:.4f}>={min_effect}, CI non sovrapposte, n={n_events}>={min_n}, direzione consistente BUY/SELL"
    else:
        verdict = "BORDERLINE"
        reasons = []
        if delta_p < min_effect:
            reasons.append(f"DeltaP={delta_p:.4f}<{min_effect}")
        if n_events < min_n:
            reasons.append(f"n={n_events}<{min_n}")
        if not ci_non_overlap:
            reasons.append("CI95 sovrapposte")
        if not direction_consistency_ok:
            reasons.append("direzione BUY/SELL non pienamente consistente")
        verdict_reason = "; ".join(reasons)

    primary_result = {
        "hypothesis_id": "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT",
        "n_events": n_events,
        "n_baseline_pool": len(baseline_outcomes_all),
        "match_quality_distribution": quality_counts,
        "event_probability": event_prob,
        "baseline_probability": baseline_prob,
        "delta_p": delta_p,
        "delta_e_mfe_atr": delta_e,
        "ci95_non_overlapping": ci_non_overlap,
        "buy": buy_result,
        "sell": sell_result,
        "direction_consistency_ok": direction_consistency_ok,
        "VERDICT": verdict,
        "verdict_reason": verdict_reason,
        "verdict_locked_before_robustness_diagnostics": True,
    }
    print("\n" + "=" * 70)
    print("PRIMARY RESULT (locked before robustness diagnostics)")
    print("=" * 70)
    print(json.dumps({k: v for k, v in primary_result.items() if k not in ("buy", "sell")}, indent=2, default=str))
    print(f"\n*** VERDICT: {verdict} ({verdict_reason}) ***\n")

    return {
        "primary_result": primary_result,
        "event_outcomes": event_outcomes,
        "baseline_outcomes": baseline_outcomes_all,
        "match_records": match_records,
        "df": df, "state": state, "events": events,
        "threshold_key": threshold_key,
    }


if __name__ == "__main__":
    result = main()
    out = {k: v for k, v in result.items() if k not in ("df", "state", "events", "event_outcomes", "baseline_outcomes")}
    # eventi/baseline salvati solo con campi serializzabili
    out["event_outcomes_summary"] = [{k: v for k, v in o.items() if not k.startswith("_") or k in ("_direction", "_row")} for o in result["event_outcomes"]]
    json.dump(out, open(os.path.join(PHASE6_DIR, "h006_primary_result.json"), "w", encoding="utf-8"), indent=2, default=str)
    print(f"written: {os.path.join(PHASE6_DIR, 'h006_primary_result.json')}")
