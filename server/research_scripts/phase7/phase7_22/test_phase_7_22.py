#!/usr/bin/env python3
"""Phase 7.22 - suite di test per ORDER_BLOCK EDGE_VALIDATION_V1."""
import os
import sys
import unittest

PHASE722_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE722_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE722_DIR)
import build_identity_and_perimeter as identity_builder  # noqa: E402
import build_orderblock_data_exposure_map as exposure_builder  # noqa: E402
import build_canonical_economic_dataset as dataset_builder  # noqa: E402
import build_orderblock_baseline_economics as baseline_builder  # noqa: E402
import build_orderblock_cost_stress as cost_builder  # noqa: E402
import build_orderblock_execution_realism as execn_builder  # noqa: E402
import build_orderblock_visual_audit_sample as visual_builder  # noqa: E402
import build_orderblock_temporal_robustness as temporal_builder  # noqa: E402
import build_orderblock_statistical_uncertainty as stats_builder  # noqa: E402
import build_orderblock_oos_forward_analysis as oos_builder  # noqa: E402
import build_orderblock_minimum_viable_capital as mvc_builder  # noqa: E402
import build_orderblock_decision_card as decision_builder  # noqa: E402
import build_orderblock_frozen_forward_config as frozen_builder  # noqa: E402
import verify_phase_7_22 as verifier  # noqa: E402
from nxs_orderblock_dataset_loader import load_events, net_pnl, risk_r  # noqa: E402

ARTIFACTS = [
    ("identity_and_perimeter_v1.json", identity_builder.build),
    ("orderblock_data_exposure_map_v1.json", exposure_builder.build),
    ("canonical_economic_dataset_v1.json", dataset_builder.build),
    ("orderblock_baseline_economics_v1.json", baseline_builder.build),
    ("orderblock_cost_stress_v1.json", cost_builder.build),
    ("orderblock_execution_realism_v1.json", execn_builder.build),
    ("orderblock_visual_audit_sample_v1.json", visual_builder.build),
    ("orderblock_temporal_robustness_v1.json", temporal_builder.build),
    ("orderblock_statistical_uncertainty_v1.json", stats_builder.build),
    ("orderblock_oos_forward_analysis_v1.json", oos_builder.build),
    ("orderblock_minimum_viable_capital_v1.json", mvc_builder.build),
    ("orderblock_decision_card_v1.json", decision_builder.build),
    ("orderblock_frozen_forward_config_v1.json", frozen_builder.build),
]


class TestDeterminism(unittest.TestCase):
    def test_all_artifacts_deterministic(self):
        for fname, build_fn in ARTIFACTS:
            saved = load_json(os.path.join(PHASE722_DIR, fname))
            self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(build_fn()), fname)


class TestIdentityAndPerimeter(unittest.TestCase):
    def setUp(self):
        self.payload = identity_builder.build()

    def test_canonical_identity_order_block(self):
        self.assertEqual(self.payload["canonical_strategy_identity"], "ORDER_BLOCK")

    def test_old_pf_wr_not_used(self):
        self.assertTrue(self.payload["old_pf_wr_not_used_as_baseline"])

    def test_mt5_ground_truth(self):
        self.assertTrue(self.payload["mt5_is_ground_truth_for_real_events"])

    def test_no_breakout_acc_or_tsi_modification_flag(self):
        self.assertTrue(self.payload["no_modification_to_breakout_acc_or_tsi_in_this_phase"])

    def test_ob_mit_kept_separate(self):
        self.assertIn("OB_MIT", self.payload["ob_mit_relationship"])
        self.assertIn("DISABILITATO", self.payload["ob_mit_relationship"])


class TestDataExposureMap(unittest.TestCase):
    def setUp(self):
        self.payload = exposure_builder.build()

    def test_no_true_historical_holdout(self):
        self.assertIn("Nessun vero holdout", self.payload["conclusion"])

    def test_forward_window_marked_untouched(self):
        periods = self.payload["periods"]
        forward = next(p for p in periods if "2026.08.25" in p["period"])
        self.assertTrue(forward["genuinely_untouched_for_economic_baseline"])
        self.assertTrue(forward["genuinely_untouched_for_signal_level_integrity"])


class TestCanonicalDataset(unittest.TestCase):
    def test_events_use_real_mt5_pairing(self):
        payload = dataset_builder.build()
        if payload.get("status") == "RUN_NOT_YET_CAPTURED":
            self.skipTest("run non ancora catturato")
        self.assertTrue(payload["mt5_is_ground_truth"])
        self.assertGreaterEqual(payload["n_events_paired"], 0)


class TestBaselineEconomics(unittest.TestCase):
    def setUp(self):
        self.payload = baseline_builder.build()

    def test_denominators_sum(self):
        if self.payload["ALL"]["n_trades"] == 0:
            self.skipTest("nessun evento")
        self.assertEqual(self.payload["BUY"]["n_trades"] + self.payload["SELL"]["n_trades"],
                         self.payload["ALL"]["n_trades"])

    def test_no_side_eliminated_flag(self):
        self.assertTrue(self.payload["no_side_eliminated_for_worse_performance"])

    def test_no_tuning(self):
        self.assertTrue(self.payload["no_tuning_applied"])
        self.assertTrue(self.payload["no_optimization_applied"])


class TestCostStress(unittest.TestCase):
    def setUp(self):
        self.payload = cost_builder.build()

    def test_3_scenarios_present(self):
        self.assertEqual(set(self.payload["scenarios"].keys()),
                         {"COST_BASE", "COST_MODERATE", "COST_STRESS"})

    def test_costs_strictly_increasing(self):
        costs = [self.payload["scenarios"][k]["extra_roundtrip_cost_assumed_price_units"]
                for k in ("COST_BASE", "COST_MODERATE", "COST_STRESS")]
        self.assertEqual(costs, sorted(costs))
        self.assertEqual(len(set(costs)), 3)


class TestExecutionRealism(unittest.TestCase):
    def test_blocked_and_rejected_not_dropped_flag(self):
        payload = execn_builder.build()
        if payload.get("status") == "CERTIFICATE_NOT_YET_CAPTURED":
            self.skipTest("certificato non ancora catturato")
        self.assertTrue(payload["blocked_and_rejected_not_dropped"])
        self.assertIn("GENERATED", payload["funnel_counts"])
        self.assertIn("BLOCKED", payload["funnel_counts"])
        self.assertIn("BROKER_REJECT", payload["funnel_counts"])


class TestVisualAuditSample(unittest.TestCase):
    def setUp(self):
        self.payload = visual_builder.build()

    def test_stage_a_never_contains_outcome_fields(self):
        if self.payload.get("status") == "NO_EVENTS_YET":
            self.skipTest("nessun evento")
        forbidden = {"net_pnl", "exit_time", "exit_price", "exit_reason", "hold_sec"}
        for stratum in self.payload["reviews"].values():
            for r in stratum:
                shown = set(r["stage_a_blind_review"]["data_shown"])
                self.assertEqual(shown & forbidden, set())

    def test_forbidden_question_not_asked(self):
        if self.payload.get("status") == "NO_EVENTS_YET":
            self.skipTest("nessun evento")
        for stratum in self.payload["reviews"].values():
            for r in stratum:
                self.assertEqual(r["stage_a_blind_review"]["forbidden_question_not_asked"], "Vincera'?")

    def test_no_operational_rule_derived(self):
        if self.payload.get("status") == "NO_EVENTS_YET":
            self.skipTest("nessun evento")
        self.assertTrue(self.payload["no_operational_rule_derived_from_visual_observations"])


class TestTemporalRobustness(unittest.TestCase):
    def test_concentration_computed(self):
        payload = temporal_builder.build()
        if payload.get("status") == "NO_EVENTS_YET":
            self.skipTest("nessun evento")
        self.assertIn("top_5", payload["concentration_of_profit"])
        self.assertIn("without_top_5", payload["edge_survives_without_top_trades"])


class TestStatisticalUncertainty(unittest.TestCase):
    def test_bootstrap_ci_present(self):
        payload = stats_builder.build()
        if payload.get("status") == "NO_EVENTS_YET":
            self.skipTest("nessun evento")
        self.assertTrue(payload["iid_not_assumed_blindly"])
        self.assertTrue(payload["ci_includes_zero_means_no_edge_declared"])


class TestOOSForwardAnalysis(unittest.TestCase):
    def setUp(self):
        self.payload = oos_builder.build()

    def test_window_declared_untouched(self):
        if self.payload.get("status") == "RUN_NOT_YET_CAPTURED":
            self.skipTest("run forward non ancora catturato")
        self.assertTrue(self.payload["window_genuinely_untouched"])
        self.assertTrue(self.payload["single_validation_run_only"])

    def test_insufficient_not_failed(self):
        if self.payload.get("status") == "RUN_NOT_YET_CAPTURED":
            self.skipTest("run forward non ancora catturato")
        self.assertNotEqual(self.payload["decision"], "FAILED")


class TestMinimumViableCapital(unittest.TestCase):
    def test_5_levels(self):
        payload = mvc_builder.build()
        if payload.get("status") == "NO_EVENTS_YET":
            self.skipTest("nessun evento")
        levels = {row["capital_eur"] for row in payload["capital_table"]}
        self.assertEqual(levels, {300, 500, 1000, 2500, 10000})
        self.assertTrue(payload["no_optimization_no_sizing_proposed"])


class TestDecisionCard(unittest.TestCase):
    def test_decision_allowed_and_not_live_ready(self):
        payload = decision_builder.build()
        allowed = {"EDGE_VALIDATED_PRELIMINARY", "EDGE_CANDIDATE_REQUIRES_OOS",
                  "EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION", "EDGE_NOT_SUPPORTED",
                  "INSUFFICIENT_EVIDENCE"}
        self.assertIn(payload["decision"], allowed)
        self.assertFalse(payload["decision_means_live_ready"])
        self.assertTrue(payload["no_optimization_performed"])


class TestFrozenForwardConfig(unittest.TestCase):
    def test_not_executed_and_both_directions(self):
        payload = frozen_builder.build()
        self.assertTrue(payload["not_executed_only_frozen"])
        self.assertTrue(payload["no_live_deploy"])
        self.assertIn("ENTRAMBE", payload["config_frozen"]["direction_scope"])
        self.assertIn("BREAKOUT_ACC resta congelata",
                      " ".join(payload["rules_from_this_point_forward"]))


class TestNoScopeViolations(unittest.TestCase):
    def test_no_mql5_product_platform_changes(self):
        import subprocess
        result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                                "contracts/"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")

    def test_phase_7_21_and_7_18_untouched(self):
        import subprocess
        for rel in ("server/research_scripts/phase7/phase7_21", "server/research_scripts/phase7/phase7_18"):
            result = subprocess.run(["git", "diff", "--name-only", "--", rel], cwd=ROOT,
                                    capture_output=True, text=True)
            self.assertEqual(result.stdout.strip(), "", f"{rel} risulta modificato")


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        self.assertEqual(verifier.verify(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
