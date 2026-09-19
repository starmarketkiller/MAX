#!/usr/bin/env python3
"""Phase 7.0B sec.3 - Esercita Baseline Engine v4 su dati SINTETICI
(synthetic_fixtures.py) per produrre baseline_quality_report_v4.json.
Nessun dato di mercato reale, nessuna metrica di outcome/ΔP (sec.19: no
edge evaluation in questa fase) - solo qualita' del matching stesso.
"""
import os
import sys

PHASE7_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PHASE7_DIR, "engine"))
sys.path.insert(0, os.path.join(PHASE7_DIR, "..", "phase6_6"))

from baseline_engine_v4 import BaselineEngineV4  # noqa: E402
from synthetic_fixtures import generate_fixture  # noqa: E402
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def main():
    fx = generate_fixture(seed=42)
    boundaries = fx["split_boundaries"]
    engine = BaselineEngineV4(match_dimensions=["volatility_state"], k=5, split_boundaries=boundaries)

    discovery_rows = [r for r in fx["control_pool"] if boundaries["discovery"][0] <= r < boundaries["discovery"][1]]
    discovery_feats = {r: fx["feature_by_row"][r] for r in discovery_rows if r in fx["feature_by_row"]}
    engine.fit_normalization(discovery_feats)  # nessuna dim numerica dichiarata -> ok, params vuoti

    results = []
    for ev_row in fx["event_rows"]:
        ev_dir = fx["direction_by_row"][ev_row]
        ev_feat = fx["feature_by_row"].get(ev_row, {"volatility_state": "HIGH", "trend_state": "UP"})
        ev_split = None
        for name, (s, e) in boundaries.items():
            if s <= ev_row < e:
                ev_split = name
        if ev_split is None:
            continue
        same_split_pool = [c for c in fx["control_pool"] if boundaries[ev_split][0] <= c < boundaries[ev_split][1]]
        control_row_by_id = {c: c for c in same_split_pool}
        control_direction_by_id = {c: fx["direction_by_row"].get(c, ev_dir) for c in same_split_pool}
        control_features_by_id = {c: fx["feature_by_row"].get(c, {"volatility_state": "HIGH"}) for c in same_split_pool}

        result = engine.match(
            event_id=f"EVT-{ev_row}", event_row=ev_row, event_direction=ev_dir, event_features=ev_feat,
            control_pool=same_split_pool, control_row_by_id=control_row_by_id,
            control_direction_by_id=control_direction_by_id, control_features_by_id=control_features_by_id,
        )
        results.append(result)

    from baseline_engine_v4 import build_quality_report
    report = build_quality_report(results)
    report["SYNTHETIC_FIXTURE_ONLY"] = True
    report["note"] = "Baseline Engine v4 esercitata su synthetic_fixtures.py - nessun dato di mercato reale, nessuna metrica di outcome/ΔP calcolata (sec.19 Phase 7.0B)."
    report["match_dimensions_used"] = ["volatility_state"]
    report["k"] = 5

    out_path = os.path.join(PHASE7_DIR, "baseline_quality_report_v4.json")
    save_json(out_path, wrap_with_provenance(report, "phase7/run_baseline_v4_on_fixtures.py"))
    print(f"n_events={report['n_events']} n_matched={report['n_matched']} n_rejected={report['n_rejected_insufficient_pool']}")
    print(f"match_quality_counts={report['match_quality_counts']}")
    print(f"written: {out_path}")


if __name__ == "__main__":
    main()
