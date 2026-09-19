#!/usr/bin/env python3
"""Phase 7.3 sec.11-12 - Synthetic Test Suite + Dry Run strutturale.
Dati interamente SINTETICI (nessun dato NEXUS) - un "toy detector"
generico esercita l'intera pipeline: detect -> causality guard ->
episode engine -> baseline adapter -> outcome contract -> evidence
record, end-to-end. I 10 casi nominati dall'utente (sec.11) sono
verificati esplicitamente."""
import hashlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PHASE73_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PHASE73_DIR, "engine"))
sys.path.insert(0, PHASE73_DIR)
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))

from sequence_causality_guard import enforce_temporal_causality, SequenceCausalityViolation  # noqa: E402
from sequence_episode_engine import build_event_and_episode_views  # noqa: E402
from sequence_state_snapshot import build_state_snapshot, load_causal_safe_feature_ids  # noqa: E402
from sequence_baseline_adapter_v1 import SequenceBaselineAdapter  # noqa: E402
from outcome_surface_v3 import OutcomeSurfaceV3, OutcomeShoppingBlocked  # noqa: E402
from cross_split_safety import CrossSplitViolation  # noqa: E402
from baseline_engine_v4 import FitIsolationViolation  # noqa: E402


class DuplicateSequenceEventError(Exception):
    pass


class SequenceEventRegistry:
    """Dedup deterministica per sequence_event_id (sec.11, caso 8)."""
    def __init__(self):
        self._seen = set()

    @staticmethod
    def make_id(sequence_id, event_a_index, detector_version):
        raw = f"{sequence_id}|{event_a_index}|{detector_version}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def register(self, sequence_id, event_a_index, detector_version):
        eid = self.make_id(sequence_id, event_a_index, detector_version)
        if eid in self._seen:
            raise DuplicateSequenceEventError(f"sequence_event_id duplicato: {eid} (sequence_id={sequence_id}, event_a_index={event_a_index})")
        self._seen.add(eid)
        return eid


def toy_detect(values, threshold, detector_version="toy-v1"):
    """Detector sintetico: event_a quando |value| supera threshold;
    direction=BUY se value>0 altrimenti SELL; transition si risolve
    immediatamente (stesso bar, per semplicita' del toy)."""
    events = []
    registry = SequenceEventRegistry()
    for i, v in enumerate(values):
        if abs(v) > threshold:
            direction = "BUY" if v > 0 else "SELL"
            eid = registry.register("SEQ-TOY", i, detector_version)
            events.append({
                "sequence_event_id": eid, "sequence_id": "SEQ-TOY", "direction": direction,
                "event_a_index": i, "transition_complete_index": i, "event_b_index_optional": None,
                "observation_cutoff_index": i, "prediction_start_index": i, "detector_version": detector_version,
            })
    return events, registry


RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    # ---- Caso 1: valid sequence detected ----
    values = [0.1, 0.2, -0.9, 0.05, 0.85, 0.86, 0.87, -0.95, 0.1, 0.92]
    events, registry = toy_detect(values, threshold=0.8)
    check("valid_sequence_detected", len(events) >= 1, f"n_eventi={len(events)}")

    # ---- Caso 4: direction preserved ----
    expected_dirs = ["SELL" if values[e["event_a_index"]] < 0 else "BUY" for e in events]
    actual_dirs = [e["direction"] for e in events]
    check("direction_preserved", expected_dirs == actual_dirs)

    # ---- Caso 8: duplicated event ids rejected ----
    try:
        registry.register("SEQ-TOY", events[0]["event_a_index"], "toy-v1")
        check("duplicated_event_ids_rejected", False, "duplicato NON rifiutato!")
    except DuplicateSequenceEventError:
        check("duplicated_event_ids_rejected", True)

    # ---- Caso 2: future-dependent transition rejected ----
    try:
        enforce_temporal_causality(observation_cutoff_index=5, max_feature_timestamp_index=8,
                                    transition_complete_index=5, prediction_start_index=5,
                                    outcome_window_start_index=6, sequence_event_id="TEST-FUTURE")
        check("future_dependent_transition_rejected", False, "violazione NON rilevata!")
    except SequenceCausalityViolation:
        check("future_dependent_transition_rejected", True)

    # ---- Caso 7: outcome starts after prediction start ----
    ok = enforce_temporal_causality(observation_cutoff_index=5, max_feature_timestamp_index=5,
                                     transition_complete_index=5, prediction_start_index=5,
                                     outcome_window_start_index=6, sequence_event_id="TEST-OK")
    check("outcome_starts_after_prediction_start", ok is True)
    try:
        enforce_temporal_causality(observation_cutoff_index=5, max_feature_timestamp_index=5,
                                    transition_complete_index=5, prediction_start_index=5,
                                    outcome_window_start_index=5, sequence_event_id="TEST-OVERLAP")
        check("outcome_overlap_rejected", False, "sovrapposizione NON rilevata!")
    except SequenceCausalityViolation:
        check("outcome_overlap_rejected", True)

    # ---- Caso 3: overlapping episode collapse ----
    clustered_events = [dict(e, event_a_index=e["event_a_index"]) for e in events]
    # forziamo un cluster noto: eventi a indice 4,5,6 (ravvicinati) + isolati
    synthetic_cluster_events = [
        {"sequence_event_id": f"C-{i}", "sequence_id": "SEQ-TOY", "direction": "BUY", "event_a_index": i,
         "transition_complete_index": i, "prediction_start_index": i}
        for i in [4, 5, 6, 20, 40, 41]
    ]
    ev_view, ep_view = build_event_and_episode_views(synthetic_cluster_events, episode_gap_rule=3,
                                                       natural_horizon=40, overlap_policy="COLLAPSE_TO_FIRST")
    check("overlapping_episode_collapse", ev_view["n"] == 6 and ep_view["n_episodes"] == 3,
          f"event_n={ev_view['n']} episode_n={ep_view['n_episodes']}")

    # ---- Caso 5/6: baseline same-split enforcement + cross-split control rejected ----
    boundaries = {"discovery": (0, 100), "internal_validation": (100, 150),
                  "locked_validation": (150, 200), "final_holdout": (200, 250)}
    adapter = SequenceBaselineAdapter(match_dimensions=["toy_state"], k=5, split_boundaries=boundaries)
    discovery_snaps = {i: {"toy_state": 1.0 if i % 2 == 0 else 0.0} for i in range(0, 100, 2)}
    adapter.fit_on_discovery_only(discovery_snaps)
    same_split_pool = list(range(0, 40, 2))
    seq_event_demo = {"sequence_event_id": "DEMO-BASE-1", "event_a_index": 10, "direction": "BUY",
                       "state_snapshot": {"toy_state": 1.0}}
    result_ok = adapter.match_sequence_event(seq_event_demo, same_split_pool,
                                              {c: c for c in same_split_pool},
                                              {c: {"toy_state": 1.0} for c in same_split_pool})
    check("baseline_same_split_enforcement", result_ok["status"] in ("MATCHED", "MATCHED_K_SHORTFALL") and
          all(m["control_split"] == "discovery" for m in result_ok["matches"]))

    cross_split_pool = same_split_pool + [120, 121]  # 120/121 sono in internal_validation
    result_cross = adapter.match_sequence_event(seq_event_demo, cross_split_pool,
                                                 {c: c for c in cross_split_pool},
                                                 {c: {"toy_state": 1.0} for c in cross_split_pool})
    matched_control_ids = {m["control_id"] for m in result_cross["matches"]}
    check("cross_split_control_rejected", not ({120, 121} & matched_control_ids),
          "il pool di controllo cross-split viene filtrato PRIMA del matching (same_split), mai incluso nei match finali")

    # ---- Caso 9: insufficient control pool rejected ----
    tiny_pool = same_split_pool[:5]
    result_tiny = adapter.match_sequence_event(seq_event_demo, tiny_pool,
                                                {c: c for c in tiny_pool},
                                                {c: {"toy_state": 1.0} for c in tiny_pool})
    check("insufficient_control_pool_rejected", result_tiny["status"] == "REJECTED_INSUFFICIENT_POOL")

    # ---- Caso 10: post-hoc outcome addition rejected ----
    surface = OutcomeSurfaceV3(primary_outcome="P_PLUS_1ATR_BEFORE_MINUS_1ATR",
                                secondary_outcomes=["MFE"], diagnostic_outcomes=["MAE"])
    try:
        surface.assert_no_post_hoc_outcome_addition("REVERSAL_PROBABILITY", already_saw_results=True)
        check("post_hoc_outcome_addition_rejected", False, "outcome shopping NON bloccato!")
    except OutcomeShoppingBlocked:
        check("post_hoc_outcome_addition_rejected", True)

    # ---- Dry run strutturale E2E (sec.12): detector -> snapshot -> episode -> baseline -> outcome -> evidence ----
    safe_ids = load_causal_safe_feature_ids()
    snap = build_state_snapshot({"volatility_state": "HIGH", "trend_state": "UP", "directional_efficiency": 0.5,
                                  "position_in_rolling_range": 0.6, "roc": 0.02, "session": "LONDON"},
                                 direction="BUY", causal_safe_feature_ids=safe_ids)
    e2e_event = {"sequence_event_id": "E2E-DEMO-1", "sequence_id": "SEQ-TOY", "direction": "BUY",
                 "event_a_index": 10, "transition_complete_index": 10, "prediction_start_index": 10,
                 "observation_cutoff_index": 10, "state_snapshot": snap, "detector_version": "toy-v1"}
    enforce_temporal_causality(observation_cutoff_index=10, max_feature_timestamp_index=10,
                                transition_complete_index=10, prediction_start_index=10,
                                outcome_window_start_index=11, sequence_event_id=e2e_event["sequence_event_id"])
    ev_view2, ep_view2 = build_event_and_episode_views([e2e_event], episode_gap_rule=10, natural_horizon=40,
                                                         overlap_policy="COLLAPSE_TO_FIRST")
    e2e_adapter = SequenceBaselineAdapter(match_dimensions=["directional_efficiency"], k=5, split_boundaries=boundaries)
    e2e_adapter.fit_on_discovery_only({i: {"directional_efficiency": 0.4 + 0.01 * i} for i in range(0, 100, 2)})
    e2e_pool = list(range(0, 40, 2))
    e2e_result = e2e_adapter.match_sequence_event(
        e2e_event, e2e_pool, {c: c for c in e2e_pool},
        {c: {"directional_efficiency": 0.4 + 0.01 * c} for c in e2e_pool})
    evidence_stub = {
        "event_view_n": ev_view2["n"], "episode_view_n": ep_view2["n"], "episode_cluster_count": ep_view2["n_episodes"],
        "dependence_status": "NOT_SENSITIVE", "baseline_match_status": e2e_result["status"],
        "primary_outcome_id": surface.primary_outcome,
        "lifecycle_state": "GENERATED",
    }
    check("structural_dry_run_e2e_completes", evidence_stub["baseline_match_status"] in ("MATCHED", "MATCHED_K_SHORTFALL"))

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = sum(1 for r in RESULTS if r["status"] == "FAIL")
    print(f"\n=== Synthetic suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0, RESULTS, evidence_stub


if __name__ == "__main__":
    ok, results, evidence_stub = main()
    sys.exit(0 if ok else 1)
