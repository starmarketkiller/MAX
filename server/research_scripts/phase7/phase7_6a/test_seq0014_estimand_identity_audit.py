#!/usr/bin/env python3
"""Phase 7.6A - MECH-23 Estimand Identity Audit: consistency checks.
Verifica la coerenza interna dell'audit e che NESSUN artifact congelato
precedente (frozen structural spec, preregistrazione) sia stato
modificato. NON esegue discovery, NON legge outcome."""
import os
import sys

PHASE76A_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE76A_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    doc_path = os.path.join(PHASE76A_DIR, "seq0014_estimand_identity_audit_v1.json")
    doc = load_json(doc_path)
    p = doc["payload"]

    check("canonical_hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))

    # ---- la sorgente canonica deve essere citata verbatim, non riassunta liberamente ----
    src = p["canonical_source"]
    check("falsification_definition_mentions_choppy_and_trending",
          "choppy" in src["falsification_definition_verbatim"] and
          "trending" in src["falsification_definition_verbatim"])
    check("falsification_definition_mentions_setup",
          "setup" in src["falsification_definition_verbatim"].lower())

    # ---- classificazione e non-equivalenza forzata ----
    check("classification_is_related_but_distinct", p["estimand_comparison"]["classification"] == "RELATED_BUT_DISTINCT")
    check("not_forced_equivalence_check_present", "not_forced_equivalence_check" in p["estimand_comparison"])

    cur = p["estimand_comparison"]["current_state_entry_experiment"]
    orig = p["estimand_comparison"]["original_mech23_claim"]
    check("current_experiment_unit_is_a_bar", "barra" in cur["unit_of_analysis"].lower())
    check("original_claim_unit_is_a_directional_setup", "setup" in orig["unit_of_analysis"].lower())
    check("units_of_analysis_are_textually_different", cur["unit_of_analysis"] != orig["unit_of_analysis"])
    check("outcomes_are_textually_different", cur["outcome"] != orig["outcome"])

    # ---- SEQ-0014A: il lavoro strutturale gia' fatto resta valido, scoping esplicito ----
    a = p["seq0014a_definition"]
    check("seq0014a_status_structurally_feasible", a["status"] == "STRUCTURALLY_FEASIBLE")
    check("seq0014a_scope_note_present_and_warns_against_reinterpretation",
          "SEQ-0014B" in a["structural_result_scope_note"] and "NON" in a["structural_result_scope_note"])
    check("seq0014a_references_correct_frozen_family_id",
          a["sequence_family_id_reference"] == "SEQFAM-SEQ0014-LOWINFO-STATE-STRUCTURAL-V1")

    # ---- SEQ-0014B: non operazionalizzato, nessuna risposta inventata ----
    b = p["seq0014b_definition"]
    check("seq0014b_status_needs_specification", b["status"] == "NEEDS_DIRECTIONAL_SETUP_POPULATION_SPECIFICATION")
    check("seq0014b_no_family_id_assigned_yet", b["sequence_family_id_reference"] is None)
    missing = p["seq0014b_missing_specification"]["open_questions"]
    check("seq0014b_has_multiple_open_questions", len(missing) >= 5, f"n={len(missing)}")
    check("seq0014b_open_questions_not_answered",
          all(q.get("not_specified_in_registry") is True for q in missing))

    # ---- outcome naming audit: nessuna rinominazione globale, solo chiarimento ----
    ona = p["outcome_naming_audit"]
    check("outcome_naming_flags_forward_range", "FORWARD_RANGE_ATR" in ona["metric_classification"])
    check("outcome_naming_does_not_rename_system_id",
          "REALIZED_VOLATILITY_AFTER_SETUP" in ona["action_taken"] and "INVARIATO" in ona["action_taken"])

    # ---- stato aggiornato coerente ----
    us = p["updated_status"]
    check("seq0014a_updated_status_matches", us["SEQ0014A_STATUS"] in a["preregistration_status"])
    check("seq0014b_updated_status_matches", us["MECH23_FILTER_CLAIM_STATUS"] == b["status"])
    check("discovery_not_authorized_for_either",
          us["discovery_authorized_for_seq0014a"] is False and us["discovery_authorized_for_seq0014b"] is False)

    # ---- nessun artifact congelato precedente e' stato toccato ----
    frozen_spec_path = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_5c",
                                     "seq0014_frozen_structural_spec_v1.json")
    prereg_path = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_6a",
                                "seq0014_statistical_preregistration_v1.json")
    check("frozen_structural_spec_file_exists_and_untouched_claim_matches_path",
          os.path.exists(frozen_spec_path) and p["frozen_structural_spec_untouched"].endswith(
              "seq0014_frozen_structural_spec_v1.json - nessuna modifica."))
    check("preregistration_file_exists_and_untouched_claim_matches_path",
          os.path.exists(prereg_path) and p["frozen_preregistration_untouched"].endswith(
              "seq0014_statistical_preregistration_v1.json - nessuna modifica."))

    check("no_control_pool_modified_flag", p["no_control_pool_modified"] is True)
    check("no_new_structural_spec_created_flag", p["no_new_structural_spec_created"] is True)
    check("no_new_detector_created_flag", p["no_new_detector_created"] is True)
    check("no_outcome_accessed_flag", p["no_nexus_outcome_data_accessed"] is True)
    check("no_edge_discovery_flag", p["no_edge_discovery_performed"] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- verifica statica: il builder non legge mai outcome ----
    builder_path = os.path.join(PHASE76A_DIR, "build_seq0014_estimand_identity_audit.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_opens_outcomes_csv", "OUTCOMES_PATH" not in builder_src and "outcomes_v1" not in builder_src)
    check("builder_never_imports_outcome_computation", "load_outcomes" not in builder_src and "compute_outcome" not in builder_src)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== SEQ-0014 estimand identity audit consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
