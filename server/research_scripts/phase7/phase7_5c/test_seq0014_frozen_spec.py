#!/usr/bin/env python3
"""Phase 7.5C - SEQ-0014 frozen spec: regression/consistency checks.
Verifica la COERENZA INTERNA dello spec congelato (formule, hash,
confini, evitamento tautologia detector-vs-matching) - NON esegue il
gate strutturale (script separato) e NON legge alcun outcome."""
import os
import sys

PHASE75C_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE75C_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    spec_path = os.path.join(PHASE75C_DIR, "seq0014_frozen_structural_spec_v1.json")
    doc = load_json(spec_path)
    p = doc["payload"]

    check("canonical_hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))

    detector_path = os.path.join(PHASE75C_DIR, "seq0014_state_entry_detector.py")
    check("detector_source_file_exists", os.path.exists(detector_path))
    check("detector_hash_matches_current_file",
          p["detector_provenance"]["source_sha256"] == file_sha256(detector_path))
    check("detector_frozen_true", p["detector_frozen"] is True)

    check("embargo_equals_horizon_minus_1",
          p["proposed_outcome_overlap_embargo_bars"] == p["proposed_natural_horizon"] - 1,
          f"embargo={p['proposed_outcome_overlap_embargo_bars']}, horizon={p['proposed_natural_horizon']}")

    check("episode_gap_rule_not_copied_from_seq0009_or_seq0015",
          p["episode_gap_rule"] not in (2, 3), f"episode_gap_rule={p['episode_gap_rule']}")
    check("natural_horizon_not_copied_from_seq0009_or_seq0015",
          p["proposed_natural_horizon"] != 40, f"natural_horizon={p['proposed_natural_horizon']}")

    check("direction_policy_is_non_directional", p["event_direction_policy"] == "NON_DIRECTIONAL")

    # sec.1 - la trasformazione STATE -> STATE-ENTRY EVENT deve essere esplicita.
    sed = p["state_entry_event_definition"]
    check("state_entry_event_a_defined", "event_a" in sed and "0->1" in sed["event_a"])
    check("state_exit_defined_but_not_an_event", "exit_definition" in sed)
    check("reset_reentry_rule_explicit", "re_entry_and_minimum_reset_rule" in sed)

    # sec.8 - evitamento tautologia: la feature di stato NON deve essere la dimensione di matching.
    state_feature = p["state_definition"]["condition"]
    match_dims = p["matching_spec"]["match_dimensions"]
    check("state_feature_not_used_as_match_dimension",
          "directional_efficiency" in state_feature and
          all("directional_efficiency" not in d for d in match_dims),
          f"state usa directional_efficiency, match_dimensions={match_dims}")
    check("tautology_avoidance_note_present", "tautology_avoidance_note" in p["matching_spec"])

    ms = p["matching_spec"]
    for field in ("match_dimensions", "k", "minimum_control_count", "max_control_reuse_per_run",
                  "state_feature_definitions", "control_pool_construction_policy", "split_boundaries"):
        check(f"matching_spec_has_{field}", field in ms)

    boundaries = ms["split_boundaries"]
    names_in_order = ["discovery", "internal_validation", "locked_validation", "final_holdout"]
    contiguous = all(boundaries[names_in_order[i]][1] == boundaries[names_in_order[i + 1]][0]
                      for i in range(len(names_in_order) - 1))
    check("split_boundaries_contiguous_no_gap_no_overlap", contiguous, f"{boundaries}")
    check("discovery_n_bars_matches_seq0009_seq0015_published_value",
          (boundaries["discovery"][1] - boundaries["discovery"][0]) == 2393,
          "stesso dataset/partition di SEQ-0009/SEQ-0015")

    state_cut = p["state_definition"]["tercile_cutpoints_fit_on_discovery_only"]
    check("state_tercile_cutpoints_ascending", state_cut["q1_low_med"] < state_cut["q2_med_high"])
    match_cut = ms["state_feature_definitions"]["volatility_state_pre_entry"][
        "tercile_cutpoints_fit_on_discovery_only"]
    check("matching_tercile_cutpoints_ascending", match_cut["q1_low_med"] < match_cut["q2_med_high"])

    check("no_rescue_clause_present", "no_rescue_clause" in p)
    check("no_outcome_accessed_flag", p["no_nexus_outcome_data_accessed"] is True)
    check("no_edge_discovery_flag", p["no_edge_discovery_performed"] is True)
    check("no_statistical_contract_flag", p["no_statistical_contract_built"] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== SEQ-0014 frozen spec consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
