#!/usr/bin/env python3
"""Phase 6 sec.8 - Robustness diagnostics. Eseguiti SOLO DOPO che
run_h006_test.py ha gia' stampato/salvato il verdetto primario - questo
script non puo' e non deve cambiare quel verdetto, lo arricchisce solo
di narrativa/contesto (pre-registrata in H006_frozen_spec.json,
allowed_subgroup_analyses).
"""
import json
import os

import numpy as np
import pandas as pd

from run_h006_test import main as run_primary
from edge_discovery import wl_censored, mean_mfe, outlier_robustness_check  # noqa: E402
from stats_utils import probability_record  # noqa: E402

PHASE6_DIR = os.path.dirname(os.path.abspath(__file__))


def regime_of(row, regime_params):
    vol_terc = regime_params["vol_tercile_33_67"]
    eff_terc = regime_params["directional_efficiency_tercile_33_67"]
    freshness = regime_params["transition_freshness_bars_leq"]
    v, e, p = row["atr_percentile"], row["directional_efficiency"], row["trend_persistence_bars"]
    if pd.isna(v) or pd.isna(e) or pd.isna(p):
        return None
    if v > vol_terc[1]:
        return "HIGH_VOL"
    if v < vol_terc[0]:
        return "LOW_VOL"
    if p <= freshness:
        return "TRANSITION"
    if e > eff_terc[1]:
        return "TRENDING"
    return "RANGING"


def bootstrap_delta_p(event_outcomes, baseline_outcomes, threshold_key, n_boot=2000, seed=42):
    rng = np.random.default_rng(seed)
    ev = np.array([1 if o[threshold_key] == "TARGET_FIRST" else (0 if o[threshold_key] == "STOP_FIRST" else np.nan) for o in event_outcomes])
    ev = ev[~np.isnan(ev)]
    bl = np.array([1 if o[threshold_key] == "TARGET_FIRST" else (0 if o[threshold_key] == "STOP_FIRST" else np.nan) for o in baseline_outcomes])
    bl = bl[~np.isnan(bl)]
    if len(ev) == 0 or len(bl) == 0:
        return None
    deltas = []
    for _ in range(n_boot):
        ev_s = rng.choice(ev, size=len(ev), replace=True)
        bl_s = rng.choice(bl, size=len(bl), replace=True)
        deltas.append(ev_s.mean() - bl_s.mean())
    deltas = np.array(deltas)
    return {
        "n_boot": n_boot,
        "mean": float(deltas.mean()),
        "ci95_low": float(np.percentile(deltas, 2.5)),
        "ci95_high": float(np.percentile(deltas, 97.5)),
        "pct_positive": float((deltas > 0).mean()),
    }


def event_clustering(event_rows):
    rows_sorted = sorted(event_rows)
    gaps = [rows_sorted[i + 1] - rows_sorted[i] for i in range(len(rows_sorted) - 1)]
    if not gaps:
        return {"n_events": len(rows_sorted), "note": "campione troppo piccolo per gap"}
    gaps = np.array(gaps)
    return {
        "n_events": len(rows_sorted),
        "median_gap_bars": float(np.median(gaps)),
        "min_gap_bars": int(gaps.min()),
        "pct_gap_leq_3_bars": float((gaps <= 3).mean()),
        "pct_gap_leq_10_bars": float((gaps <= 10).mean()),
    }


def main():
    result = run_primary()
    primary = result["primary_result"]
    event_outcomes = result["event_outcomes"]
    baseline_outcomes = result["baseline_outcomes"]
    state = result["state"]
    threshold_key = result["threshold_key"]

    params = json.load(open(os.path.join(PHASE6_DIR, "frozen_baseline_parameters.json"), encoding="utf-8"))
    regime_params = params["regime_layer_thresholds"]

    # --- regime breakdown ---
    regime_counts = {}
    regime_outcomes = {}
    for o in event_outcomes:
        row = state.iloc[o["_row"]]
        reg = regime_of(row, regime_params)
        regime_counts[reg] = regime_counts.get(reg, 0) + 1
        regime_outcomes.setdefault(reg, []).append(o)
    regime_summary = {}
    for reg, outs in regime_outcomes.items():
        w, l, c = wl_censored(outs, threshold_key)
        pr = probability_record(w, l, c)
        regime_summary[str(reg)] = {"n": w + l, "observed_p": pr["observed_p"]}

    # --- subperiod (quarterly) stability ---
    quarters = [
        ("Q1_2022-02-04_2022-05-03", pd.Timestamp("2022-02-04", tz="UTC"), pd.Timestamp("2022-05-04", tz="UTC")),
        ("Q2_2022-05-04_2022-08-03", pd.Timestamp("2022-05-04", tz="UTC"), pd.Timestamp("2022-08-04", tz="UTC")),
        ("Q3_2022-08-04_2022-11-03", pd.Timestamp("2022-08-04", tz="UTC"), pd.Timestamp("2022-11-04", tz="UTC")),
        ("Q4_2022-11-04_2023-02-03", pd.Timestamp("2022-11-04", tz="UTC"), pd.Timestamp("2023-02-04", tz="UTC")),
    ]
    quarterly_summary = {}
    for label, qstart, qend in quarters:
        outs = [o for o in event_outcomes if qstart <= state["bar_time_utc"].iloc[o["_row"]] < qend]
        w, l, c = wl_censored(outs, threshold_key)
        pr = probability_record(w, l, c)
        quarterly_summary[label] = {"n": w + l, "observed_p": pr["observed_p"]}

    # --- outlier trimming (riuso Phase 5) ---
    robustness_trim = outlier_robustness_check(event_outcomes, threshold_key)

    # --- bootstrap ---
    boot = bootstrap_delta_p(event_outcomes, baseline_outcomes, threshold_key)

    # --- event clustering ---
    clustering = event_clustering([o["_row"] for o in event_outcomes])

    diagnostics = {
        "note": "Diagnostici POST-verdetto - non hanno cambiato ne' possono cambiare il VERDICT gia' bloccato in h006_primary_result.json",
        "regime_breakdown": {"counts": {str(k): v for k, v in regime_counts.items()}, "outcome_summary": regime_summary},
        "quarterly_subperiod_stability": quarterly_summary,
        "outlier_trim_10pct": robustness_trim,
        "bootstrap_delta_p": boot,
        "event_clustering": clustering,
    }
    json.dump(diagnostics, open(os.path.join(PHASE6_DIR, "h006_robustness_diagnostics.json"), "w", encoding="utf-8"), indent=2, default=str)
    print(json.dumps(diagnostics, indent=2, default=str))
    print(f"\nwritten: {os.path.join(PHASE6_DIR, 'h006_robustness_diagnostics.json')}")
    return diagnostics


if __name__ == "__main__":
    main()
