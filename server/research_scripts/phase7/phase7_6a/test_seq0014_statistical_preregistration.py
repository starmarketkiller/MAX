#!/usr/bin/env python3
"""Phase 7.6A - SEQ-0014 statistical preregistration: consistency
checks. Verifica la COERENZA INTERNA del contratto congelato e che
questo script/i suoi artifact NON abbiano MAI letto outcome. NON
esegue discovery."""
import json
import os
import sys

PHASE76A_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE76A_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    doc_path = os.path.join(PHASE76A_DIR, "seq0014_statistical_preregistration_v1.json")
    doc = load_json(doc_path)
    p = doc["payload"]

    check("canonical_hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))

    # ---- lo stato di blocco deve essere esplicito e coerente ----
    check("preregistration_status_is_blocked", p["preregistration_status"] == "BLOCKED_ON_CONTROL_POOL_ESTIMAND_AMBIGUITY")
    check("discovery_not_authorized", p["discovery_authorized"] is False)
    check("baseline_estimand_status_blocked", p["baseline_estimand_contract"]["status"] == "BLOCKED")
    check("blocker_summary_present_and_nonempty", len(p.get("blocker_summary", "")) > 0)

    # ---- audit di contaminazione: deve essere un numero reale, non inventato ----
    contam = p["baseline_estimand_contract"]["contamination_audit"]
    check("contamination_fraction_is_plausible",
          0.0 < contam["fraction_of_current_eligible_control_pool_also_in_state"] < 1.0,
          f"{contam['fraction_of_current_eligible_control_pool_also_in_state']}")
    check("contamination_roughly_matches_base_rate",
          abs(contam["fraction_of_current_eligible_control_pool_also_in_state"] -
              contam["overall_base_rate_of_in_state_across_discovery"]) < 0.05,
          "conferma che la policy attuale non filtra per stato (estimand A, non B)")
    check("n_events_matches_structural_gate_result", contam["n_events"] == p["structural_gate_summary"]["EVENT_VIEW"])

    # ---- domanda scientifica e outcome contract devono essere congelati (indipendenti da A/B) ----
    check("scientific_question_frozen", p["scientific_question"]["frozen"] is True)
    check("non_directional_confirmed", "non_directional_confirmation" in p["scientific_question"])
    check("no_directional_p_atr_outcome_reused",
          "P_PLUS" not in json.dumps(p["outcome_contract"]) and "MFE" not in json.dumps(p["outcome_contract"])
          and "MAE" not in json.dumps(p["outcome_contract"]),
          "nessun outcome direzionale (P(+X ATR before -1ATR), MFE/MAE) riusato per una family NON_DIRECTIONAL")
    check("primary_outcome_is_realized_volatility",
          p["outcome_contract"]["primary_outcome"]["id"] == "REALIZED_VOLATILITY_AFTER_SETUP")
    check("inferential_family_size_is_2", p["outcome_contract"]["inferential_family_size_verified_programmatically"] == 2)
    check("multiplicity_n_comparisons_is_2", p["multiplicity_contract"]["n_comparisons"] == 2)

    # ---- ATR normalization fissa (mai ricalcolata sulla finestra futura) ----
    common = p["outcome_contract"]["common_definitions"]
    check("normalization_uses_atr_t_not_future", "ATR_t" in common["normalization_atr"]
          and "future" not in common["normalization_atr"].lower())
    check("horizon_reused_from_frozen_structural_spec", common["horizon_bars"] == 20)

    # ---- inference method: candidato dichiarato, non validato, non inventato ex-novo ----
    inf = p["inference_contract"]
    check("candidate_method_is_reused_general_infra",
          "block_sign_flip_permutation_matched_pair" == inf["candidate_primary_method"])
    check("validation_status_honest", inf["validation_status"] == "PRIMARY_INFERENCE_METHOD_NOT_YET_VALIDATED")
    check("no_uncalibrated_method_flag_true", inf["no_uncalibrated_method_applied"] is True)
    check("dependence_gate_thresholds_match_phase74a_frozen_values",
          inf["dependence_gate_reused"]["frozen_thresholds_reused_unchanged"]["acf_lag1_sensitive"] == 0.2
          and inf["dependence_gate_reused"]["frozen_thresholds_reused_unchanged"]["acf_lag1_invalid"] == 0.45,
          "stesse soglie congelate in Phase 7.4A, non ri-tarate qui")

    # ---- effect size floor riusa la stessa filosofia/numero di minimum_evidence_gates.json ----
    check("effect_size_floor_is_010", p["effect_size_contract"]["minimum_material_effect_size"]["value"] == 0.10)

    # ---- accesso ai dati: solo discovery autorizzata per il futuro, il resto resta chiuso ----
    dap = p["data_access_policy"]
    check("only_discovery_authorized_for_future", dap["authorized_for_future_discovery_run"] == ["development_discovery"])
    check("internal_validation_locked", "development_internal_validation" in dap["locked_until_separately_authorized"])
    check("locked_validation_locked", "locked_validation" in dap["locked_until_separately_authorized"])
    check("final_holdout_locked", "final_holdout" in dap["locked_until_separately_authorized"])

    # ---- nessun outcome letto, nessuna discovery eseguita, nessun'altra family riesaminata ----
    check("no_outcome_accessed_flag", p["no_nexus_outcome_data_accessed"] is True)
    check("no_edge_discovery_flag", p["no_edge_discovery_performed"] is True)
    check("no_validation_partitions_opened_flag", p["no_internal_validation_locked_or_final_holdout_opened"] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- verifica statica: questo script e il builder non LEGGONO MAI alcun file di outcome
    # (una menzione narrativa di "outcomes_v1.csv" per dichiarare che NON viene aperto e'
    # legittima - qui si verifica che non compaia in una chiamata read_csv/open reale) ----
    for fname in ("build_seq0014_statistical_preregistration.py",):
        with open(os.path.join(PHASE76A_DIR, fname), encoding="utf-8") as f:
            src = f.read()
        check(f"{fname}_never_opens_outcomes_csv",
              "read_csv(\"outcomes" not in src and "read_csv('outcomes" not in src
              and "OUTCOMES_PATH" not in src)
        check(f"{fname}_never_imports_outcome_computation_module",
              "load_outcomes" not in src and "compute_outcome" not in src)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== SEQ-0014 statistical preregistration consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
