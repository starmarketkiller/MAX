#!/usr/bin/env python3
"""Phase 7.5A - Sequence Structural Feasibility Gate: regression suite
(v2, post Structural Gate Integration & Geometry Semantics Patch).

Interamente su dati SINTETICI (nessun dato NEXUS, nessun outcome). Il
"replay" della geometria SEQ-0015 usa solo i conteggi GIA' PUBBLICATI
(EVENT_VIEW=249, embargo=39, minimum=30) per verificare che il gate
generale li avrebbe segnalati - non e' una nuova indagine su SEQ-0015
(chiusa, vedi failure_memory_registry_v1.json FAIL-009): nessun outcome
letto, nessun dato reale usato, nessuna nuova conclusione su quella
sequence.

Contiene i 4 controesempi sintetici obbligatori della patch di
integrazione:
  A - gap mediano SOTTO l'embargo ma abbastanza cluster indipendenti
      (dimostra che il proxy del gap mediano non e' sufficiente da solo).
  B - firing rate molto basso ma un solo cluster (NOT_TESTABLE).
  C - geometria FEASIBLE ma pool di matching insufficiente (non READY).
  D - geometria + matching entrambi validi (READY_FOR_PREREGISTRATION)."""
import json
import os
import random
import sys

PHASE75_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE75_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))

from sequence_structural_feasibility_gate import (  # noqa: E402
    evaluate_family_structural_feasibility, missing_spec_fields, missing_matching_spec_fields,
    compute_detection_funnel, compute_cluster_geometry, compute_feasibility_ratios,
    classify_firing_geometry_risk_flag, run_matching_preflight,
    REQUIRED_DETECTOR_GEOMETRY_FIELDS, REQUIRED_MATCHING_SPEC_FIELDS, DEFAULT_POLICY,
    VERDICT_FEASIBLE, VERDICT_BORDERLINE, VERDICT_NOT_TESTABLE, VERDICT_NEEDS_DETECTOR_FORMALIZATION,
    VERDICT_NEEDS_MATCHING_FORMALIZATION, VERDICT_MATCHING_STRUCTURALLY_INFEASIBLE,
    FORMALIZATION_LEVEL_NONE, FORMALIZATION_LEVEL_DETECTOR_GEOMETRY_READY,
    FORMALIZATION_LEVEL_MATCHING_PREFLIGHT_READY,
    MATCHING_STATUS_NOT_DECLARED, MATCHING_STATUS_DECLARED_AWAITING_DATA,
    MATCHING_STATUS_EXECUTED_FEASIBLE, MATCHING_STATUS_EXECUTED_INFEASIBLE,
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


def _matching_spec(**overrides):
    ms = {
        "match_dimensions": ["state"], "k": 3, "minimum_control_count": 5,
        "max_control_reuse_per_run": 10, "state_feature_definitions": {"state": {"source": "TEST"}},
        "control_pool_construction_policy": "TEST_SAME_SPLIT_SAME_DIRECTION",
        "split_boundaries": {"discovery": (0, 1_000_000)},
    }
    ms.update(overrides)
    return ms


def _matching_runtime(event_rows, control_pool):
    return {
        "control_pool": control_pool,
        "control_row_by_id": {c: c for c in control_pool},
        "control_direction_by_id": {c: "BOTH" for c in control_pool},
        "control_features_by_id": {c: {"state": "A"} for c in control_pool},
        "discovery_features_by_row": {c: {"state": "A"} for c in control_pool},
        "event_features_by_row": {r: {"state": "A"} for r in event_rows},
    }


def test_missing_fields_never_invented():
    """Nessun parametro inventato - una family incompleta deve essere
    classificata NEEDS_DETECTOR_FORMALIZATION con l'elenco esatto dei
    campi mancanti, MAI fatta girare con un default silenzioso."""
    empty = {"sequence_family_id": "SEQFAM-EMPTY"}
    missing = missing_spec_fields(empty)
    check("all_required_fields_flagged_when_absent",
          set(missing) == set(REQUIRED_DETECTOR_GEOMETRY_FIELDS) - {"sequence_family_id"},
          f"missing={sorted(missing)}")

    r = evaluate_family_structural_feasibility(empty)
    check("empty_spec_verdict_is_needs_formalization", r["verdict"] == VERDICT_NEEDS_DETECTOR_FORMALIZATION)
    check("empty_spec_formalization_level_none", r["formalization_level"] == FORMALIZATION_LEVEL_NONE)
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


def test_matching_spec_incomplete_never_invented():
    """Stessa filosofia fail-closed applicata al LIVELLO 2 (matching) -
    nessuna dimensione di matching inventata (istruzione esplicita
    sec.2 della patch di integrazione)."""
    empty_matching = {}
    missing = missing_matching_spec_fields(empty_matching)
    check("all_matching_fields_flagged_when_absent", set(missing) == set(REQUIRED_MATCHING_SPEC_FIELDS))

    partial_matching = _matching_spec()
    del partial_matching["max_control_reuse_per_run"]
    del partial_matching["state_feature_definitions"]
    missing2 = missing_matching_spec_fields(partial_matching)
    check("partial_matching_spec_flags_exactly_missing",
          set(missing2) == {"max_control_reuse_per_run", "state_feature_definitions"})


def test_geometry_feasible_without_matching_spec_is_not_feasible():
    """CORREZIONE CENTRALE della patch: prima dell'integrazione, una
    geometria FEASIBLE bastava da sola per il verdetto finale FEASIBLE.
    Ora deve restituire NEEDS_MATCHING_FORMALIZATION - matching_spec e'
    completamente assente dallo spec."""
    spec = _minimal_spec()  # nessun matching_spec, nessun matching_runtime_data
    result = evaluate_family_structural_feasibility(spec)
    check("geometry_alone_is_feasible", result["geometry_verdict"] == VERDICT_FEASIBLE)
    check("final_verdict_is_NOT_feasible_without_matching",
          result["verdict"] == VERDICT_NEEDS_MATCHING_FORMALIZATION,
          f"verdict={result['verdict']} (regressione se questo torna a essere FEASIBLE)")
    check("formalization_level_is_detector_geometry_ready_only",
          result["formalization_level"] == FORMALIZATION_LEVEL_DETECTOR_GEOMETRY_READY)
    check("matching_status_not_declared", result["matching"]["status"] == MATCHING_STATUS_NOT_DECLARED)


def test_matching_spec_declared_but_no_runtime_data():
    """matching_spec completo ma nessuna feature REALE ancora disponibile
    (matching_runtime_data assente) -> DECLARED_AWAITING_DATA, mai
    simulato con dati inventati, verdetto finale resta NEEDS_MATCHING_FORMALIZATION."""
    spec = _minimal_spec(matching_spec=_matching_spec())
    result = evaluate_family_structural_feasibility(spec)
    check("matching_status_declared_awaiting_data", result["matching"]["status"] == MATCHING_STATUS_DECLARED_AWAITING_DATA)
    check("verdict_still_needs_matching_formalization", result["verdict"] == VERDICT_NEEDS_MATCHING_FORMALIZATION)


def test_seq0015_published_geometry_structural_replay():
    """Replay SINTETICO della sola geometria GIA' PUBBLICATA per SEQ-0015.
    Verifica che NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY salta del tutto
    la valutazione del matching (non c'e' nulla di indipendente da matchare)."""
    random.seed(42)
    rows = []
    r = 100
    while len(rows) < 249:
        rows.append(r)
        r += random.randint(1, 8)
    spec = _minimal_spec(
        sequence_family_id="SEQFAM-STRUCTURAL-REPLAY-ONLY-NOT-A-NEW-SEQ0015-RUN",
        event_row_indices=rows[:249],
        discovery_partition={"partition_id": "SYNTHETIC_REPLAY_OF_PUBLISHED_GEOMETRY", "n_bars": 2393},
    )
    result = evaluate_family_structural_feasibility(spec)
    check("replay_verdict_not_testable", result["verdict"] == VERDICT_NOT_TESTABLE, f"verdict={result['verdict']}")
    check("replay_geometry_verdict_not_testable", result["geometry_verdict"] == VERDICT_NOT_TESTABLE)
    check("replay_independent_view_collapses", result["detection_funnel"]["INDEPENDENT_VIEW"]["n"] < 30)
    check("replay_matching_not_evaluated_when_geometry_already_fails",
          result["matching"]["status"] == MATCHING_STATUS_NOT_DECLARED,
          "non ha senso valutare il matching se la geometria e' gia' NOT_TESTABLE")
    check("replay_would_have_caught_it_before_outcome_contract", result["provenance"]["outcome_blind"] is True)


def test_counterexample_A_median_gap_below_embargo_but_enough_clusters():
    """CONTROESEMPIO A (obbligatorio, sec.10 della patch): gap mediano
    SOTTO l'embargo (quindi firing_geometry_risk_flag=True) ma abbastanza
    gap GRANDI da generare >=1.5x il minimo di cluster indipendenti.
    Costruzione: 46 cluster, 138 eventi totali -> 92 gap piccoli (10
    barre, dentro cluster) + 45 gap grandi (100 barre, fra cluster).
    Sorted gaps: la maggioranza (92/137) e' piccola -> mediana=10<=39."""
    rows = []
    r = 0
    n_clusters = 46
    cluster_size = 3
    for c in range(n_clusters):
        for i in range(cluster_size):
            rows.append(r)
            r += 10  # gap interno al cluster, << embargo=39
        if c < n_clusters - 1:
            r += 100 - 10  # gap fra cluster, >> embargo=39 (il -10 compensa il +10 gia' aggiunto sopra)
    spec = _minimal_spec(sequence_family_id="SEQFAM-COUNTEREXAMPLE-A", event_row_indices=rows,
                          discovery_partition={"partition_id": "TEST", "n_bars": max(rows) + 100})
    result = evaluate_family_structural_feasibility(spec)
    gaps = [rows[i + 1] - rows[i] for i in range(len(rows) - 1)]
    check("counterexample_A_setup_median_gap_below_embargo",
          result["firing_geometry_risk_flag"]["median_gap_bars"] <= 39,
          f"median_gap={result['firing_geometry_risk_flag']['median_gap_bars']}")
    check("counterexample_A_risk_flag_is_true", result["firing_geometry_risk_flag"]["risk_flag"] is True)
    check("counterexample_A_independent_units_well_above_minimum",
          result["feasibility_ratios"]["independent_units"] >= 1.5 * 30,
          f"independent_units={result['feasibility_ratios']['independent_units']}")
    check("counterexample_A_geometry_verdict_is_feasible", result["geometry_verdict"] == VERDICT_FEASIBLE,
          "il risk_flag puo' essere true, ma il verdetto di geometria e' comunque FEASIBLE se i gate reali passano")


def test_counterexample_B_low_firing_rate_single_cluster():
    """CONTROESEMPIO B (obbligatorio): firing rate molto basso (eventi
    rari) ma tutti concentrati in un solo blocco -> NOT_TESTABLE, a
    dimostrazione che 'raro' da solo non e' sufficiente per essere ammessi."""
    rare_but_clustered = list(range(1000, 1000 + 20 * 5, 5))  # 20 eventi, gap=5<<39, firing_rate=20/50000
    spec = _minimal_spec(sequence_family_id="SEQFAM-COUNTEREXAMPLE-B", event_row_indices=rare_but_clustered,
                          discovery_partition={"partition_id": "TEST", "n_bars": 50000})
    result = evaluate_family_structural_feasibility(spec)
    check("counterexample_B_firing_rate_is_indeed_sparse", result["detection_funnel"]["firing_rate"] < 0.02)
    check("counterexample_B_verdict_not_testable", result["verdict"] == VERDICT_NOT_TESTABLE,
          f"verdict={result['verdict']}")
    check("counterexample_B_geometry_verdict_not_testable", result["geometry_verdict"] == VERDICT_NOT_TESTABLE)


def test_counterexample_C_geometry_feasible_matching_pool_insufficient():
    """CONTROESEMPIO C (obbligatorio): geometria FEASIBLE ma il pool di
    controllo reale e' troppo piccolo (sotto minimum_control_count) per
    la maggior parte/tutti gli eventi indipendenti -> non READY_FOR_
    PREREGISTRATION (MATCHING_STRUCTURALLY_INFEASIBLE)."""
    rows = list(range(0, 60 * 60, 60))  # stessa geometria ampia del caso feasible
    tiny_pool = list(range(500_000, 500_002))  # 2 controlli, sotto minimum_control_count=5
    spec = _minimal_spec(
        sequence_family_id="SEQFAM-COUNTEREXAMPLE-C", event_row_indices=rows,
        discovery_partition={"partition_id": "TEST", "n_bars": max(rows) + 100},
        matching_spec=_matching_spec(),
        matching_runtime_data=_matching_runtime(rows, tiny_pool),
    )
    result = evaluate_family_structural_feasibility(spec)
    check("counterexample_C_geometry_verdict_feasible", result["geometry_verdict"] == VERDICT_FEASIBLE)
    check("counterexample_C_matching_executed_infeasible",
          result["matching"]["status"] == MATCHING_STATUS_EXECUTED_INFEASIBLE)
    check("counterexample_C_not_ready_for_preregistration",
          result["verdict"] == VERDICT_MATCHING_STRUCTURALLY_INFEASIBLE,
          f"verdict={result['verdict']} - geometria da sola NON deve bastare per FEASIBLE")


def test_counterexample_D_both_geometry_and_matching_valid():
    """CONTROESEMPIO D (obbligatorio): geometria E matching entrambi
    validi -> FEASIBLE (equivalente a READY_FOR_PREREGISTRATION)."""
    rows = list(range(0, 60 * 60, 60))
    ample_pool = list(range(500_000, 500_040))  # 40 controlli, ampio
    spec = _minimal_spec(
        sequence_family_id="SEQFAM-COUNTEREXAMPLE-D", event_row_indices=rows,
        discovery_partition={"partition_id": "TEST", "n_bars": max(rows) + 100},
        matching_spec=_matching_spec(),
        matching_runtime_data=_matching_runtime(rows, ample_pool),
    )
    result = evaluate_family_structural_feasibility(spec)
    check("counterexample_D_geometry_verdict_feasible", result["geometry_verdict"] == VERDICT_FEASIBLE)
    check("counterexample_D_matching_executed_feasible",
          result["matching"]["status"] == MATCHING_STATUS_EXECUTED_FEASIBLE)
    check("counterexample_D_verdict_is_feasible_ready_for_preregistration",
          result["verdict"] == VERDICT_FEASIBLE)
    check("counterexample_D_formalization_level_matching_preflight_ready",
          result["formalization_level"] == FORMALIZATION_LEVEL_MATCHING_PREFLIGHT_READY)
    check("counterexample_D_provenance_has_matching_block", "matching" in result["provenance"])
    for field in ("baseline_engine_version", "matching_spec_hash", "max_control_reuse_per_run", "matching_result_hash"):
        check(f"counterexample_D_matching_provenance_has_{field}", field in result["provenance"]["matching"])


def test_matching_runtime_missing_event_features_fail_closed():
    """Se matching_runtime_data e' dichiarato ma manca la feature per
    anche una sola osservazione indipendente, il gate deve sollevare
    (fail-closed), MAI inventare una feature placeholder."""
    from sequence_structural_feasibility_gate import MatchingRuntimeDataIncompleteError
    rows = list(range(0, 60 * 60, 60))
    ample_pool = list(range(500_000, 500_040))
    runtime = _matching_runtime(rows, ample_pool)
    del runtime["event_features_by_row"][rows[0]]  # rimuove la feature di UN solo evento
    spec = _minimal_spec(event_row_indices=rows,
                          discovery_partition={"partition_id": "TEST", "n_bars": max(rows) + 100},
                          matching_spec=_matching_spec(), matching_runtime_data=runtime)
    try:
        evaluate_family_structural_feasibility(spec)
        check("missing_event_feature_raises", False, "avrebbe dovuto sollevare MatchingRuntimeDataIncompleteError")
    except MatchingRuntimeDataIncompleteError:
        check("missing_event_feature_raises", True)


def test_borderline_thin_margin():
    spec = _minimal_spec(event_row_indices=list(range(0, 32 * 60, 60)))  # 32 unita', minimo=30, <1.5x
    result = evaluate_family_structural_feasibility(spec)
    check("thin_margin_geometry_is_borderline", result["geometry_verdict"] == VERDICT_BORDERLINE,
          f"geometry_verdict={result['geometry_verdict']}, n={result['feasibility_ratios']['independent_units']}")
    check("thin_margin_final_verdict_needs_matching_without_matching_spec",
          result["verdict"] == VERDICT_NEEDS_MATCHING_FORMALIZATION)


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
    check("policy_declares_required_matching_spec_fields",
          set(payload["required_matching_spec_inputs"]["fields"]) == set(REQUIRED_MATCHING_SPEC_FIELDS))


def test_gate_module_never_imports_outcome_data():
    gate_path = os.path.join(ROOT, "server", "research_scripts", "phase7", "engine",
                              "sequence_structural_feasibility_gate.py")
    with open(gate_path, encoding="utf-8") as f:
        content = f.read()
    banned = ["outcome_surface_v3", "nxs_m15_gold", "load_outcomes", "validation_access_ledger"]
    for token in banned:
        check(f"gate_does_not_import_{token}", token not in content)


def test_no_pathological_verdict_word_survives_in_risk_flag():
    """Verifica meccanica della correzione di semantica: il modulo non
    deve piu' contenere la vecchia coppia di verdetti pseudo-autorevoli
    PATHOLOGICAL_FOR_HORIZON/COMPATIBLE_WITH_HORIZON - solo il booleano
    risk_flag diagnostico."""
    gate_path = os.path.join(ROOT, "server", "research_scripts", "phase7", "engine",
                              "sequence_structural_feasibility_gate.py")
    with open(gate_path, encoding="utf-8") as f:
        content = f.read()
    check("no_pathological_for_horizon_verdict_word", "PATHOLOGICAL_FOR_HORIZON" not in content)
    check("no_compatible_with_horizon_verdict_word", "COMPATIBLE_WITH_HORIZON" not in content)
    check("risk_flag_marked_diagnostic_only", "DIAGNOSTIC_ONLY" in content)


def main():
    test_missing_fields_never_invented()
    test_matching_spec_incomplete_never_invented()
    test_geometry_feasible_without_matching_spec_is_not_feasible()
    test_matching_spec_declared_but_no_runtime_data()
    test_seq0015_published_geometry_structural_replay()
    test_counterexample_A_median_gap_below_embargo_but_enough_clusters()
    test_counterexample_B_low_firing_rate_single_cluster()
    test_counterexample_C_geometry_feasible_matching_pool_insufficient()
    test_counterexample_D_both_geometry_and_matching_valid()
    test_matching_runtime_missing_event_features_fail_closed()
    test_borderline_thin_margin()
    test_cluster_geometry_fields_present()
    test_matching_preflight_determinism_and_reuse_cap()
    test_provenance_and_determinism()
    test_ranking_is_structural_only_no_edge_fields()
    test_policy_artifact_matches_code_defaults()
    test_gate_module_never_imports_outcome_data()
    test_no_pathological_verdict_word_survives_in_risk_flag()

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Phase 7.5A Sequence Structural Feasibility Gate regression suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
