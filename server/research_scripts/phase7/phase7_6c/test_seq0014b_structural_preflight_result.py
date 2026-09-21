#!/usr/bin/env python3
"""Phase 7.6C - SEQ-0014B structural preflight RESULT: consistency checks
+ test sintetico OBBLIGATORIO del no-double-counting invariant (sec.7
della richiesta: famiglia A indipendente da sola, famiglia B indipendente
da sola, ma righe sottostanti condivise - il conteggio pooled DEVE
collassare, mai sommare ingenuamente)."""
import os
import sys

PHASE76C_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE76C_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE76C_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_5"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402
from dependence_diagnostics import assign_clusters  # noqa: E402
from sequence_structural_feasibility_gate import compute_detection_funnel  # noqa: E402

sys.path.insert(0, PHASE76C_DIR)
from build_seq0014b_structural_preflight_result import (  # noqa: E402
    compute_cross_family_pooled_geometry, compute_overlap_audit,
)

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def synthetic_no_double_counting_case():
    """Famiglia A: righe [100,200,300] (gap=100 fra loro, >> embargo=39) -
    internamente indipendente per costruzione (episode_gap_rule_A=2,
    embargo=39: nessuna coppia entro 39 barre). Famiglia B: righe
    [110,210,310] (stesso gap=100 interno, anch'essa internamente
    indipendente da sola) - MA ogni riga di B e' a distanza 10 dalla
    corrispondente riga di A (10<=39=embargo condiviso), quindi le due
    famiglie CONDIVIDONO la stessa realizzazione di mercato sottostante
    (3 eventi di mercato distinti, non 6). Il conteggio pooled corretto
    DEVE collassare a 3 cluster cross-family, MAI sommare 3+3=6."""
    embargo = 39
    natural_horizon = 40
    overlap_policy = "COLLAPSE_TO_FIRST"

    rows_a = [100, 200, 300]
    rows_b = [110, 210, 310]
    direction_a = {r: "BUY" for r in rows_a}
    direction_b = {r: "BUY" for r in rows_b}

    funnel_a = compute_detection_funnel(
        event_row_indices=rows_a, n_bars=1000, episode_gap_rule=2, natural_horizon=natural_horizon,
        overlap_policy=overlap_policy, outcome_overlap_embargo_bars=embargo, direction_by_row=direction_a,
    )
    funnel_b = compute_detection_funnel(
        event_row_indices=rows_b, n_bars=1000, episode_gap_rule=2, natural_horizon=natural_horizon,
        overlap_policy=overlap_policy, outcome_overlap_embargo_bars=embargo, direction_by_row=direction_b,
    )

    within_family_geometry = {
        "FAMILY_A": {"CHOPPY": funnel_a, "TRENDING": _empty_like(funnel_a)},
        "FAMILY_B": {"CHOPPY": funnel_b, "TRENDING": _empty_like(funnel_b)},
    }
    spec = {"cross_family_dependence_clustering": {"threshold_bars": embargo}}
    records = (
        [{"setup_family_id": "FAMILY_A", "row_index": r} for r in rows_a] +
        [{"setup_family_id": "FAMILY_B", "row_index": r} for r in rows_b]
    )
    pooled = compute_cross_family_pooled_geometry(records, within_family_geometry, spec)
    return funnel_a, funnel_b, pooled


def _empty_like(funnel):
    return {
        "n_bars": funnel["n_bars"], "n_raw_events": 0, "firing_rate": 0.0,
        "gap_stats": {"median_gap_bars": None, "p10": None, "p25": None, "p50": None, "p75": None, "p90": None},
        "EVENT_VIEW": {"n": 0}, "EPISODE_VIEW": {"n": 0, "n_episodes": 0, "representative_rows": []},
        "INDEPENDENT_VIEW": {"n": 0, "n_independent_observations": 0, "representative_rows": [], "direction_by_row": {}},
        "episode_gap_rule": funnel["episode_gap_rule"], "natural_horizon": funnel["natural_horizon"],
        "overlap_policy": funnel["overlap_policy"], "outcome_overlap_embargo_bars": funnel["outcome_overlap_embargo_bars"],
    }


def main():
    # ================= TEST SINTETICO OBBLIGATORIO (no-double-counting) =================
    funnel_a, funnel_b, pooled = synthetic_no_double_counting_case()
    check("synthetic_family_A_independent_alone", funnel_a["INDEPENDENT_VIEW"]["n"] == 3,
          f"got {funnel_a['INDEPENDENT_VIEW']['n']}")
    check("synthetic_family_B_independent_alone", funnel_b["INDEPENDENT_VIEW"]["n"] == 3,
          f"got {funnel_b['INDEPENDENT_VIEW']['n']}")
    naive_sum = funnel_a["INDEPENDENT_VIEW"]["n"] + funnel_b["INDEPENDENT_VIEW"]["n"]
    check("synthetic_naive_sum_would_be_6", naive_sum == 6)
    check("synthetic_pooled_collapses_to_3_not_6",
          pooled["no_double_counting_check"]["CHOPPY_pooled_independent_units"] == 3,
          f"got {pooled['no_double_counting_check']['CHOPPY_pooled_independent_units']}")
    check("synthetic_no_double_counting_invariant_holds",
          pooled["no_double_counting_check"]["CHOPPY_invariant_holds"] is True)
    check("synthetic_collapse_is_strict_less_than",
          pooled["no_double_counting_check"]["CHOPPY_pooled_independent_units"] <
          pooled["no_double_counting_check"]["CHOPPY_sum_family_independent_units_naive"])

    # A negative control: se A e B NON condividessero righe vicine (es. B a [500,600,700],
    # lontano da A), il pooled DEVE invece dare 6, non collassare artificiosamente.
    rows_a2 = [100, 200, 300]
    rows_b2 = [500, 600, 700]
    funnel_a2 = compute_detection_funnel(rows_a2, 1000, 2, 40, "COLLAPSE_TO_FIRST", 39, {r: "BUY" for r in rows_a2})
    funnel_b2 = compute_detection_funnel(rows_b2, 1000, 2, 40, "COLLAPSE_TO_FIRST", 39, {r: "BUY" for r in rows_b2})
    within2 = {"FAMILY_A": {"CHOPPY": funnel_a2, "TRENDING": _empty_like(funnel_a2)},
               "FAMILY_B": {"CHOPPY": funnel_b2, "TRENDING": _empty_like(funnel_b2)}}
    records2 = ([{"setup_family_id": "FAMILY_A", "row_index": r} for r in rows_a2] +
                [{"setup_family_id": "FAMILY_B", "row_index": r} for r in rows_b2])
    pooled2 = compute_cross_family_pooled_geometry(records2, within2, {"cross_family_dependence_clustering": {"threshold_bars": 39}})
    check("synthetic_negative_control_no_collapse_when_rows_far_apart",
          pooled2["no_double_counting_check"]["CHOPPY_pooled_independent_units"] == 6,
          f"got {pooled2['no_double_counting_check']['CHOPPY_pooled_independent_units']}")

    # ================= CONSISTENZA DEL RESULT ARTIFACT REALE =================
    doc_path = os.path.join(PHASE76C_DIR, "seq0014b_structural_preflight_result_v1.json")
    doc = load_json(doc_path)
    p = doc["payload"]
    check("canonical_hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))
    check("spec_commit_reference_present", "seq0014b_structural_preflight_spec_v1.json" in p["spec_commit_reference"])
    check("development_discovery_row_range_matches_known_value", p["development_discovery_row_range"] == [396, 2789])
    check("n_bars_discovery_matches_known_value", p["n_bars_discovery"] == 2393)

    # ---- base counts: coerenza interna (CHOPPY+TRENDING+MED = totale scope, per famiglia e overall) ----
    bc = p["base_counts"]
    check("overall_choppy_plus_trending_equals_total",
          bc["overall"]["n_CHOPPY"] + bc["overall"]["n_TRENDING"] == bc["overall"]["n_total"])
    for fam, b in bc["per_family"].items():
        check(f"{fam}_choppy_plus_trending_equals_total", b["n_CHOPPY"] + b["n_TRENDING"] == b["n_total"])
    check("overall_total_equals_sum_of_family_totals",
          bc["overall"]["n_total"] == sum(b["n_total"] for b in bc["per_family"].values()))
    check("overall_med_equals_sum_of_family_med",
          bc["overall"]["n_MED_excluded"] == sum(b["n_MED_excluded"] for b in bc["per_family"].values()))

    # ---- overlap audit: obbligatorio, fraction ben definita, secondary diagnostic strutturalmente 0 ----
    oa = p["overlap_audit"]
    check("overlap_audit_present_with_required_fields",
          all(k in oa for k in ("n_unique_rows_with_exactly_1_family", "n_unique_rows_with_2_or_more_families",
                                  "max_families_on_a_single_row", "family_combination_distribution_on_shared_rows",
                                  "fraction_setup_records_sharing_a_row_with_another_family")))
    check("overlap_audit_max_families_at_least_2", oa["max_families_on_a_single_row"] >= 2,
          "conferma empirica del concern del reviewer (bar 1500-style co-firing)")
    check("overlap_audit_secondary_diagnostic_is_zero_as_expected_structurally",
          oa["secondary_diagnostic_med_excluded_rows_also_colocated_with_a_non_med_family"] == 0)

    # ---- within-family geometry: EVENT>=EPISODE>=INDEPENDENT per ogni famiglia x regime ----
    for fam, by_regime in p["within_family_geometry"].items():
        for regime, funnel in by_regime.items():
            check(f"{fam}_{regime}_event_geq_episode_geq_independent",
                  funnel["EVENT_VIEW"]["n"] >= funnel["EPISODE_VIEW"]["n"] >= funnel["INDEPENDENT_VIEW"]["n"])

    # ---- cross-family pooled geometry: invariant deve reggere (mai bug), collasso rilevato ----
    cfg = p["cross_family_pooled_geometry"]
    ndc = cfg["no_double_counting_check"]
    check("pooled_independent_units_leq_naive_sum", ndc["invariant_holds"] is True)
    check("choppy_pooled_leq_naive_sum", ndc["CHOPPY_invariant_holds"] is True)
    check("trending_pooled_leq_naive_sum", ndc["TRENDING_invariant_holds"] is True)
    check("cross_family_collapse_detected_on_real_data", ndc["cross_family_collapse_detected"] is True,
          "atteso vista l'alta densita' di PULLBACK/VOLATILITY_EXPANSION")

    # ---- verdetto composito: stati family-level MAI collassati in un solo verde ----
    ov = p["overall_structural_verdict"]
    check("per_family_verdicts_cover_all_6_families", set(ov["per_family_verdicts"].keys()) ==
          set(p["base_counts"]["per_family"].keys()))
    check("needs_arm_size_policy_always_present", "NEEDS_ARM_SIZE_POLICY" in ov["composite_verdict_states"])
    check("family_level_failures_not_hidden_if_any_present",
          (any(v != "FAMILY_LEVEL_FEASIBLE" for v in ov["per_family_verdicts"].values()) ==
           any(s in ov["composite_verdict_states"] for s in ("FAMILY_LEVEL_INSUFFICIENT", "MATCHING_STRUCTURALLY_INFEASIBLE"))))

    # ---- hard stop / status coherence ----
    check("hard_stop_flag_matches_status",
          p["hard_stop_triggered"] == (p["seq0014b_status"] == "NOT_TESTABLE_WITH_FROZEN_SETUP_POPULATION"))
    check("status_is_one_of_two_valid_values",
          p["seq0014b_status"] in ("NOT_TESTABLE_WITH_FROZEN_SETUP_POPULATION",
                                    "STRUCTURALLY_FEASIBLE_AWAITING_STATISTICAL_PREREGISTRATION"))

    # ---- failure-memory/RECLAIM: nessun impatto sulla geometria, no primary outcome, no discovery ----
    check("no_outcome_accessed_flag", p["no_nexus_outcome_data_accessed"] is True)
    check("no_edge_discovery_flag", p["no_edge_discovery_performed"] is True)
    check("no_primary_outcome_selected_flag", p["no_primary_outcome_selected"] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- verifica statica: il builder non legge/calcola mai outcome ----
    builder_path = os.path.join(PHASE76C_DIR, "build_seq0014b_structural_preflight_result.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_opens_outcomes_csv", "OUTCOMES_PATH" not in builder_src and "outcomes_v1" not in builder_src)
    check("builder_never_imports_outcome_computation",
          "load_outcomes" not in builder_src and "compute_outcome" not in builder_src)
    check("builder_never_reads_directional_efficiency_for_matching",
          "directional_efficiency" not in builder_src.split("def run_same_family_matching")[1].split("def ")[0],
          "il matching deve usare SOLO volatility_state_pre_setup (atr_percentile), mai la feature che "
          "definisce il regime - evita la tautologia")

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== SEQ-0014B structural preflight result consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
