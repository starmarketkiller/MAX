#!/usr/bin/env python3
"""Phase 7.1 sec.C - Fit dei parametri di Baseline Engine v4 SOLO su
development.discovery (2023-02-04..2024-08-03) - terzili di coarsening
(volatility_state/trend_state) e standardizzazione delle 3 feature NN
(directional_efficiency, position_in_rolling_range, roc). Congelati e
riusati IDENTICI su internal_validation/locked_validation/final_holdout
- mai ricalcolati (discovery_fitted_only, baseline_contract_v4.json).

Enforcement tecnico: BaselineEngineV4.fit_normalization() solleva
FitIsolationViolation se una riga fuori da discovery viene passata qui -
verificato esplicitamente sotto come test negativo prima di procedere.
"""
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
DATA_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_1", "data")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_1"))
from baseline_engine_v4 import BaselineEngineV4, FitIsolationViolation  # noqa: E402
from splits_p71 import assign_split_p71, SPLIT_BOUNDARIES_DATES  # noqa: E402

NN_FEATURES = ["directional_efficiency", "position_in_rolling_range", "roc"]


def main():
    state = pd.read_csv(os.path.join(DATA_DIR, "market_state_dataset_p71.csv"), parse_dates=["bar_time_utc"])
    state = state.sort_values("bar_time_utc").reset_index(drop=True)
    state["split"] = state["bar_time_utc"].apply(assign_split_p71)

    discovery = state[state["split"] == "discovery"].dropna(subset=["atr_percentile", "ema_slope_atr_norm"] + NN_FEATURES)
    print(f"development.discovery: {len(discovery)} barre utilizzabili (non-NaN su feature di matching) su {(state['split']=='discovery').sum()} totali")

    vol_low, vol_high = discovery["atr_percentile"].quantile([1 / 3, 2 / 3]).values
    trend_low, trend_high = discovery["ema_slope_atr_norm"].quantile([1 / 3, 2 / 3]).values

    # fit_normalization: usa row_index come "riga" per assign_split - qui
    # costruiamo boundaries in termini di row_index del dataframe COMPLETO
    # (bars/state condividono lo stesso index 0..n-1)
    full_boundaries_by_index = build_index_boundaries(state)
    engine = BaselineEngineV4(match_dimensions=NN_FEATURES, k=5, split_boundaries=full_boundaries_by_index)
    discovery_feats = {i: {f: state.loc[i, f] for f in NN_FEATURES} for i in discovery.index}
    norm_params = engine.fit_normalization(discovery_feats)
    print(f"fit_normalization su discovery: OK, {len(norm_params)} feature numeriche standardizzate")

    # Test negativo obbligatorio: fit su una riga di internal_validation deve fallire.
    iv_idx = state[state["split"] == "internal_validation"].dropna(subset=NN_FEATURES).index
    try:
        engine.fit_normalization({int(iv_idx[0]): {f: state.loc[iv_idx[0], f] for f in NN_FEATURES}})
        print("ERRORE: fit su internal_validation avrebbe dovuto fallire!")
        raise SystemExit(1)
    except FitIsolationViolation as e:
        print(f"Fit isolation correttamente verificato (test negativo su internal_validation): {type(e).__name__}")

    frozen = {
        "fitted_at_declared": datetime.now(timezone.utc).isoformat(),
        "fitted_on_split": "discovery",
        "n_discovery_rows_used": len(discovery),
        "categorical_terciles": {
            "volatility_state": {"low_boundary": float(vol_low), "high_boundary": float(vol_high), "source_feature": "atr_percentile"},
            "trend_state": {"low_boundary": float(trend_low), "high_boundary": float(trend_high), "source_feature": "ema_slope_atr_norm"},
        },
        "nn_standardization": {f: {"mean": norm_params[f][0], "std": norm_params[f][1]} for f in NN_FEATURES},
        "match_dimensions": ["volatility_state", "trend_state"] + NN_FEATURES,
        "k": 5,
        "fit_isolation_negative_test_passed": True,
    }
    out_path = os.path.join(DATA_DIR, "frozen_baseline_parameters_p71.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(frozen, f, indent=2)
    print(json.dumps(frozen, indent=2, default=str))
    print(f"\nwritten: {out_path}")


def build_index_boundaries(state: pd.DataFrame) -> dict:
    """Converte SPLIT_BOUNDARIES_DATES (date) in boundaries su row_index
    del dataframe state (0..n-1), compatibili con cross_split_safety.assign_split."""
    bounds = {}
    for name, (start, end) in SPLIT_BOUNDARIES_DATES.items():
        mask = (state["bar_time_utc"] >= start) & (state["bar_time_utc"] <= end)
        idx = state.index[mask]
        if len(idx) == 0:
            continue
        bounds[name] = (int(idx.min()), int(idx.max()) + 1)
    return bounds


if __name__ == "__main__":
    main()
