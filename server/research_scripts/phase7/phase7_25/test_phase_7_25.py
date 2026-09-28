#!/usr/bin/env python3
"""Phase 7.25 - suite di test: determinismo, baseline, concentrazione,
incertezza statistica, cost stress, execution realism, robustezza
temporale, visual audit, path anatomy, OOS, MVC, confronto, decision
card, verificatore, nessuna violazione di perimetro."""
import os
import sys
import unittest

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE725_DIR)
import build_liq_sweep_data_exposure_map as exposure_builder  # noqa: E402
import build_liq_sweep_baseline_economics as baseline_builder  # noqa: E402
import build_liq_sweep_concentration_analysis as concentration_builder  # noqa: E402
import build_liq_sweep_statistical_uncertainty as stats_builder  # noqa: E402
import build_liq_sweep_cost_stress as cost_builder  # noqa: E402
import build_liq_sweep_execution_realism as execn_builder  # noqa: E402
import build_liq_sweep_temporal_robustness as temporal_builder  # noqa: E402
import build_liq_sweep_visual_audit as visual_builder  # noqa: E402
import build_liq_sweep_path_anatomy as path_builder  # noqa: E402
import build_liq_sweep_oos_forward_analysis as oos_builder  # noqa: E402
import build_liq_sweep_minimum_viable_capital as mvc_builder  # noqa: E402
import build_liq_sweep_comparison_with_prior_strategies as comparison_builder  # noqa: E402
import build_liq_sweep_edge_decision_card as decision_builder  # noqa: E402
import verify_phase_7_25 as verifier  # noqa: E402

ARTIFACTS = [
    ("data_exposure_map_v1.json", exposure_builder.build),
    ("baseline_economics_v1.json", baseline_builder.build),
    ("concentration_analysis_v1.json", concentration_builder.build),
    ("statistical_uncertainty_v1.json", stats_builder.build),
    ("cost_stress_v1.json", cost_builder.build),
    ("execution_realism_v1.json", execn_builder.build),
    ("temporal_robustness_v1.json", temporal_builder.build),
    ("visual_audit_sample_v1.json", visual_builder.build),
    ("path_anatomy_v1.json", path_builder.build),
    ("oos_forward_analysis_v1.json", oos_builder.build),
    ("minimum_viable_capital_v1.json", mvc_builder.build),
    ("comparison_with_prior_strategies_v1.json", comparison_builder.build),
    ("decision_card_v1.json", decision_builder.build),
]


class TestDeterminism(unittest.TestCase):
    def test_all_artifacts_deterministic(self):
        for fname, build_fn in ARTIFACTS:
            saved = load_json(os.path.join(PHASE725_DIR, fname))
            self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(build_fn()), fname)


class TestDataExposureMap(unittest.TestCase):
    def test_forward_window_classified_true_oos(self):
        payload = exposure_builder.build()
        forward = next(p for p in payload["periods"] if p["category"] == "true_oos")
        self.assertTrue(forward["genuinely_untouched"])

    def test_net_pnl_declared_seen_not_blind(self):
        payload = exposure_builder.build()
        diagnostic = next(p for p in payload["periods"] if isinstance(p["category"], list))
        self.assertIn("net P&L totale ALL aggregato", " ".join(diagnostic["seen_for"]))


class TestBaselineEconomics(unittest.TestCase):
    def setUp(self):
        self.payload = baseline_builder.build()

    def test_42_closed_events(self):
        self.assertEqual(self.payload["ALL"]["n_trades"], 42)

    def test_no_side_eliminated(self):
        self.assertTrue(self.payload["no_side_eliminated_for_worse_performance"])
        self.assertGreater(self.payload["SELL"]["n_trades"], 0)

    def test_denominators_sum(self):
        d = self.payload["denominators_explicit"]
        self.assertEqual(d["BUY"] + d["SELL"], d["ALL"])


class TestConcentrationAnalysis(unittest.TestCase):
    def test_top_n_present(self):
        payload = concentration_builder.build()
        for k in ("top_1", "top_3", "top_5", "top_10pct"):
            self.assertIn(k, payload["concentration"])

    def test_without_top_n_present(self):
        payload = concentration_builder.build()
        self.assertIn("without_top_5", payload["concentration"]["without_top_n"])


class TestStatisticalUncertainty(unittest.TestCase):
    def test_iid_and_block_both_present(self):
        payload = stats_builder.build()
        r = payload["results"]["ALL"]
        self.assertIsNotNone(r["net_expectancy_bootstrap_ci_iid"])
        self.assertIsNotNone(r["net_expectancy_block_bootstrap_ci"])

    def test_iid_not_blindly_assumed_flag(self):
        payload = stats_builder.build()
        self.assertTrue(payload["iid_assumption_not_blindly_assumed"])


class TestCostStress(unittest.TestCase):
    def test_3_scenarios_present(self):
        payload = cost_builder.build()
        self.assertEqual(set(payload["scenarios"].keys()), {"COST_BASE", "COST_MODERATE", "COST_STRESS"})

    def test_costs_strictly_increasing(self):
        payload = cost_builder.build()
        costs = [payload["scenarios"][k]["extra_roundtrip_cost_assumed_price_units"]
                for k in ("COST_BASE", "COST_MODERATE", "COST_STRESS")]
        self.assertEqual(costs, sorted(costs))
        self.assertEqual(len(set(costs)), 3)


class TestExecutionRealism(unittest.TestCase):
    def test_funnel_all_stages_preserved(self):
        payload = execn_builder.build()
        fp = payload["funnel_all_stages_preserved_none_dropped"]
        for k in ("generated", "blocked", "open_attempt", "broker_reject", "opened",
                 "closed_within_window", "still_open_at_period_end"):
            self.assertIsNotNone(fp[k], k)

    def test_three_level_separation_present(self):
        payload = execn_builder.build()
        self.assertEqual(set(payload["three_level_separation"].keys()),
                        {"signal_level_opportunity", "executable_trade", "realized_trade"})


class TestTemporalRobustness(unittest.TestCase):
    def test_by_year_present(self):
        payload = temporal_builder.build()
        self.assertGreaterEqual(len(payload["by_year"]), 1)

    def test_rolling_window_present(self):
        payload = temporal_builder.build()
        self.assertIn(f"rolling_window_{payload['rolling_window_size']}_trades_mean_net", payload)


class TestVisualAudit(unittest.TestCase):
    def setUp(self):
        self.payload = visual_builder.build()

    def test_6_real_trade_events_sampled(self):
        self.assertEqual(self.payload["sample_size_real_trade_events"], 6)

    def test_stage_a_no_outcome_fields(self):
        forbidden = {"actual_pnl", "exit_timestamp", "exit_price", "exit_reason", "mfe", "mae",
                    "r_multiple"}
        for revs in self.payload["reviews"].values():
            for rev in revs:
                shown = set(rev["stage_a_blind_review"]["data_shown"])
                self.assertEqual(shown & forbidden, set())

    def test_forbidden_question_not_asked(self):
        for revs in self.payload["reviews"].values():
            for rev in revs:
                self.assertEqual(rev["stage_a_blind_review"]["forbidden_question_not_asked"], "Vincera'?")

    def test_charts_actually_generated_on_disk(self):
        charts_dir = os.path.join(PHASE725_DIR, "charts")
        for sid, paths in self.payload["chart_files"].items():
            for stage_paths in paths.values():
                for p in stage_paths.values():
                    full = os.path.join(ROOT, p)
                    self.assertTrue(os.path.exists(full), full)

    def test_blocked_near_miss_declared_gap_not_fabricated(self):
        self.assertEqual(self.payload["blocked_near_miss"]["status"], "GAP_DICHIARATO_NON_FABBRICATO")

    def test_matched_non_event_produced(self):
        self.assertIn("control_datetime", self.payload["matched_non_event"])
        for p in self.payload["matched_non_event"]["charts"].values():
            self.assertTrue(os.path.exists(os.path.join(ROOT, p)))


class TestPathAnatomy(unittest.TestCase):
    def test_descriptive_flag(self):
        payload = path_builder.build()
        self.assertTrue(payload["descriptive_only_no_new_rule_derived"])

    def test_per_event_matches_closed_count(self):
        payload = path_builder.build()
        self.assertEqual(payload["summary"]["n_events_total"], 42)


class TestOOSForwardAnalysis(unittest.TestCase):
    def test_status_known(self):
        payload = oos_builder.build()
        self.assertIn(payload.get("status") or payload.get("decision"),
                     {"RUN_NOT_YET_LAUNCHED", "RUN_NOT_YET_COLLECTED", "INSUFFICIENT_OOS_SAMPLE",
                      "SAMPLE_SUFFICIENT_FOR_A_FIRST_READ"})

    def test_window_genuinely_untouched_if_available(self):
        payload = oos_builder.build()
        if "window_genuinely_untouched" in payload:
            self.assertTrue(payload["window_genuinely_untouched"])


class TestMinimumViableCapital(unittest.TestCase):
    def test_mvc_defined(self):
        payload = mvc_builder.build()
        self.assertIsNotNone(payload["MINIMUM_VIABLE_CAPITAL_EUR"])

    def test_no_sizing_proposed(self):
        payload = mvc_builder.build()
        self.assertTrue(payload["no_optimization_no_sizing_proposed"])


class TestComparison(unittest.TestCase):
    def test_three_strategies_present(self):
        payload = comparison_builder.build()
        self.assertEqual(set(payload["comparison_table"].keys()),
                        {"BREAKOUT_ACC", "ORDER_BLOCK", "LIQ_SWEEP"})

    def test_descriptive_not_ranking_flag(self):
        payload = comparison_builder.build()
        self.assertIn("descriptive_not_ranking", payload)


class TestDecisionCard(unittest.TestCase):
    def test_decision_allowed(self):
        payload = decision_builder.build()
        allowed = {"EDGE_VALIDATED_PRELIMINARY", "EDGE_CANDIDATE_REQUIRES_OOS",
                  "EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION", "EDGE_NOT_SUPPORTED",
                  "INSUFFICIENT_EVIDENCE"}
        self.assertIn(payload["decision"], allowed)

    def test_not_live_ready(self):
        payload = decision_builder.build()
        self.assertFalse(payload["decision_means_live_ready"])

    def test_no_optimization_flag(self):
        payload = decision_builder.build()
        self.assertTrue(payload["no_optimization_performed"])


class TestNoScopeViolations(unittest.TestCase):
    def test_no_mql5_product_platform_changes(self):
        import subprocess
        result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                                "contracts/"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")

    def test_prior_phases_untouched(self):
        import subprocess
        for phase_dir in ("phase7_21", "phase7_22", "phase7_23", "phase7_24"):
            result = subprocess.run(["git", "diff", "--name-only", "--",
                                    f"server/research_scripts/phase7/{phase_dir}"],
                                   cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.stdout.strip(), "", phase_dir)


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        self.assertEqual(verifier.verify(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
