#!/usr/bin/env python3
"""Outcome-blind compatibility diagnostic for the two existing regimes.

This does not train, optimize, or select a classifier.  The classifiers have
different timeframes and ontologies, so compatibility is assessed only on
facets that have an explicit semantic crosswalk.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
PHASE55 = ROOT / "server/research_scripts/phase5_5"
PHASE727 = ROOT / "server/research_scripts/phase7/phase7_27"
H4_REGIME = PHASE55 / "regime_layer_v1.csv"
D1_PRICE = ROOT / "server/research_scripts/phase7/phase7_9h/raw_data/nxs_d1_gold_phase79h.csv"
OUT = Path(__file__).resolve().parent / "regime_compatibility_diagnostic_v1.json"

# Explicit, outcome-independent semantic crosswalk. TRANSITION has no direct
# equivalent in the D1 Cartesian trend/volatility representation.
CROSSWALK = {
    "HIGH_VOL": {"d1_dimension": "vol_tercile", "accepted_values": ["HIGH"]},
    "LOW_VOL": {"d1_dimension": "vol_tercile", "accepted_values": ["LOW"]},
    "TRENDING": {"d1_dimension": "sma50_slope", "accepted_values": ["UP", "DOWN"]},
    "RANGING": {"d1_dimension": "sma50_slope", "accepted_values": ["FLAT"]},
    "TRANSITION": {"d1_dimension": None, "accepted_values": []},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_d1_regime() -> pd.DataFrame:
    sys.path.insert(0, str(PHASE727))
    try:
        import nxs_regime_classifier as classifier
        classifier._REGIME_DF = None
        return classifier.build_regime_table().copy()
    finally:
        sys.path.pop(0)


def build_report() -> dict:
    h4 = pd.read_csv(H4_REGIME)
    h4["bar_time_utc"] = pd.to_datetime(h4["bar_time_utc"], utc=True)
    h4["calendar_date"] = h4["bar_time_utc"].dt.date

    d1 = _load_d1_regime()
    d1["calendar_date"] = pd.to_datetime(d1["time"]).dt.date
    d1_daily = d1[["calendar_date", "sma50_slope", "vol_tercile"]].drop_duplicates("calendar_date")
    joined = h4.merge(d1_daily, on="calendar_date", how="left", validate="many_to_one")

    in_overlap = joined[
        (joined["calendar_date"] >= d1_daily["calendar_date"].min())
        & (joined["calendar_date"] <= d1_daily["calendar_date"].max())
    ].copy()
    matched = in_overlap[in_overlap["sma50_slope"].notna()].copy()

    evaluations = []
    per_state = {}
    for state, rule in CROSSWALK.items():
        state_rows = matched[matched["regime_v1"] == state]
        if rule["d1_dimension"] is None:
            per_state[state] = {
                "n": int(len(state_rows)),
                "comparable": False,
                "reason": "No direct D1 semantic equivalent",
            }
            continue
        dimension = rule["d1_dimension"]
        known = state_rows[~state_rows[dimension].isin(["UNKNOWN"]) & state_rows[dimension].notna()].copy()
        compatible = known[dimension].isin(rule["accepted_values"])
        per_state[state] = {
            "n": int(len(state_rows)),
            "n_comparable": int(len(known)),
            "n_compatible": int(compatible.sum()),
            "agreement_rate": float(compatible.mean()) if len(known) else None,
            "comparable": True,
        }
        evaluations.extend(compatible.tolist())

    coverage_rate = float(len(matched) / len(in_overlap)) if len(in_overlap) else 0.0
    agreement_rate = float(sum(evaluations) / len(evaluations)) if evaluations else None
    # FULL is structurally unavailable: H4 is one priority-ordered label while
    # D1 is a Cartesian trend/vol representation. Any actual comparable facets
    # with overlapping coverage establish PARTIAL, otherwise NONE.
    semantic = "PARTIAL" if len(matched) and evaluations else "NONE"

    return {
        "schema_version": 1,
        "diagnostic_only": True,
        "scientific_outcomes_read": False,
        "semantic_compatibility": semantic,
        "full_compatibility_possible": False,
        "full_compatibility_blocker": "Different timeframe and ontology: H4 priority-ordered single state versus D1 trend x volatility facets.",
        "sources": {
            "phase5_5_h4": {
                "file": H4_REGIME.relative_to(ROOT).as_posix(),
                "sha256": sha256(H4_REGIME),
                "timeframe": "H4",
                "states": list(CROSSWALK),
                "threshold_fit": "discovery rows [0,3366)",
            },
            "phase7_27_d1": {
                "file": D1_PRICE.relative_to(ROOT).as_posix(),
                "sha256": sha256(D1_PRICE),
                "timeframe": "D1",
                "dimensions": ["sma50_slope", "vol_tercile"],
                "known_limitation": "ATR tercile boundaries are fitted on the full D1 dataset; diagnostic comparison only.",
            },
        },
        "crosswalk": CROSSWALK,
        "coverage": {
            "h4_rows_in_calendar_overlap": int(len(in_overlap)),
            "h4_rows_matched_to_d1_calendar_date": int(len(matched)),
            "calendar_date_coverage_rate": coverage_rate,
        },
        "missingness": {
            "h4_regime_missing": int(matched["regime_v1"].isna().sum()),
            "d1_trend_unknown": int((matched["sma50_slope"] == "UNKNOWN").sum()),
            "d1_volatility_unknown": int((matched["vol_tercile"] == "UNKNOWN").sum()),
        },
        "comparable_facets": {
            "n": int(len(evaluations)),
            "agreement_rate": agreement_rate,
            "disagreement_rate": (1.0 - agreement_rate) if agreement_rate is not None else None,
            "per_h4_state": per_state,
        },
        "phase1_regime_source": "PHASE5_5_H4_REGIME_V1",
        "selection_reason": "H4 granularity and discovery-only threshold fitting; selected before and without MACD outcomes.",
        "not_permitted": [
            "No classifier tuning",
            "No third classifier",
            "No classifier choice based on MACD outcome",
            "No use of this diagnostic as an effect-significance gate"
        ],
    }


def main() -> int:
    report = build_report()
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
