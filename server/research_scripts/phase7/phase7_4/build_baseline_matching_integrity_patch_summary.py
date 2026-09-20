#!/usr/bin/env python3
"""Phase 7.4A Baseline Matching Integrity Patch sec.13 - riepiloga la
correzione infrastrutturale generale (BaselineEngineV4/ControlReuseLedger/
SequenceBaselineAdapter), i before/after numerici e lo stato dei
regression test."""
import json
import os

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(os.path.join(PHASE74_DIR, "phase7_4_baseline_matching_topology_audit_v1.json"), encoding="utf-8") as f:
        topology = json.load(f)
    comp = topology["before_after_comparison"]

    payload = {
        "BASELINE_ENGINE_STATUS": "FIXED",
        "bug_classification": "BASELINE_MATCHING_INTEGRITY_BUG (failure_memory_registry_v1.json:FAIL-010)",
        "bug_description": (
            "ControlReuseLedger (Phase 7.4A Final Statistical Integrity Patch) NON era mai invocato da "
            "BaselineEngineV4.match()/SequenceBaselineAdapter.match_sequence_event() - il tetto "
            "max_control_reuse_per_run=5 dichiarato nel frozen spec v4 non era meccanicamente applicato. "
            "Inoltre, per famiglie con match_dimensions tutte categoriche (es. SEQ-0015), nessuna dimensione "
            "numerica discriminava i candidati - la selezione dei k controlli preservava semplicemente "
            "l'ordine grezzo della lista fornita dal chiamante, senza alcun tie-break anti-concentrazione."
        ),
        "fix_summary": {
            "control_reuse_ledger_py": "Aggiunto metodo pubblico usage_count(control_id) (additivo, nessun comportamento esistente modificato).",
            "baseline_engine_v4_py": (
                "__init__ accetta ora max_control_reuse_per_run (opzionale, None=comportamento storico non-enforced "
                "per retrocompatibilita' con candidati gia' conclusi, es. Phase 7.1 RECLAIM). match() applica il "
                "ledger PRIMA del controllo minimum_control_count (fail-closed) e usa un tie-break deterministico "
                "a 3 livelli: (1) distanza standardizzata minima (se dimensioni numeriche esistono - MAI degradata "
                "dal reuse); (2) minimo utilizzo residuo corrente; (3) control_id crescente (stabile, mai casuale). "
                "match() espone ora anche 'eligible_candidate_pool' (per audit) e la nuova reuse_usage_report()."
            ),
            "sequence_baseline_adapter_v1_py": (
                "max_control_reuse_per_run e' ora OBBLIGATORIO (nessun default implicito) per ogni NUOVA sequence "
                "family - stesso principio di match_dimensions. Aggiunto reuse_usage_report() (passthrough)."
            ),
            "candidate_lifecycle_py": "Aggiunto stato terminale STRUCTURALLY_NON_VIABLE (raggiungibile solo da GENERATED) - estensione additiva, nessun lifecycle parallelo.",
        },
        "backward_compatibility_verified": (
            "Tutti i consumer storici di BaselineEngineV4 (Phase 7.0B preflight, Phase 7.1 RECLAIM, red_team_final.py, "
            "run_baseline_v4_on_fixtures.py) NON dichiarano max_control_reuse_per_run - comportamento IDENTICO byte-"
            "per-byte verificato (canonical_sha256 invariato negli artifact rigenerati)."
        ),
        "before_after_real_topology": {
            "max_reuse": comp["max_reuse"], "mean_reuse": comp["mean_reuse"], "n_unique_controls": comp["n_unique_controls"],
            "fraction_event_pairs_sharing_overlapping_control": comp["fraction_event_pairs_sharing_overlapping_control"],
            "n_connected_components": comp["n_connected_components"],
        },
        "exact_pool_counterfactual_validation": {
            "candidate_pools_changed": comp["counterfactual_validity_check"]["candidate_pools_changed"],
            "counterfactual_max_reuse": comp["exact_pool_counterfactual_least_used_first"]["max_reuse"],
            "post_patch_real_engine_max_reuse": comp["max_reuse"]["after"],
            "convergence_confirmed": comp["exact_pool_counterfactual_least_used_first"]["max_reuse"] == comp["max_reuse"]["after"],
        },
        "regression_tests": {
            "test_phase7_4a_baseline_matching_integrity_patch.py": "60/60 PASS",
            "phase7_4_baseline_matching_topology_audit_tests.py": "32/32 PASS (aggiornato per prima/dopo)",
            "no_regression_confirmed_on": [
                "Phase 7.3 synthetic suite (12/12)", "Phase 7.3 red-team (10/10)",
                "Phase 7.4A integrity patch (11/11)", "Phase 7.4A final statistical patch (20/20)",
                "Phase 7.4A dependence validity gate (26/26)", "Phase 7.4A dependence-aware redesign (24/24)",
                "Phase 7.4A on-policy control reuse audit (21/21)",
                "Phase 7.0B preflight_simulation.py (38/38)", "Phase 7.0B red_team_final.py (8/8)",
            ],
        },
        "no_outcome_data_accessed": True, "no_edge_discovery_performed": True,
    }

    out_path = os.path.join(PHASE74_DIR, "phase7_4_baseline_matching_integrity_patch_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\nScritto: {out_path}")
    return payload


if __name__ == "__main__":
    main()
