#!/usr/bin/env python3
"""Phase 7.21 - suite di test per BREAKOUT_ACC EDGE_VALIDATION_V1."""
import os
import sys
import unittest

PHASE721_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE721_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE721_DIR)
import build_data_exposure_map as exposure_builder  # noqa: E402
import build_baseline_economics as baseline_builder  # noqa: E402
import build_cost_stress as cost_builder  # noqa: E402
import build_execution_realism as execn_builder  # noqa: E402
import build_visual_audit_sample as visual_builder  # noqa: E402
import build_temporal_robustness as temporal_builder  # noqa: E402
import build_statistical_uncertainty as stats_builder  # noqa: E402
import build_oos_forward_analysis as oos_builder  # noqa: E402
import build_minimum_viable_capital as mvc_builder  # noqa: E402
import build_breakoutacc_decision_card as decision_builder  # noqa: E402
import build_frozen_forward_config as frozen_builder  # noqa: E402
import verify_phase_7_21 as verifier  # noqa: E402
from nxs_breakoutacc_dataset_loader import load_opened_events, net_pnl, risk_r  # noqa: E402

ARTIFACTS = [
    ("data_exposure_map_v1.json", exposure_builder.build),
    ("baseline_economics_v1.json", baseline_builder.build),
    ("cost_stress_v1.json", cost_builder.build),
    ("execution_realism_v1.json", execn_builder.build),
    ("visual_audit_sample_v1.json", visual_builder.build),
    ("temporal_robustness_v1.json", temporal_builder.build),
    ("statistical_uncertainty_v1.json", stats_builder.build),
    ("oos_forward_analysis_v1.json", oos_builder.build),
    ("minimum_viable_capital_v1.json", mvc_builder.build),
    ("breakoutacc_decision_card_v1.json", decision_builder.build),
    ("frozen_forward_config_v1.json", frozen_builder.build),
]


class TestDeterminism(unittest.TestCase):
    def test_all_artifacts_deterministic(self):
        for fname, build_fn in ARTIFACTS:
            saved = load_json(os.path.join(PHASE721_DIR, fname))
            self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(build_fn()), fname)


class TestDataExposureMap(unittest.TestCase):
    def setUp(self):
        self.payload = exposure_builder.build()

    def test_h2_declared_post_hoc(self):
        h2 = self.payload["hypothesis_preregistration"]["hypothesis_secondary"]
        self.assertIn("POST_HOC", h2["status"])

    def test_no_strategy_modification_flag(self):
        self.assertTrue(self.payload["hypothesis_preregistration"]["no_strategy_modification_to_favor_buy"])

    def test_no_true_historical_holdout_declared(self):
        conclusion = self.payload["data_exposure_map"]["conclusion"]
        self.assertIn("NESSUN vero holdout", conclusion)

    def test_forward_window_marked_genuinely_untouched(self):
        periods = self.payload["data_exposure_map"]["periods"]
        forward = next(p for p in periods if "2026.08.15" in p["period"])
        self.assertTrue(forward["genuinely_untouched"])


class TestBaselineEconomics(unittest.TestCase):
    def setUp(self):
        self.payload = baseline_builder.build()

    def test_47_opened_trades(self):
        self.assertEqual(self.payload["ALL"]["n_trades"], 47)
        self.assertEqual(self.payload["denominators_explicit"]["ALL"], 47)

    def test_buy_sell_denominators_sum_to_all(self):
        self.assertEqual(self.payload["BUY"]["n_trades"] + self.payload["SELL"]["n_trades"],
                         self.payload["ALL"]["n_trades"])

    def test_buy_only_not_presented_as_validated(self):
        self.assertTrue(self.payload["buy_only_not_presented_as_validated_strategy"])

    def test_no_tuning(self):
        self.assertTrue(self.payload["no_tuning_applied"])
        self.assertTrue(self.payload["no_optimization_applied"])

    def test_sell_win_rate_zero(self):
        # dato osservato, non un'assunzione - documentato esplicitamente nel vault report.
        self.assertEqual(self.payload["SELL"]["win_rate"], 0.0)


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

    def test_not_selected_to_preserve_edge_flag(self):
        self.assertTrue(self.payload["scenario_not_selected_to_preserve_edge"])


class TestExecutionRealism(unittest.TestCase):
    def setUp(self):
        self.payload = execn_builder.build()

    def test_blocked_and_rejected_not_dropped(self):
        self.assertIn("blocked_and_rejected_not_dropped", self.payload)
        bl = self.payload["blocked_and_rejected_not_dropped"]["blocked_events_direction_adjusted_signal_quality"]
        self.assertEqual(bl["n"], 11)

    def test_three_edge_levels_present(self):
        for k in ("signal_edge", "executable_edge", "realized_edge"):
            self.assertIn(k, self.payload)

    def test_realized_edge_uses_real_n(self):
        self.assertEqual(self.payload["realized_edge"]["n"], 47)


class TestVisualAuditSample(unittest.TestCase):
    def setUp(self):
        self.payload = visual_builder.build()

    def test_8_events_sampled(self):
        self.assertEqual(self.payload["sample_size"], 8)

    def test_all_strata_present(self):
        for k in ("winner", "loser", "random", "blocked_near_miss", "broker_reject_near_miss"):
            self.assertIn(k, self.payload["reviews"])

    def test_stage_a_never_contains_outcome_fields(self):
        forbidden = {"realized_pnl", "realized_swap", "realized_commission", "exit_fill_price",
                    "exit_fill_time", "measurement_A_post_signal_path", "measurement_B_post_fill_path"}
        for stratum in self.payload["reviews"].values():
            for r in stratum:
                shown = set(r["stage_a_blind_review"]["data_shown"])
                self.assertEqual(shown & forbidden, set())

    def test_forbidden_question_not_asked(self):
        for stratum in self.payload["reviews"].values():
            for r in stratum:
                self.assertEqual(r["stage_a_blind_review"]["forbidden_question_not_asked"], "Vincera'?")

    def test_blinding_limitation_declared(self):
        self.assertIn("blinding_limitation_declared", self.payload)

    def test_no_operational_rule_derived(self):
        self.assertTrue(self.payload["no_operational_rule_derived_from_visual_observations"])


class TestTemporalRobustness(unittest.TestCase):
    def setUp(self):
        self.payload = temporal_builder.build()

    def test_concentration_computed(self):
        self.assertIn("top_5", self.payload["concentration_of_profit"])

    def test_edge_without_top_trades_computed(self):
        self.assertIn("without_top_5", self.payload["edge_survives_without_top_trades"])

    def test_extreme_concentration_finding_present(self):
        # scoperta chiave di questa fase: rimuovendo i primi 5 trade l'edge
        # diventa negativo - deve restare visibile, non nascosta.
        self.assertFalse(self.payload["edge_survives_without_top_trades"]["without_top_5"]["still_positive"])


class TestStatisticalUncertainty(unittest.TestCase):
    def setUp(self):
        self.payload = stats_builder.build()

    def test_bootstrap_ci_present_for_all_groups(self):
        for g in ("ALL", "BUY", "SELL"):
            self.assertIsNotNone(self.payload["results"][g]["net_expectancy_bootstrap_ci"])

    def test_iid_not_assumed_blindly(self):
        self.assertTrue(self.payload["iid_not_assumed_blindly"])

    def test_all_group_ci_includes_zero(self):
        # scoperta chiave: l'expectancy AGGREGATA non e' statisticamente
        # distinguibile da zero con questo campione - deve restare visibile.
        ci = self.payload["results"]["ALL"]["net_expectancy_bootstrap_ci"]
        self.assertFalse(ci["excludes_zero"])


class TestOOSForwardAnalysis(unittest.TestCase):
    def setUp(self):
        self.payload = oos_builder.build()

    def test_window_declared_untouched(self):
        self.assertTrue(self.payload["window_genuinely_untouched"])

    def test_single_validation_run_only(self):
        self.assertTrue(self.payload["single_validation_run_only"])

    def test_insufficient_sample_not_failed(self):
        self.assertEqual(self.payload["decision"], "INSUFFICIENT_OOS_SAMPLE")
        self.assertNotEqual(self.payload["decision"], "FAILED")


class TestMinimumViableCapital(unittest.TestCase):
    def setUp(self):
        self.payload = mvc_builder.build()

    def test_5_capital_levels(self):
        levels = {row["capital_eur"] for row in self.payload["capital_table"]}
        self.assertEqual(levels, {300, 500, 1000, 2500, 10000})

    def test_risk_pct_decreases_with_capital(self):
        table = sorted(self.payload["capital_table"], key=lambda r: r["capital_eur"])
        risks = [row["risk_pct_of_capital_avg_sl"] for row in table]
        self.assertEqual(risks, sorted(risks, reverse=True))

    def test_no_sizing_proposed(self):
        self.assertTrue(self.payload["no_optimization_no_sizing_proposed"])


class TestDecisionCard(unittest.TestCase):
    def setUp(self):
        self.payload = decision_builder.build()

    def test_decision_allowed(self):
        allowed = {"EDGE_VALIDATED_PRELIMINARY", "EDGE_CANDIDATE_REQUIRES_OOS",
                  "EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION", "EDGE_NOT_SUPPORTED",
                  "INSUFFICIENT_EVIDENCE"}
        self.assertIn(self.payload["decision"], allowed)

    def test_not_live_ready(self):
        self.assertFalse(self.payload["decision_means_live_ready"])

    def test_5_checks_present(self):
        for i in range(1, 6):
            self.assertTrue(any(k.startswith(f"{i}_") for k in self.payload["checks"]))

    def test_no_optimization_performed(self):
        self.assertTrue(self.payload["no_optimization_performed"])


class TestFrozenForwardConfig(unittest.TestCase):
    def setUp(self):
        self.payload = frozen_builder.build()

    def test_not_executed_only_frozen(self):
        self.assertTrue(self.payload["not_executed_only_frozen"])
        self.assertTrue(self.payload["no_live_deploy"])

    def test_both_directions_kept(self):
        self.assertIn("ENTRAMBE", self.payload["config_frozen"]["direction_scope"])


class TestNetPnlAnchor(unittest.TestCase):
    def test_first_event_net_pnl_matches_known_sl_exit(self):
        events = load_opened_events()
        first = next(e for e in events if e["event_id"] == "evt_1209b7abca9456d1")
        self.assertAlmostEqual(abs(first["realized_pnl"]), risk_r(first), delta=0.01)


class TestNoScopeViolations(unittest.TestCase):
    def test_no_mql5_product_platform_changes(self):
        import subprocess
        result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                                "contracts/"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        self.assertEqual(verifier.verify(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
