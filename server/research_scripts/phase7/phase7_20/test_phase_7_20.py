#!/usr/bin/env python3
"""Phase 7.20 - suite di test per la shortlist strategie candidate a
Edge Validation."""
import os
import sys
import unittest

PHASE720_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE720_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE720_DIR)
import build_strategy_universe as universe_builder  # noqa: E402
import build_evaluation_matrix as matrix_builder  # noqa: E402
import build_shortlist as shortlist_builder  # noqa: E402
import build_edge_validation_protocol as protocol_builder  # noqa: E402
import build_recommended_first as recommended_builder  # noqa: E402
import build_evidence_reusability as reusability_builder  # noqa: E402
import build_edge_validation_gap_analysis as gap_builder  # noqa: E402
import build_inclusion_exclusion_summary as incl_excl_builder  # noqa: E402
import verify_phase_7_20 as verifier  # noqa: E402

ARTIFACTS = [
    ("strategy_universe_v1.json", universe_builder.build),
    ("evaluation_matrix_v1.json", matrix_builder.build),
    ("shortlist_v1.json", shortlist_builder.build),
    ("edge_validation_protocol_v1.json", protocol_builder.build),
    ("recommended_first_v1.json", recommended_builder.build),
    ("evidence_reusability_v1.json", reusability_builder.build),
    ("edge_validation_gap_analysis_v1.json", gap_builder.build),
    ("inclusion_exclusion_summary_v1.json", incl_excl_builder.build),
]


class TestDeterminism(unittest.TestCase):
    def test_all_artifacts_deterministic(self):
        for fname, build_fn in ARTIFACTS:
            saved = load_json(os.path.join(PHASE720_DIR, fname))
            self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(build_fn()), fname)


class TestUniverseComplete(unittest.TestCase):
    def setUp(self):
        self.payload = universe_builder.build()

    def test_83_strategies(self):
        self.assertEqual(self.payload["n_strategies_total"], 83)
        self.assertEqual(len(self.payload["universe"]), 83)

    def test_no_new_data_flag(self):
        self.assertTrue(self.payload["no_new_data_generated_in_this_phase"])

    def test_tsi_and_order_block_present_with_defect_audit(self):
        by_id = {u["canonical_strategy_id"]: u for u in self.payload["universe"]}
        for sid in ("TSI", "ORDER_BLOCK", "BREAKOUT_ACC"):
            self.assertIsNotNone(by_id[sid]["phase_7_10_static_audit"])


class TestEvaluationMatrix(unittest.TestCase):
    def setUp(self):
        self.payload = matrix_builder.build()

    def test_16_criteria_declared(self):
        self.assertEqual(len(self.payload["criteria"]), 16)

    def test_5_categories_declared(self):
        self.assertEqual(len(self.payload["classification_categories"]), 5)

    def test_pf_alone_never_used_flag(self):
        self.assertTrue(self.payload["pf_alone_never_used_to_classify"])

    def test_full_83_coverage(self):
        self.assertEqual(self.payload["n_strategies_total_covered"], 83)

    def test_required_names_in_tier_a(self):
        for sid in ("BREAKOUT_ACC", "ORDER_BLOCK", "TSI", "ADX_RSI", "SAR"):
            self.assertIn(sid, self.payload["tier_a_deep_dive"])

    def test_tier_a_entries_have_all_16_criteria(self):
        criteria_ids = {c["id"] for c in self.payload["criteria"]}
        for sid, entry in self.payload["tier_a_deep_dive"].items():
            missing = criteria_ids - set(entry.keys())
            self.assertEqual(missing, set(), f"{sid} manca criteri {missing}")

    def test_tsi_not_auto_promoted(self):
        self.assertNotEqual(self.payload["tier_a_deep_dive"]["TSI"]["category"],
                            "READY_FOR_EDGE_VALIDATION")

    def test_adx_rsi_and_sar_not_promoted_without_integrity_check(self):
        for sid in ("ADX_RSI", "SAR"):
            self.assertEqual(self.payload["tier_a_deep_dive"][sid]["category"], "DO_NOT_USE_YET")

    def test_liq_sweep_promising_not_ready(self):
        self.assertEqual(self.payload["tier_a_deep_dive"]["LIQ_SWEEP"]["category"],
                         "PROMISING_BUT_NEEDS_INTEGRITY_WORK")

    def test_category_counts_sum_to_83(self):
        self.assertEqual(sum(self.payload["category_counts"].values()), 83)

    def test_tier_c_bulk_has_explicit_rule(self):
        self.assertIn("rule", self.payload["tier_c_bulk"])
        self.assertGreater(self.payload["tier_c_bulk"]["n_strategies"], 0)


class TestShortlist(unittest.TestCase):
    def setUp(self):
        self.payload = shortlist_builder.build()

    def test_breakout_acc_and_order_block_shortlisted(self):
        self.assertIn("BREAKOUT_ACC", self.payload["strategies"])
        self.assertIn("ORDER_BLOCK", self.payload["strategies"])

    def test_tsi_not_shortlisted(self):
        self.assertNotIn("TSI", self.payload["strategies"])

    def test_every_entry_has_10_required_fields(self):
        required = {"perche_candidata", "evidenza_positiva_gia_esistente", "rischi_limiti",
                   "quali_dati_usare", "implementation_identity_canonica", "test_economico_corretto",
                   "quali_costi_includere", "quale_holdout_oos_usare",
                   "nuovo_run_mt5_o_artifact_bastano", "livello_visual_audit_possibile",
                   "minimum_viable_capital_da_verificare"}
        for sid, entry in self.payload["strategies"].items():
            self.assertTrue(required.issubset(entry.keys()), f"{sid} manca campi")

    def test_size_below_5_has_justification(self):
        if self.payload["shortlist_size"] < 3:
            self.assertIn("why_fewer_than_requested_minimum", self.payload)


class TestEdgeValidationProtocol(unittest.TestCase):
    def setUp(self):
        self.payload = protocol_builder.build()

    def test_not_executed_flag(self):
        self.assertTrue(self.payload["not_executed_in_this_phase"])

    def test_no_optimization_no_sweep_no_compounding_no_portfolio(self):
        text = " ".join(self.payload["explicit_exclusions_this_protocol_never_does"]).lower()
        for forbidden in ("optimization", "sweep", "compounding", "portfolio"):
            self.assertIn(forbidden, text)

    def test_stages_sequential_with_gates(self):
        stages = self.payload["stages"]
        for key in ("0_preregistration", "1_baseline_edge", "2_costs", "3_oos", "4_execution_realism"):
            self.assertIn(key, stages)
            self.assertIn("gate_to_pass", stages[key])


class TestRecommendedFirst(unittest.TestCase):
    def test_breakout_acc_recommended(self):
        payload = recommended_builder.build()
        self.assertEqual(payload["recommended_first"], "BREAKOUT_ACC")
        self.assertIn("not_a_promotion", payload)


class TestEvidenceReusability(unittest.TestCase):
    def test_order_block_and_tsi_old_evidence_not_reusable(self):
        payload = reusability_builder.build()
        strategies_not_reusable = {item["strategy"] for item in
                                   payload["not_reusable_as_evidence_of_current_canonical_implementation"]}
        self.assertIn("ORDER_BLOCK", strategies_not_reusable)
        self.assertIn("TSI", strategies_not_reusable)


class TestGapAnalysis(unittest.TestCase):
    def test_both_shortlisted_strategies_have_gaps_listed(self):
        payload = gap_builder.build()
        self.assertIn("BREAKOUT_ACC", payload)
        self.assertIn("ORDER_BLOCK", payload)
        self.assertGreater(len(payload["BREAKOUT_ACC"]), 0)
        self.assertGreater(len(payload["ORDER_BLOCK"]), 0)


class TestNoScopeViolations(unittest.TestCase):
    def test_no_mql5_product_platform_contracts_changes(self):
        import subprocess
        result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                                "contracts/"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        self.assertEqual(verifier.verify(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
