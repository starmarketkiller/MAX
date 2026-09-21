#!/usr/bin/env python3
"""Phase 7.5B - SEQ-0009 frozen spec: regression/consistency checks.
Verifica la COERENZA INTERNA dello spec congelato (formule, hash,
confini) - NON esegue il gate strutturale (script separato) e NON
legge alcun outcome."""
import json
import os
import sys

PHASE75B_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE75B_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    spec_path = os.path.join(PHASE75B_DIR, "seq0009_frozen_structural_spec_v1.json")
    doc = load_json(spec_path)
    p = doc["payload"]

    check("canonical_hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))

    dp = p["detector_provenance"]
    operative_path = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_1", "build_events_p71.py")
    reference_path = os.path.join(ROOT, "server", "research_scripts", "phase5", "build_events.py")
    check("operative_detector_hash_matches_current_file", dp["operative_source_sha256"] == file_sha256(operative_path))
    check("reference_detector_hash_matches_current_file", dp["reference_source_sha256"] == file_sha256(reference_path))
    check("detector_frozen_true", p["detector_frozen"] is True)

    check("embargo_equals_horizon_minus_1",
          p["proposed_outcome_overlap_embargo_bars"] == p["proposed_natural_horizon"] - 1,
          f"embargo={p['proposed_outcome_overlap_embargo_bars']}, horizon={p['proposed_natural_horizon']}")

    check("episode_gap_rule_not_copied_from_seq0015",
          p["episode_gap_rule"] != 3 or "NON copiato" in p["episode_rule_rationale"],
          f"episode_gap_rule={p['episode_gap_rule']}")

    check("direction_policy_is_per_event", p["event_direction_policy"] == "PER_EVENT_DIRECTION")
    check("direction_mapping_high_is_sell", p["direction_derivation"]["mapping"]["HIGH"] == "SELL")
    check("direction_mapping_low_is_buy", p["direction_derivation"]["mapping"]["LOW"] == "BUY")

    ms = p["matching_spec"]
    for field in ("match_dimensions", "k", "minimum_control_count", "max_control_reuse_per_run",
                  "state_feature_definitions", "control_pool_construction_policy", "split_boundaries"):
        check(f"matching_spec_has_{field}", field in ms)

    boundaries = ms["split_boundaries"]
    names_in_order = ["discovery", "internal_validation", "locked_validation", "final_holdout"]
    contiguous = all(boundaries[names_in_order[i]][1] == boundaries[names_in_order[i + 1]][0]
                      for i in range(len(names_in_order) - 1))
    check("split_boundaries_contiguous_no_gap_no_overlap", contiguous, f"{boundaries}")
    check("discovery_n_bars_matches_seq0015_published_value",
          (boundaries["discovery"][1] - boundaries["discovery"][0]) == 2393,
          "stesso n_bars=2393 gia' pubblicato per development_discovery in Phase 7.4A - stesso dataset/partition")

    cutpoints = ms["state_feature_definitions"]["volatility_state_pre_event"]["tercile_cutpoints_fit_on_discovery_only"]
    check("tercile_cutpoints_ascending", cutpoints["q1_low_med"] < cutpoints["q2_med_high"])

    check("double_sweep_edge_case_documented",
          "double_sweep" in p["event_definition"]["ambiguous_double_sweep_same_bar_rule"].lower()
          or "ambiguo" in p["event_definition"]["ambiguous_double_sweep_same_bar_rule"].lower())
    check("isolated_from_reclaim_documented", "isolated_from_reclaim" in p["event_definition"])
    check("no_rescue_clause_present", "no_rescue_clause" in p)
    check("no_outcome_accessed_flag", p["no_nexus_outcome_data_accessed"] is True)
    check("no_edge_discovery_flag", p["no_edge_discovery_performed"] is True)
    check("no_statistical_contract_flag", p["no_statistical_contract_built"] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== SEQ-0009 frozen spec consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
