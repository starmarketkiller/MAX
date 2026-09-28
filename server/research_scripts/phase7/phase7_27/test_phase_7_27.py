#!/usr/bin/env python3
"""Phase 7.27 - suite di test: determinismo, preregistrazione,
generatori di benchmark (causalita', determinismo del seed), metriche
di outcome, risultati per-strategia/cross-strategy, multiple testing,
decisione, aggiornamenti al Safety Net (Phase 7.26), verificatore,
nessuna violazione di perimetro."""
import os
import sys
import unittest
from datetime import datetime

PHASE727_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE727_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE727_DIR)
import nxs_prereg_constants as C  # noqa: E402
import build_preregistration as prereg_builder  # noqa: E402
import build_benchmark_samples as samples_builder  # noqa: E402
import build_per_strategy_results as per_strat_builder  # noqa: E402
import build_regime_controlled_analysis as regime_builder  # noqa: E402
import build_cross_strategy_results as cross_builder  # noqa: E402
import build_multiple_testing_accounting as mtest_builder  # noqa: E402
import build_buy_dominance_decision_card as decision_builder  # noqa: E402
import verify_phase_7_27 as verifier  # noqa: E402
from nxs_benchmark_generators import (random_timestamps_matched, regime_matched_random,  # noqa: E402
                                      seed_for)
from nxs_regime_classifier import regime_for_index, build_regime_table  # noqa: E402
from nxs_gold_d1_loader import bar_index_for_date  # noqa: E402
from nxs_outcome_metrics import compute_outcome_metrics  # noqa: E402

ARTIFACTS = [
    ("preregistration_v1.json", prereg_builder.build),
    ("benchmark_samples_v1.json", samples_builder.build),
    ("per_strategy_results_v1.json", per_strat_builder.build),
    ("regime_controlled_analysis_v1.json", regime_builder.build),
    ("cross_strategy_results_v1.json", cross_builder.build),
    ("multiple_testing_accounting_v1.json", mtest_builder.build),
    ("decision_card_v1.json", decision_builder.build),
]


class TestDeterminism(unittest.TestCase):
    def test_all_artifacts_deterministic(self):
        for fname, build_fn in ARTIFACTS:
            saved = load_json(os.path.join(PHASE727_DIR, fname))
            self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(build_fn()), fname)


class TestPreregistration(unittest.TestCase):
    def test_frozen_flags_true(self):
        payload = prereg_builder.build()
        self.assertTrue(payload["frozen_before_any_result_examined"])
        self.assertTrue(payload["no_benchmark_change_after_seeing_results"])
        self.assertTrue(payload["datasets_are_discovery_not_holdout"])

    def test_3_strategies_no_tsi(self):
        payload = prereg_builder.build()
        self.assertEqual(set(payload["strategies_included"]), {"BREAKOUT_ACC", "ORDER_BLOCK", "LIQ_SWEEP"})

    def test_5_benchmarks_declared(self):
        payload = prereg_builder.build()
        self.assertEqual(len(payload["benchmarks"]), 5)


class TestSeedDeterminism(unittest.TestCase):
    def test_seed_stable_across_calls(self):
        s1 = seed_for("BREAKOUT_ACC", "RANDOM_TIMESTAMPS_MATCHED")
        s2 = seed_for("BREAKOUT_ACC", "RANDOM_TIMESTAMPS_MATCHED")
        self.assertEqual(s1, s2)

    def test_random_sample_reproducible(self):
        start, end = datetime(2019, 2, 21), datetime(2026, 6, 9)
        seed = seed_for("BREAKOUT_ACC", "RANDOM_TIMESTAMPS_MATCHED")
        r1 = random_timestamps_matched(start, end, 36, seed)
        r2 = random_timestamps_matched(start, end, 36, seed)
        self.assertEqual(r1, r2)


class TestRegimeMatchingCausality(unittest.TestCase):
    def test_regime_uses_only_trailing_data(self):
        df = build_regime_table()
        early_idx = 10  # troppo presto per avere SMA50/ATR14 completi
        r = regime_for_index(early_idx)
        self.assertIsNone(r["trend"])

    def test_regime_matched_excludes_self_index(self):
        start, end = datetime(2019, 2, 21), datetime(2026, 6, 9)
        real_idx = bar_index_for_date(datetime(2019, 6, 5))
        matched = regime_matched_random([real_idx], start, end, seed_for("BREAKOUT_ACC", "REGIME_MATCHED_RANDOM_LONG"))
        self.assertNotEqual(matched[0], real_idx)


class TestOutcomeMetrics(unittest.TestCase):
    def test_metrics_have_all_horizons(self):
        m = compute_outcome_metrics(500)
        for h in C.HORIZONS_D1_BARS:
            self.assertIn(f"h{h}", m["horizons"])

    def test_censored_near_end_of_series(self):
        from nxs_gold_d1_loader import load_d1
        last_idx = len(load_d1()) - 1
        m = compute_outcome_metrics(last_idx)
        self.assertFalse(m["data_available"])


class TestPerStrategyResults(unittest.TestCase):
    def test_3_strategies_kept_separate(self):
        payload = per_strat_builder.build()
        self.assertEqual(set(payload.keys()), {"BREAKOUT_ACC", "ORDER_BLOCK", "LIQ_SWEEP"})

    def test_order_block_sample_limitation_declared(self):
        payload = per_strat_builder.build()
        self.assertIsNotNone(payload["ORDER_BLOCK"]["sample_size_limitation"])

    def test_regime_matched_is_paired_design(self):
        payload = per_strat_builder.build()
        for strat in payload:
            self.assertEqual(payload[strat]["per_benchmark_results"]["REGIME_MATCHED_RANDOM_LONG"]["design"],
                            "PAIRED")


class TestCrossStrategyResults(unittest.TestCase):
    def test_pattern_in_declared_options(self):
        payload = cross_builder.build()
        self.assertIn(payload["cross_strategy_pattern"], payload["pattern_options_declared"])

    def test_concordance_not_automatic_edge_flag(self):
        payload = cross_builder.build()
        self.assertTrue(payload["concordance_not_automatically_edge"])


class TestMultipleTestingAccounting(unittest.TestCase):
    def test_primary_less_than_total(self):
        payload = mtest_builder.build()
        self.assertLess(payload["n_primary_comparisons_used_for_decision"],
                        payload["n_total_statistical_comparisons_this_phase"])

    def test_no_cherry_picking_flag(self):
        payload = mtest_builder.build()
        self.assertTrue(payload["no_cherry_picking_most_favorable_comparison_for_decision"])


class TestDecisionCard(unittest.TestCase):
    def test_decision_allowed(self):
        payload = decision_builder.build()
        self.assertIn(payload["decision"], C.DECISION_ALLOWED)

    def test_never_edge_validated(self):
        payload = decision_builder.build()
        self.assertNotIn("EDGE_VALIDATED", payload["decision"].upper())

    def test_no_optimization_no_deploy(self):
        payload = decision_builder.build()
        self.assertTrue(payload["no_optimization_no_deploy"])


class TestSafetyNetUpdates(unittest.TestCase):
    def test_new_hypothesis_registered(self):
        phase726_dir = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_26")
        sys.path.insert(0, phase726_dir)
        import build_hypothesis_registry as hb
        hyp = {h["hypothesis_id"] for h in hb.build()["hypotheses"]}
        self.assertIn("H_BUY_DOMINANCE_MARKET_REGIME_ARTIFACT", hyp)

    def test_new_hypothesis_not_prematurely_supported(self):
        phase726_dir = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_26")
        sys.path.insert(0, phase726_dir)
        import build_hypothesis_registry as hb
        hyp = {h["hypothesis_id"]: h for h in hb.build()["hypotheses"]}
        h = hyp["H_BUY_DOMINANCE_MARKET_REGIME_ARTIFACT"]
        self.assertEqual(h["lifecycle_state"], "TESTING")

    def test_priority_queue_marks_completed(self):
        phase726_dir = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_26")
        sys.path.insert(0, phase726_dir)
        import build_research_priority_queue as pq
        payload = pq.build()
        c = next(c for c in payload["ranked_candidates"] if c["candidate_id"] == "BUY_BIAS_BENCHMARK_VS_BUY_AND_HOLD")
        self.assertEqual(c["status"], "COMPLETED_PHASE_7_27")
        self.assertNotEqual(payload["top_priority"], "BUY_BIAS_BENCHMARK_VS_BUY_AND_HOLD")

    def test_existing_strategy_verdicts_not_reinterpreted(self):
        """I verdict originali (H1/H_ORDER_BLOCK/H_LIQ_SWEEP) devono restare
        gli stessi lifecycle_state gia' assegnati in Phase 7.26."""
        phase726_dir = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_26")
        sys.path.insert(0, phase726_dir)
        import build_hypothesis_registry as hb
        hyp = {h["hypothesis_id"]: h for h in hb.build()["hypotheses"]}
        self.assertEqual(hyp["H1_BREAKOUT_ACC_NET_EXPECTANCY_POSITIVE"]["lifecycle_state"], "INCONCLUSIVE")
        self.assertEqual(hyp["H_ORDER_BLOCK_EDGE_EXISTS"]["lifecycle_state"], "INCONCLUSIVE")
        self.assertEqual(hyp["H_LIQ_SWEEP_EDGE_EXISTS"]["lifecycle_state"], "INCONCLUSIVE")

    def test_phase726_verifier_still_clean(self):
        phase726_dir = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_26")
        sys.path.insert(0, phase726_dir)
        import verify_phase_7_26
        self.assertEqual(verify_phase_7_26.verify(), [])


class TestNoScopeViolations(unittest.TestCase):
    def test_no_mql5_product_platform_changes(self):
        import subprocess
        result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                                "contracts/"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")

    def test_prior_phases_untouched(self):
        import subprocess
        for phase_dir in verifier.FROZEN_PHASE_DIRS:
            result = subprocess.run(["git", "diff", "--name-only", "--",
                                    f"server/research_scripts/phase7/{phase_dir}"],
                                   cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.stdout.strip(), "", phase_dir)


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        self.assertEqual(verifier.verify(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
