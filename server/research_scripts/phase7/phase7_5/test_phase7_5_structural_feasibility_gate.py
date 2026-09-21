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
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_5"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))

from sequence_structural_feasibility_gate import (  # noqa: E402
    evaluate_family_structural_feasibility, missing_spec_fields, missing_matching_spec_fields,
    compute_detection_funnel, compute_cluster_geometry, compute_feasibility_ratios,
    classify_firing_geometry_risk_flag, run_matching_preflight, resolve_direction_by_row,
    REQUIRED_DETECTOR_GEOMETRY_FIELDS, REQUIRED_MATCHING_SPEC_FIELDS, DEFAULT_POLICY,
    VERDICT_FEASIBLE, VERDICT_BORDERLINE, VERDICT_NOT_TESTABLE, VERDICT_NEEDS_DETECTOR_FORMALIZATION,
    VERDICT_NEEDS_MATCHING_FORMALIZATION, VERDICT_MATCHING_STRUCTURALLY_INFEASIBLE,
    FORMALIZATION_LEVEL_NONE, FORMALIZATION_LEVEL_DETECTOR_GEOMETRY_READY,
    FORMALIZATION_LEVEL_MATCHING_SPEC_READY_AWAITING_RUNTIME_DATA, FORMALIZATION_LEVEL_MATCHING_PREFLIGHT_READY,
    MATCHING_STATUS_NOT_DECLARED, MATCHING_STATUS_DECLARED_AWAITING_DATA,
    MATCHING_STATUS_EXECUTED_FEASIBLE, MATCHING_STATUS_EXECUTED_INFEASIBLE,
    DIRECTION_POLICY_FIXED_BUY, DIRECTION_POLICY_FIXED_SELL, DIRECTION_POLICY_NON_DIRECTIONAL,
    DIRECTION_POLICY_PER_EVENT, VALID_EVENT_DIRECTION_POLICIES, DirectionDerivationError,
)
from canonical_utils import canonical_sha256  # noqa: E402
from sequence_baseline_adapter_v1 import SequenceBaselineAdapter  # noqa: E402
from dependence_diagnostics import assign_clusters  # noqa: E402

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
        "event_direction_policy": DIRECTION_POLICY_FIXED_BUY,
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
    # NOTA (Directional Matching Fidelity Final Patch): control_direction_by_id
    # NON e' piu' un campo di matching_runtime_data - run_matching_preflight lo
    # costruisce internamente PER OGNI evento (direction-conditioned counterfactual,
    # replica esatta di SequenceBaselineAdapter), mai una mappa globale unica.
    return {
        "control_pool": control_pool,
        "control_row_by_id": {c: c for c in control_pool},
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
    check("cluster_geometry_has_n_episode_clusters", "n_episode_clusters" in geo)
    check("cluster_geometry_has_raw_block", "raw_event_embargo_geometry" in geo)
    check("cluster_geometry_has_inferential_block", "inferential_independent_geometry" in geo)

    raw = geo["raw_event_embargo_geometry"]
    for field in ("n_clusters", "cluster_size_distribution", "max_cluster_size", "median_cluster_size",
                  "fraction_events_in_largest_cluster", "fraction_gaps_below_embargo",
                  "longest_no_event_gap_bars"):
        check(f"raw_geometry_has_{field}", field in raw)
    check("longest_gap_reflects_the_isolated_tail", raw["longest_no_event_gap_bars"] >= 9800)

    inf = geo["inferential_independent_geometry"]
    for field in ("n_independent_clusters", "cluster_size_distribution", "max_cluster_size",
                  "median_cluster_size", "fraction_episode_representatives_in_largest_cluster",
                  "fraction_gaps_below_embargo", "longest_no_episode_gap"):
        check(f"inferential_geometry_has_{field}", field in inf)


def test_cluster_geometry_invariant_matches_independent_view():
    """CORREZIONE (Cluster Geometry Consistency Patch, post-review): il
    bug originale confondeva la geometria raw-event-embargo con quella
    inferenziale (episode representatives). Verifica l'invariant
    esplicito ORA imposto meccanicamente in evaluate_family_structural_
    feasibility - deve valere per costruzione su QUALUNQUE spec valido."""
    spec = _minimal_spec(event_row_indices=list(range(0, 60 * 60, 60)))
    result = evaluate_family_structural_feasibility(spec)
    inf_n = result["cluster_geometry"]["inferential_independent_geometry"]["n_independent_clusters"]
    check("inferential_n_matches_independent_view_n", inf_n == result["detection_funnel"]["INDEPENDENT_VIEW"]["n"],
          f"inferential={inf_n}, INDEPENDENT_VIEW.n={result['detection_funnel']['INDEPENDENT_VIEW']['n']}")


def test_cluster_geometry_raw_and_inferential_can_genuinely_differ():
    """CONTROESEMPIO OBBLIGATORIO (sec.6 della review): costruire eventi
    dove il clustering diretto dei raw event con embargo produce un
    conteggio DIVERSO dal clustering dei rappresentanti di EPISODE_VIEW
    con lo stesso embargo - riproduce lo stesso meccanismo del bug reale
    (SEQ-0009: 8 raw vs 10 inferential) su un caso piccolo, verificato
    per costruzione (non a mano).

    Costruzione: 3 mini-episodi di 2 eventi ravvicinati (gap interno=1),
    separati da gap=3 fra un mini-episodio e il successivo -> raw_rows=
    [100,101, 104,105, 108,109]. episode_gap_rule=1 (solo eventi
    CONSECUTIVI, gap<=1, nello stesso episodio) -> 3 episodi, uno per
    mini-cluster, rappresentanti (COLLAPSE_TO_FIRST) = [100, 104, 108].
    embargo=3:
      - raw-event embargo clustering (soglia 3 sui 6 raw row): i gap
        alternano 1,3,1,3,1 - TUTTI <=3, quindi transitivamente
        collassano in 1 SOLO cluster (esattamente il meccanismo del bug:
        i micro-gap=1 'ponteggiano' i gap=3 in un'unica catena).
      - inferential embargo clustering (soglia 3 sui 3 rappresentanti
        [100,104,108]): gap=4 fra ciascuno, 4>3 -> NESSUNO si unisce,
        3 cluster distinti (i micro-gap che 'ponteggiavano' la catena
        raw sono stati gia' rimossi dalla rappresentazione episodica)."""
    raw_rows = []
    r = 100
    for _ in range(3):
        raw_rows.append(r)
        raw_rows.append(r + 1)
        r += 4  # gap fra mini-cluster = 4-1 = 3 (fra l'ultimo evento di uno e il primo del successivo)
    episode_gap_rule = 1
    embargo = 3  # < gap fra rappresentanti (che e' 4), ma i raw-event singoli hanno gap=1 o 3 fra loro

    episode_clusters, _ = assign_clusters(sorted(raw_rows), episode_gap_rule)
    episode_representatives = sorted(c[0] for c in episode_clusters)
    raw_clusters, _ = assign_clusters(sorted(raw_rows), embargo)
    inferential_clusters, _ = assign_clusters(episode_representatives, embargo)

    check("counterexample_setup_produces_divergence", len(raw_clusters) != len(inferential_clusters),
          f"raw_rows={raw_rows}, episode_representatives={episode_representatives}, "
          f"n_raw_clusters={len(raw_clusters)}, n_inferential_clusters={len(inferential_clusters)} - "
          f"se questo fallisce, il caso sintetico va aggiustato, non il gate")

    geometry = compute_cluster_geometry(raw_rows, episode_representatives, episode_gap_rule, embargo)
    check("bug_reproduced_raw_differs_from_inferential",
          geometry["raw_event_embargo_geometry"]["n_clusters"] !=
          geometry["inferential_independent_geometry"]["n_independent_clusters"],
          f"raw={geometry['raw_event_embargo_geometry']['n_clusters']}, "
          f"inferential={geometry['inferential_independent_geometry']['n_independent_clusters']}")
    check("inferential_matches_direct_recomputation",
          geometry["inferential_independent_geometry"]["n_independent_clusters"] == len(inferential_clusters))


def test_matching_preflight_per_event_control_pool():
    """Phase 7.5B - control_pool_by_event_row (bug concreto trovato
    applicando il gate a SEQ-0009): l'esclusione per sovrapposizione
    outcome e' PER-EVENTO (dipende dalla riga t di quell'evento), non
    globale - due eventi devono poter ricevere pool di controllo
    DIVERSI nella stessa run. Retro-compatibilita' verificata: senza
    l'argomento, il comportamento resta quello di un pool condiviso."""
    boundaries = {"discovery": (0, 1_000_000)}
    pool_e1 = [500_000, 500_001, 500_002]
    pool_e2 = [600_000, 600_001, 600_002]
    row_by_id = {c: c for c in pool_e1 + pool_e2}
    feat_by_id = {c: {"state": "A"} for c in pool_e1 + pool_e2}
    discovery_feats = {c: {"state": "A"} for c in pool_e1 + pool_e2}
    events = [{"event_id": "E1", "event_row": 0, "direction": "BUY", "features": {"state": "A"}},
              {"event_id": "E2", "event_row": 100, "direction": "BUY", "features": {"state": "A"}}]

    preflight = run_matching_preflight(
        match_dimensions=["state"], k=3, split_boundaries=boundaries, events=events,
        control_pool=pool_e1 + pool_e2, control_row_by_id=row_by_id, control_features_by_id=feat_by_id,
        discovery_features_by_row=discovery_feats, minimum_control_count=3, max_control_reuse_per_run=10,
        control_pool_by_event_row={0: pool_e1, 100: pool_e2},
    )
    e1_picks = set(m["control_id"] for m in preflight["event_match_results"][0]["matches"])
    e2_picks = set(m["control_id"] for m in preflight["event_match_results"][1]["matches"])
    check("per_event_pool_e1_only_from_its_own_pool", e1_picks <= set(pool_e1), f"{e1_picks}")
    check("per_event_pool_e2_only_from_its_own_pool", e2_picks <= set(pool_e2), f"{e2_picks}")
    check("per_event_pool_no_cross_contamination", e1_picks.isdisjoint(pool_e2) and e2_picks.isdisjoint(pool_e1))

    # Retro-compatibilita': senza control_pool_by_event_row, comportamento invariato (pool condiviso).
    shared_preflight = run_matching_preflight(
        match_dimensions=["state"], k=3, split_boundaries=boundaries, events=events,
        control_pool=pool_e1, control_row_by_id={c: c for c in pool_e1}, control_features_by_id=feat_by_id,
        discovery_features_by_row=discovery_feats, minimum_control_count=3, max_control_reuse_per_run=10,
    )
    check("shared_pool_backward_compatible", shared_preflight["n_events"] == 2)


def test_matching_preflight_determinism_and_reuse_cap():
    boundaries = {"discovery": (0, 200), "internal_validation": (200, 280),
                  "locked_validation": (280, 360), "final_holdout": (360, 440)}
    pool = [100, 102, 104, 106, 108, 110]
    row_by_id = {c: c for c in pool}
    feat_by_id = {c: {"volatility_state": "HIGH"} for c in pool}
    discovery_feats = {i: {"volatility_state": "HIGH" if i % 2 == 0 else "LOW"} for i in range(0, 200, 2)}
    events = [{"event_id": f"EVT-{i}", "event_row": 10 + i, "direction": "BUY",
               "features": {"volatility_state": "HIGH"}} for i in range(4)]

    preflight = run_matching_preflight(
        match_dimensions=["volatility_state"], k=2, split_boundaries=boundaries, events=events,
        control_pool=pool, control_row_by_id=row_by_id,
        control_features_by_id=feat_by_id, discovery_features_by_row=discovery_feats,
        minimum_control_count=2, max_control_reuse_per_run=2,
    )
    check("preflight_tie_break_deterministic", preflight["tie_break_deterministic"] is True)
    check("preflight_reuse_within_declared_cap", preflight["max_reuse_within_declared_cap"] is True)
    check("preflight_reports_n_matched", preflight["n_matched"] + preflight["n_rejected_insufficient_pool"] == 4)


def test_shuffled_control_pool_order_still_deterministic():
    """sec.10 - stesso pool, ordine shuffled -> stessi risultati (nessuna
    dipendenza implicita dall'ordine del control_pool passato)."""
    boundaries = {"discovery": (0, 1_000_000)}
    pool = list(range(500_000, 500_010))
    row_by_id = {c: c for c in pool}
    feat_by_id = {c: {"state": "A"} for c in pool}
    discovery_feats = {c: {"state": "A"} for c in pool}
    events = [{"event_id": "E1", "event_row": 0, "direction": "BUY", "features": {"state": "A"}}]

    ordered = run_matching_preflight(match_dimensions=["state"], k=3, split_boundaries=boundaries, events=events,
                                      control_pool=list(pool), control_row_by_id=row_by_id,
                                      control_features_by_id=feat_by_id, discovery_features_by_row=discovery_feats,
                                      minimum_control_count=2, max_control_reuse_per_run=5)
    shuffled_pool = list(pool)
    random.Random(11).shuffle(shuffled_pool)
    shuffled = run_matching_preflight(match_dimensions=["state"], k=3, split_boundaries=boundaries, events=events,
                                       control_pool=shuffled_pool, control_row_by_id=row_by_id,
                                       control_features_by_id=feat_by_id, discovery_features_by_row=discovery_feats,
                                       minimum_control_count=2, max_control_reuse_per_run=5)
    ordered_picks = sorted(m["control_id"] for m in ordered["event_match_results"][0]["matches"])
    shuffled_picks = sorted(m["control_id"] for m in shuffled["event_match_results"][0]["matches"])
    check("shuffled_control_pool_same_picks", ordered_picks == shuffled_picks, f"{ordered_picks} vs {shuffled_picks}")


def test_direction_fixed_buy_never_becomes_both():
    """sec.5 - event_direction_policy=FIXED_BUY: TUTTE le righe indipendenti
    devono ricevere direzione 'BUY', mai il vecchio fallback silenzioso 'BOTH'."""
    rows = list(range(0, 60 * 60, 60))
    resolved = resolve_direction_by_row(DIRECTION_POLICY_FIXED_BUY, None, rows)
    check("fixed_buy_all_rows_are_buy", all(v == "BUY" for v in resolved.values()))
    check("fixed_buy_no_row_is_both", all(v != "BOTH" for v in resolved.values()))

    spec = _minimal_spec(event_direction_policy=DIRECTION_POLICY_FIXED_BUY, event_row_indices=rows)
    result = evaluate_family_structural_feasibility(spec)
    check("fixed_buy_funnel_direction_by_row_all_buy",
          all(v == "BUY" for v in result["detection_funnel"]["INDEPENDENT_VIEW"]["direction_by_row"].values()))


def test_direction_fixed_sell():
    rows = list(range(0, 60 * 60, 60))
    resolved = resolve_direction_by_row(DIRECTION_POLICY_FIXED_SELL, None, rows)
    check("fixed_sell_all_rows_are_sell", all(v == "SELL" for v in resolved.values()))


def test_direction_non_directional_explicit():
    """event_direction_policy=NON_DIRECTIONAL e' un valore ESPLICITAMENTE
    dichiarato (non un default silenzioso) - risultato identico (BOTH per
    riga) ma per una ragione dichiarata, verificabile via missing_spec_fields."""
    rows = list(range(0, 60 * 60, 60))
    resolved = resolve_direction_by_row(DIRECTION_POLICY_NON_DIRECTIONAL, None, rows)
    check("non_directional_all_rows_are_both", all(v == "BOTH" for v in resolved.values()))
    spec = _minimal_spec(event_direction_policy=DIRECTION_POLICY_NON_DIRECTIONAL, event_row_indices=rows)
    check("non_directional_is_valid_canonical_policy", missing_spec_fields(spec) == [])


def test_per_event_direction_missing_row_fails_closed():
    """sec.6 - 50 righe indipendenti, direction_by_row ne contiene 49 ->
    fail-closed (NEEDS_DETECTOR_FORMALIZATION), nessun default per la 50-esima."""
    rows = list(range(0, 50 * 60, 60))
    incomplete_map = {r: ("BUY" if i % 2 == 0 else "SELL") for i, r in enumerate(rows[:-1])}  # manca l'ultima
    check("per_event_missing_row_raises",
          _raises(DirectionDerivationError, resolve_direction_by_row, DIRECTION_POLICY_PER_EVENT,
                  incomplete_map, rows))
    spec = _minimal_spec(event_direction_policy=DIRECTION_POLICY_PER_EVENT, direction_by_row=incomplete_map,
                          event_row_indices=rows,
                          discovery_partition={"partition_id": "TEST", "n_bars": max(rows) + 100})
    result = evaluate_family_structural_feasibility(spec)
    check("per_event_missing_row_verdict_needs_formalization",
          result["verdict"] == VERDICT_NEEDS_DETECTOR_FORMALIZATION, f"verdict={result['verdict']}")


def _raises(exc_type, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
        return False
    except exc_type:
        return True


def test_invalid_event_direction_policy_rejected():
    """Vecchi valori narrativi ("BOTH"/"CONTEXT_DEPENDENT" dal registry
    Phase 7.2) non sono piu' ammessi come event_direction_policy per
    QUESTO gate - devono essere sostituiti da uno dei 4 valori canonici."""
    spec = _minimal_spec(event_direction_policy="BOTH")
    missing = missing_spec_fields(spec)
    check("legacy_both_value_rejected", any("event_direction_policy" in m for m in missing), f"missing={missing}")
    spec2 = _minimal_spec(event_direction_policy="CONTEXT_DEPENDENT")
    missing2 = missing_spec_fields(spec2)
    check("legacy_context_dependent_value_rejected", any("event_direction_policy" in m for m in missing2))

    def _valid_for_policy(policy):
        rows = list(range(0, 60 * 60, 60))
        extra = {"direction_by_row": {r: "BUY" for r in rows}} if policy == DIRECTION_POLICY_PER_EVENT else {}
        return missing_spec_fields(_minimal_spec(event_direction_policy=policy, event_row_indices=rows, **extra)) == []

    check("all_four_canonical_values_are_valid", all(_valid_for_policy(p) for p in VALID_EVENT_DIRECTION_POLICIES))


def test_matching_preflight_replicates_sequence_baseline_adapter_direction_semantics():
    """CONTROESEMPIO OBBLIGATORIO (sec.3-4 della review): E1=BUY, E2=SELL
    sullo STESSO pool di controlli - verifica PARITA' DIRETTA contro la
    pipeline reale (SequenceBaselineAdapter), non solo auto-consistenza
    interna del preflight.

    minimum_control_count=20 (il default di classe di BaselineEngineV4,
    l'UNICO che SequenceBaselineAdapter puo' usare - non lo espone come
    parametro) e pool>=20: la parita' qui verificata riguarda SOLO la
    semantica direzionale (control_direction_by_id per-evento), non il
    diverso minimum_control_count che matching_spec puo' dichiarare
    altrove (motivo per cui il preflight usa BaselineEngineV4
    direttamente invece di instradare sempre attraverso l'adapter)."""
    boundaries = {"discovery": (0, 1_000_000)}
    pool = list(range(500_000, 500_025))
    row_by_id = {c: c for c in pool}
    feat_by_id = {c: {"state": "A"} for c in pool}
    discovery_feats = {c: {"state": "A"} for c in pool}

    events_raw = [
        {"sequence_event_id": "E1", "event_a_index": 0, "direction": "BUY", "state_snapshot": {"state": "A"}},
        {"sequence_event_id": "E2", "event_a_index": 60, "direction": "SELL", "state_snapshot": {"state": "A"}},
    ]
    adapter = SequenceBaselineAdapter(match_dimensions=["state"], k=3, split_boundaries=boundaries,
                                       max_control_reuse_per_run=10)
    adapter.fit_on_discovery_only(discovery_feats)
    adapter_results = [adapter.match_sequence_event(ev, pool, row_by_id, feat_by_id) for ev in events_raw]

    events_for_preflight = [
        {"event_id": ev["sequence_event_id"], "event_row": ev["event_a_index"], "direction": ev["direction"],
         "features": ev["state_snapshot"]} for ev in events_raw
    ]
    preflight = run_matching_preflight(
        match_dimensions=["state"], k=3, split_boundaries=boundaries, events=events_for_preflight,
        control_pool=pool, control_row_by_id=row_by_id, control_features_by_id=feat_by_id,
        discovery_features_by_row=discovery_feats, minimum_control_count=20, max_control_reuse_per_run=10,
    )
    preflight_results = preflight["event_match_results"]
    check("parity_same_number_of_events", len(preflight_results) == len(adapter_results) == 2)
    for i, (ar, pr) in enumerate(zip(adapter_results, preflight_results)):
        check(f"parity_event_{i}_same_status", ar["status"] == pr["status"])
        check(f"parity_event_{i}_same_control_picks",
              sorted(m["control_id"] for m in ar["matches"]) == sorted(m["control_id"] for m in pr["matches"]))

    e1_control_directions = {m["control_id"]: m["control_direction"] for m in preflight_results[0]["matches"]}
    e2_control_directions = {m["control_id"]: m["control_direction"] for m in preflight_results[1]["matches"]}
    check("parity_e1_controls_evaluated_as_buy", all(d == "BUY" for d in e1_control_directions.values()))
    check("parity_e2_controls_evaluated_as_sell", all(d == "SELL" for d in e2_control_directions.values()))

    # Prova decisiva, isolata su un pool minuscolo (== k) che FORZA
    # entrambi gli eventi a condividere esattamente gli stessi control
    # bar (nessuna scelta di tie-break possibile): lo STESSO control bar
    # deve risultare "BUY" per E1 e "SELL" per E2 - impossibile con una
    # control_direction_by_id globale unica (il bug originale).
    tiny_pool = pool[:3]
    tiny_preflight = run_matching_preflight(
        match_dimensions=["state"], k=3, split_boundaries=boundaries, events=events_for_preflight,
        control_pool=tiny_pool, control_row_by_id=row_by_id, control_features_by_id=feat_by_id,
        discovery_features_by_row=discovery_feats, minimum_control_count=3, max_control_reuse_per_run=10,
    )
    tiny_e1, tiny_e2 = tiny_preflight["event_match_results"]
    tiny_e1_dirs = {m["control_id"]: m["control_direction"] for m in tiny_e1["matches"]}
    tiny_e2_dirs = {m["control_id"]: m["control_direction"] for m in tiny_e2["matches"]}
    shared_controls = set(tiny_e1_dirs) & set(tiny_e2_dirs)
    check("parity_shared_control_bar_gets_different_hypothetical_direction",
          len(shared_controls) == 3 and all(tiny_e1_dirs[c] == "BUY" for c in shared_controls)
          and all(tiny_e2_dirs[c] == "SELL" for c in shared_controls),
          f"controlli condivisi (forzati) fra E1/E2: {shared_controls} - E1={tiny_e1_dirs}, E2={tiny_e2_dirs} - "
          f"dimostra che lo STESSO control bar e' valutato ipotetico BUY per E1 e ipotetico SELL per E2")


def test_declared_awaiting_data_is_not_matching_preflight_ready():
    """sec.7 - bug corretto: matching_spec completo ma matching_runtime_data
    assente NON deve mai essere MATCHING_PREFLIGHT_READY."""
    spec = _minimal_spec(matching_spec=_matching_spec())
    result = evaluate_family_structural_feasibility(spec)
    check("declared_awaiting_data_status", result["matching"]["status"] == MATCHING_STATUS_DECLARED_AWAITING_DATA)
    check("declared_awaiting_data_formalization_level_is_intermediate",
          result["formalization_level"] == FORMALIZATION_LEVEL_MATCHING_SPEC_READY_AWAITING_RUNTIME_DATA)
    check("declared_awaiting_data_is_not_preflight_ready",
          result["formalization_level"] != FORMALIZATION_LEVEL_MATCHING_PREFLIGHT_READY)


def test_executed_feasible_is_matching_preflight_ready():
    rows = list(range(0, 60 * 60, 60))
    ample_pool = list(range(500_000, 500_040))
    spec = _minimal_spec(event_row_indices=rows,
                          discovery_partition={"partition_id": "TEST", "n_bars": max(rows) + 100},
                          matching_spec=_matching_spec(), matching_runtime_data=_matching_runtime(rows, ample_pool))
    result = evaluate_family_structural_feasibility(spec)
    check("executed_feasible_formalization_level_is_preflight_ready",
          result["formalization_level"] == FORMALIZATION_LEVEL_MATCHING_PREFLIGHT_READY)
    check("executed_feasible_status", result["matching"]["status"] == MATCHING_STATUS_EXECUTED_FEASIBLE)


def test_provenance_direction_fields():
    rows = list(range(0, 60 * 60, 60))
    ample_pool = list(range(500_000, 500_040))
    spec = _minimal_spec(event_direction_policy=DIRECTION_POLICY_FIXED_SELL, event_row_indices=rows,
                          discovery_partition={"partition_id": "TEST", "n_bars": max(rows) + 100},
                          matching_spec=_matching_spec(), matching_runtime_data=_matching_runtime(rows, ample_pool))
    result = evaluate_family_structural_feasibility(spec)
    check("provenance_has_direction_derivation", "direction_derivation" in result["provenance"])
    check("provenance_direction_policy_matches_spec",
          result["provenance"]["direction_derivation"]["event_direction_policy"] == DIRECTION_POLICY_FIXED_SELL)
    check("provenance_has_direction_map_hash", "direction_map_hash" in result["provenance"]["direction_derivation"])
    matching_prov = result["provenance"]["matching"]
    for field in ("event_direction_policy", "direction_source", "direction_map_hash",
                  "counterfactual_direction_semantics"):
        check(f"matching_provenance_has_{field}", field in matching_prov)
    check("matching_provenance_counterfactual_flag_true", matching_prov["counterfactual_direction_semantics"] is True)


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
    test_cluster_geometry_invariant_matches_independent_view()
    test_cluster_geometry_raw_and_inferential_can_genuinely_differ()
    test_matching_preflight_determinism_and_reuse_cap()
    test_matching_preflight_per_event_control_pool()
    test_shuffled_control_pool_order_still_deterministic()
    test_direction_fixed_buy_never_becomes_both()
    test_direction_fixed_sell()
    test_direction_non_directional_explicit()
    test_per_event_direction_missing_row_fails_closed()
    test_invalid_event_direction_policy_rejected()
    test_matching_preflight_replicates_sequence_baseline_adapter_direction_semantics()
    test_declared_awaiting_data_is_not_matching_preflight_ready()
    test_executed_feasible_is_matching_preflight_ready()
    test_provenance_direction_fields()
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
