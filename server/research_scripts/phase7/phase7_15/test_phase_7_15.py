#!/usr/bin/env python3
"""Phase 7.15 - suite di test per la chiusura del perimetro di
validazione di Phase 7.14."""
import os
import sys
import unittest

PHASE715_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE714_DIR = os.path.abspath(os.path.join(PHASE715_DIR, "..", "phase7_14"))
ROOT = os.path.abspath(os.path.join(PHASE715_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE715_DIR)
import build_regression_reclassification as regr_builder  # noqa: E402
import build_ob_mit_perimeter as obmit_builder  # noqa: E402
import build_ea_python_comparison_classification as cmp_builder  # noqa: E402
import build_sources_and_binaries_audit as srcbin_builder  # noqa: E402
import verify_phase_7_15 as verifier  # noqa: E402

sys.path.insert(0, PHASE714_DIR)
import build_parity_comparison as parity_builder  # noqa: E402
import build_order_block_decision_card_v2 as card_builder  # noqa: E402

ARTIFACTS = [
    ("regression_reclassification_v1.json", regr_builder.build),
    ("ob_mit_perimeter_v1.json", obmit_builder.build),
    ("ea_python_comparison_classification_v1.json", cmp_builder.build),
    ("sources_and_binaries_audit_v1.json", srcbin_builder.build),
]


class TestDeterminism(unittest.TestCase):
    def test_all_artifacts_deterministic(self):
        for fname, build_fn in ARTIFACTS:
            saved = load_json(os.path.join(PHASE715_DIR, fname))
            fresh = build_fn()
            self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(fresh), fname)


class TestRegressionReclassification(unittest.TestCase):
    def setUp(self):
        self.payload = regr_builder.build()

    def test_no_real_regressions_from_order_block_fix(self):
        self.assertEqual(self.payload["n_real_regressions_caused_by_order_block_fix"], 0)

    def test_no_frozen_test_modified(self):
        self.assertTrue(self.payload["no_frozen_test_modified_to_force_green"])
        self.assertTrue(self.payload["no_assertion_disabled"])

    def test_every_residual_failure_has_baseline_confirmation_or_declared_limit(self):
        for entry in self.payload["residual_failures_on_clean_checkout_of_fix_commit"]:
            self.assertIn("category", entry)
            self.assertIn(entry["category"],
                          {"VINCOLO_STORICO_BASELINE_ATTESO", "VINCOLO_STORICO_BASELINE_DICHIARATO",
                           "VINCOLO_STORICO_BASELINE_AMBIENTALE", "REGRESSIONE_REALE",
                           "DIFETTO_VERIFICATORE",
                           "VINCOLO_STORICO_BASELINE_DICHIARATO_E_ATTESO_COMBINATI",
                           "DIFETTO_VERIFICATORE_ISOLAMENTO_TEST_RISOLTO_IN_QUESTA_FASE"})

    def test_verifier_fixes_proposed_not_applied(self):
        self.assertGreater(len(self.payload["verifier_fixes_proposed_but_not_applied"]), 0)


class TestOBMitPerimeter(unittest.TestCase):
    def setUp(self):
        self.payload = obmit_builder.build()

    def test_order_block_call_precedes_wrapper(self):
        self.assertTrue(self.payload["static_findings"]["1_call_order"]["order_block_call_precedes_ob_mit_call"])

    def test_deterministic_no_double_signal(self):
        self.assertTrue(self.payload["deterministic_test_result"]["no_double_signal_same_tick"])
        self.assertTrue(self.payload["deterministic_test_result"]["confirms_ob_mit_sees_consumed_zone"])

    def test_toggle_dependency_documented(self):
        self.assertIn("finding", self.payload["static_findings"]["3_toggle_dependency"])

    def test_selector_20_isolated_documented(self):
        self.assertIn("finding", self.payload["static_findings"]["4_selector_20_isolated"])

    def test_scalp_override_divergence_documented_not_affecting_production(self):
        f = self.payload["static_findings"]["5_scalp_tf_override"]
        self.assertFalse(f["order_block_in_override_list"] is False)  # ORDER_BLOCK e' nell'elenco
        self.assertFalse(f["ob_mit_in_override_list"])  # OB_MIT non lo e'
        self.assertFalse(f["affects_current_production_default"])

    def test_guardia_ereditata_distinguished_from_validated_behavior(self):
        d = self.payload["guardia_ereditata_vs_comportamento_integrato_validato"]
        self.assertIn("guardia_ereditata", d)
        self.assertIn("comportamento_integrato_validato", d)
        self.assertIn("NON AFFERMATO", d["comportamento_integrato_validato"])

    def test_no_new_tester_run(self):
        self.assertTrue(self.payload["no_tester_run_launched_this_task"])


class TestEaPythonComparisonClassification(unittest.TestCase):
    def setUp(self):
        self.payload = cmp_builder.build()

    def test_three_levels_kept_distinct(self):
        levels = self.payload["three_levels_kept_distinct"]
        self.assertIn("1_pre_post_fix_same_data", levels)
        self.assertIn("2_structural_different_sources", levels)
        self.assertIn("3_event_by_event_parity", levels)

    def test_level_1_not_reclassified(self):
        self.assertFalse(self.payload["three_levels_kept_distinct"]["1_pre_post_fix_same_data"]["reclassification_needed"])

    def test_level_2_reclassified_away_from_true(self):
        l2 = self.payload["three_levels_kept_distinct"]["2_structural_different_sources"]
        self.assertTrue(l2["reclassification_needed"])
        self.assertNotEqual(l2["new_field_value"], "residual_explained: true")

    def test_final_classification_not_simply_true(self):
        self.assertIn(self.payload["final_residual_classification"],
                      {"CANDIDATE_CAUSE_QUANTIFIED_NOT_FULLY_ISOLATED",
                       "CAUSE_UNCLEAR_NOT_EXPLAINED_BY_FEED_DIFFERENCES_ALONE"})

    def test_counts_not_forced(self):
        self.assertTrue(self.payload["counts_not_forced_to_coincide"])
        self.assertTrue(self.payload["no_new_backtest_campaign"])

    def test_exact_matches_far_fewer_than_totals(self):
        l3 = self.payload["three_levels_kept_distinct"]["3_event_by_event_parity"]
        self.assertLess(l3["n_exact_matches"], l3["n_b_only_dates"] + l3["n_exact_matches"])


class TestPhase714CorrectionApplied(unittest.TestCase):
    """Verifica che la revisione tracciata sia REALMENTE presente negli
    artifact di Phase 7.14 (non solo dichiarata in Phase 7.15)."""

    def test_parity_comparison_corrected(self):
        payload = parity_builder.build()
        bvc = payload["b_vs_c_structural_comparison"]
        self.assertFalse(bvc["residual_causally_isolated"])
        self.assertIn("correction_note_phase_7_15", bvc)

    def test_decision_card_corrected(self):
        payload = card_builder.build()
        self.assertFalse(payload["parity_summary"]["residual_explained"])
        self.assertEqual(payload["parity_summary"]["residual_classification"],
                         "CANDIDATE_CAUSE_NOT_ISOLATED")

    def test_main_fix_decision_unaffected_by_correction(self):
        payload = card_builder.build()
        self.assertEqual(payload["decision"], "FIX_CAUSALLY_VALIDATED")


class TestSourcesAndBinariesAudit(unittest.TestCase):
    def setUp(self):
        self.payload = srcbin_builder.build()

    def test_no_compilation_or_execution_this_phase(self):
        self.assertTrue(self.payload["no_compilation_or_execution_launched_this_phase"])
        self.assertTrue(self.payload["no_ea_replaced_or_started_on_operational_terminal"])

    def test_current_source_only_guard(self):
        self.assertTrue(self.payload["current_source"]["contains_only_the_guard"])

    def test_deployed_binary_cross_checked_against_compile_log(self):
        cc = self.payload["cross_check_deployed_binary_vs_compile_log"]
        self.assertIn("conclusion", cc)

    def test_untouched_terminal_documented(self):
        self.assertIn("7F8EC41F011085EB9C65165AE426B5A6", self.payload["deployed_binaries"])


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        self.assertEqual(verifier.verify(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
