#!/usr/bin/env python3
"""Phase 7.5A - Sequence Structural Feasibility Gate: regression suite.
Interamente su dati SINTETICI (nessun dato NEXUS, nessun outcome). Il
"replay" della geometria SEQ-0015 usa solo i conteggi GIA' PUBBLICATI
(EVENT_VIEW=249, embargo=39, minimum=30) per verificare che il gate
generale li avrebbe segnalati - non e' una nuova indagine su SEQ-0015
(chiusa, vedi failure_memory_registry_v1.json FAIL-009): nessun outcome
letto, nessun dato reale usato, nessuna nuova conclusione su quella
sequence."""
import json
import os
import random
import sys

PHASE75_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE75_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))

from sequence_structural_feasibility_gate import (  # noqa: E402
    evaluate_family_structural_feasibility, missing_spec_fields, compute_detection_funnel,
    compute_cluster_geometry, compute_feasibility_ratios, classify_geometry_firing_rate_guard,
    run_matching_preflight, REQUIRED_SPEC_FIELDS, DEFAULT_POLICY,
    VERDICT_FEASIBLE, VERDICT_BORDERLINE, VERDICT_NOT_TESTABLE, VERDICT_NEEDS_DETECTOR_FORMALIZATION,
)
from canonical_utils import canonical_sha256  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def _minimal_spec(**overrides):
    spec = {
        "sequence_family_id": "SEQFAM-TEST",
        "detector_frozen": True,
        "detector_source_ref": "TEST_ONLY",
        "detector_parameters": {"threshold": 1.0},
        "observation_timing": {"observation_cutoff": "close(t)"},
        "event_direction_policy": "BOTH",
        "episode_gap_rule": 3,
        "overlap_policy": "COLLAPSE_TO_FIRST",
        "proposed_natural_horizon": 40,
        "proposed_outcome_overlap_embargo_bars": 39,
        "discovery_partition": {"partition_id": "TEST", "n_bars": 5000},
        "minimum_evidence_gates": {"n_nominal_minimum": 30},
        "event_row_indices": list(range(0, 60 * 60, 60)),
    }
    spec.update(overrides)
    return spec


def test_missing_fields_never_invented():
    """sec.9: nessun parametro inventato - una family incompleta deve
    essere classificata NEEDS_DETECTOR_FORMALIZATION con l'elenco esatto
    dei campi mancanti, MAI fatta girare con un default silenzioso."""
    empty = {"sequence_family_id": "SEQFAM-EMPTY"}
    missing = missing_spec_fields(empty)
    check("all_required_fields_flagged_when_absent", set(missing) == set(REQUIRED_SPEC_FIELDS) - {"sequence_family_id"},
          f"missing={sorted(missing)}")

    r = evaluate_family_structural_feasibility(empty)
    check("empty_spec_verdict_is_needs_formalization", r["verdict"] == VERDICT_NEEDS_DETECTOR_FORMALIZATION)
    check("empty_spec_no_funnel_computed", "detection_funnel" not in r,
          "il gate non deve calcolare NULLA su una family incompleta")

    partial = _minimal_spec()
    del partial["episode_gap_rule"]
    del partial["proposed_outcome_overlap_embargo_bars"]
    r2 = evaluate_family_structural_feasibility(partial)
    check("partial_spec_flags_exactly_missing_fields",
          set(r2["missing_degrees_of_freedom"]) == {"episode_gap_rule", "proposed_outcome_overlap_embargo_bars"},
          f"got={r2['missing_degrees_of_freedom']}")

    empty_events = _minimal_spec(event_row_indices=[])
    r3 = evaluate_family_structural_feasibility(empty_events)
    check("empty_event_row_indices_flagged", "event_row_indices" in r3["missing_degrees_of_freedom"])

    not_frozen = _minimal_spec(detector_frozen=False)
    r4 = evaluate_family_structural_feasibility(not_frozen)
    check("detector_frozen_false_flagged", "detector_frozen" in r4["missing_degrees_of_freedom"])


def test_seq0015_published_geometry_structural_replay():
    """Replay SINTETICO della sola geometria GIA' PUBBLICATA per SEQ-0015
    (EVENT_VIEW=249, natural_horizon=40, embargo=39, minimum=30) - verifica
    che il gate generale l'avrebbe segnalata immediatamente come
    NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY, con la causa esplicita nel
    firing_rate_guard. Nessun dato reale, nessun outcome, nessuna nuova
    indagine su SEQ-0015."""
    random.seed(42)
    rows = []
    r = 100
    while len(rows) < 249:
        rows.append(r)
        r += random.randint(1, 8)  # gap tipico << embargo=39, per costruzione (replay del fatto pubblicato)
    spec = _minimal_spec(
        sequence_family_id="SEQFAM-STRUCTURAL-REPLAY-ONLY-NOT-A-NEW-SEQ0015-RUN",
        event_row_indices=rows[:249],
        discovery_partition={"partition_id": "SYNTHETIC_REPLAY_OF_PUBLISHED_GEOMETRY", "n_bars": 2393},
    )
    result = evaluate_family_structural_feasibility(spec)
    check("replay_verdict_not_testable", result["verdict"] == VERDICT_NOT_TESTABLE,
          f"verdict={result['verdict']}")
    check("replay_independent_view_collapses", result["detection_funnel"]["INDEPENDENT_VIEW"]["n"] < 30,
          f"INDEPENDENT_VIEW={result['detection_funnel']['INDEPENDENT_VIEW']['n']}")
    check("replay_firing_guard_flags_pathological",
          result["firing_rate_guard"]["verdict"] == "PATHOLOGICAL_FOR_HORIZON")
    check("replay_would_have_caught_it_before_outcome_contract", "provenance" in result and result["provenance"]["outcome_blind"] is True)


def test_feasible_ample_geometry():
    spec = _minimal_spec(event_row_indices=list(range(0, 60 * 60, 60)))  # gap=60>39, 60 unita' >= 1.5*30
    result = evaluate_family_structural_feasibility(spec)
    check("ample_spacing_is_feasible", result["verdict"] == VERDICT_FEASIBLE, f"verdict={result['verdict']}")
    check("ample_spacing_firing_guard_compatible", result["firing_rate_guard"]["verdict"] == "COMPATIBLE_WITH_HORIZON")
    check("episode_retention_is_one_when_no_local_clustering", result["feasibility_ratios"]["episode_retention"] == 1.0)


def test_not_testable_below_minimum_even_without_clustering():
    """Un caso limite distinto da SEQ-0015: qui gli eventi NON sono
    clusterizzati (gap ampio, nessun collasso patologico) - semplicemente
    ce ne sono troppo pochi in assoluto. Deve restare NOT_TESTABLE (sotto
    il minimo) ma il firing_rate_guard deve dire COMPATIBLE_WITH_HORIZON,
    non PATHOLOGICAL_FOR_HORIZON - sono due cause distinte dello stesso
    verdetto finale, e il gate non deve confonderle."""
    spec = _minimal_spec(event_row_indices=list(range(0, 10 * 200, 200)))  # 10 eventi, gap=200>>39
    result = evaluate_family_structural_feasibility(spec)
    check("too_few_events_is_not_testable", result["verdict"] == VERDICT_NOT_TESTABLE)
    check("too_few_events_not_a_geometry_pathology",
          result["firing_rate_guard"]["verdict"] == "COMPATIBLE_WITH_HORIZON",
          "n insufficiente e geometria patologica sono cause DISTINTE dello stesso NOT_TESTABLE")


def test_borderline_thin_margin():
    spec = _minimal_spec(event_row_indices=list(range(0, 32 * 60, 60)))  # 32 unita' indipendenti, minimo=30, <1.5x
    result = evaluate_family_structural_feasibility(spec)
    check("thin_margin_is_borderline_not_feasible", result["verdict"] == VERDICT_BORDERLINE,
          f"verdict={result['verdict']}, n={result['feasibility_ratios']['independent_units']}")


def test_geometry_guard_is_not_a_fixed_percentage():
    """sec.7: prova diretta che il guard NON e' 'evento raro = buono' -
    un detector con firing_rate BASSISSIMO ma eventi concentrati in un
    'blocco' (gap piccolo fra loro, ampio prima/dopo) deve comunque
    essere PATHOLOGICAL_FOR_HORIZON."""
    rare_but_clustered = list(range(1000, 1000 + 20 * 5, 5))  # 20 eventi, gap=5<<39, firing_rate=20/50000=0.04%
    funnel = compute_detection_funnel(rare_but_clustered, n_bars=50000, episode_gap_rule=3,
                                       natural_horizon=40, overlap_policy="COLLAPSE_TO_FIRST",
                                       outcome_overlap_embargo_bars=39)
    ratios = compute_feasibility_ratios(funnel, {"n_nominal_minimum": 30})
    guard = classify_geometry_firing_rate_guard(funnel, ratios)
    check("rare_firing_rate_can_still_be_pathological", guard["verdict"] == "PATHOLOGICAL_FOR_HORIZON",
          f"firing_rate={funnel['firing_rate']:.5f}")
    check("rare_firing_rate_value_is_indeed_sparse", funnel["firing_rate"] < 0.02,
          "conferma che il caso e' REALMENTE a bassa percentuale di firing, non solo nominalmente")


def test_cluster_geometry_fields_present():
    spec = _minimal_spec(event_row_indices=list(range(0, 20 * 5, 5)) + [10000, 10100, 10200])
    result = evaluate_family_structural_feasibility(spec)
    geo = result["cluster_geometry"]
    for field in ("n_independent_clusters", "cluster_size_distribution", "max_cluster_size",
                  "median_cluster_size", "fraction_events_in_largest_cluster",
                  "fraction_gaps_below_embargo", "longest_no_event_gap_bars"):
        check(f"cluster_geometry_has_{field}", field in geo)
    check("longest_gap_reflects_the_isolated_tail", geo["longest_no_event_gap_bars"] >= 9800)


def test_matching_preflight_determinism_and_reuse_cap():
    boundaries = {"discovery": (0, 200), "internal_validation": (200, 280),
                  "locked_validation": (280, 360), "final_holdout": (360, 440)}
    pool = [100, 102, 104, 106, 108, 110]
    row_by_id = {c: c for c in pool}
    dir_by_id = {c: "BUY" for c in pool}
    feat_by_id = {c: {"volatility_state": "HIGH"} for c in pool}
    discovery_feats = {i: {"volatility_state": "HIGH" if i % 2 == 0 else "LOW"} for i in range(0, 200, 2)}
    events = [{"event_id": f"EVT-{i}", "event_row": 10 + i, "direction": "BUY",
               "features": {"volatility_state": "HIGH"}} for i in range(4)]

    preflight = run_matching_preflight(
        match_dimensions=["volatility_state"], k=2, split_boundaries=boundaries, events=events,
        control_pool=pool, control_row_by_id=row_by_id, control_direction_by_id=dir_by_id,
        control_features_by_id=feat_by_id, discovery_features_by_row=discovery_feats,
        minimum_control_count=2, max_control_reuse_per_run=2,
    )
    check("preflight_tie_break_deterministic", preflight["tie_break_deterministic"] is True)
    check("preflight_reuse_within_declared_cap", preflight["max_reuse_within_declared_cap"] is True)
    check("preflight_reports_n_matched", preflight["n_matched"] + preflight["n_rejected_insufficient_pool"] == 4)


def test_provenance_and_determinism():
    spec = _minimal_spec()
    r1 = evaluate_family_structural_feasibility(spec)
    r2 = evaluate_family_structural_feasibility(spec)
    for field in ("detector_source_ref", "detector_parameters_hash", "spec_hash", "discovery_partition",
                  "engine_version", "policy_version", "outcome_blind", "deterministic"):
        check(f"provenance_has_{field}", field in r1["provenance"])
    check("provenance_deterministic_across_runs", r1["provenance"]["spec_hash"] == r2["provenance"]["spec_hash"])
    check("funnel_deterministic_across_runs",
          canonical_sha256(r1["detection_funnel"]) == canonical_sha256(r2["detection_funnel"]))


def test_ranking_is_structural_only_no_edge_fields():
    """sec.10: il gate non deve MAI produrre un campo che assomigli a
    uno score di edge/profittabilita'."""
    spec = _minimal_spec()
    result = evaluate_family_structural_feasibility(spec)
    forbidden_substrings = ["expected_profit", "edge_score", "likelihood_of_success", "win_rate", "profitability"]
    flat = json.dumps(result).lower()
    for token in forbidden_substrings:
        check(f"no_edge_field_{token}", token not in flat)


def test_policy_artifact_matches_code_defaults():
    policy_path = os.path.join(PHASE75_DIR, "sequence_structural_feasibility_policy_v1.json")
    check("policy_artifact_exists", os.path.exists(policy_path))
    with open(policy_path, encoding="utf-8") as f:
        policy = json.load(f)
    payload = policy["payload"]
    check("policy_hash_matches_payload", policy["canonical_sha256"] == canonical_sha256(payload))
    thresholds = payload["thresholds"]
    check("policy_feasible_margin_matches_code",
          thresholds["feasible_margin_multiplier"]["value"] == DEFAULT_POLICY["feasible_margin_multiplier"])
    check("policy_episode_retention_floor_matches_code",
          thresholds["episode_retention_borderline_floor"]["value"] == DEFAULT_POLICY["episode_retention_borderline_floor"])
    check("policy_independence_retention_floor_matches_code",
          thresholds["independence_retention_borderline_floor"]["value"] ==
          DEFAULT_POLICY["independence_retention_borderline_floor"])


def test_gate_module_never_imports_outcome_data():
    """Controllo statico: il modulo del gate non deve importare/riferire
    percorsi di outcome/validation NEXUS reali - solo row index e feature
    di stato strutturali."""
    gate_path = os.path.join(ROOT, "server", "research_scripts", "phase7", "engine",
                              "sequence_structural_feasibility_gate.py")
    with open(gate_path, encoding="utf-8") as f:
        content = f.read()
    banned = ["outcome_surface_v3", "nxs_m15_gold", "load_outcomes", "validation_access_ledger"]
    for token in banned:
        check(f"gate_does_not_import_{token}", token not in content)


def main():
    test_missing_fields_never_invented()
    test_seq0015_published_geometry_structural_replay()
    test_feasible_ample_geometry()
    test_not_testable_below_minimum_even_without_clustering()
    test_borderline_thin_margin()
    test_geometry_guard_is_not_a_fixed_percentage()
    test_cluster_geometry_fields_present()
    test_matching_preflight_determinism_and_reuse_cap()
    test_provenance_and_determinism()
    test_ranking_is_structural_only_no_edge_fields()
    test_policy_artifact_matches_code_defaults()
    test_gate_module_never_imports_outcome_data()

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Phase 7.5A Sequence Structural Feasibility Gate regression suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
