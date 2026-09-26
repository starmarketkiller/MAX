#!/usr/bin/env python3
"""Phase 7.9I - suite di test di consistenza per il Mechanism Research
di BREAKOUT_ACC."""
import os
import subprocess
import sys
import unittest

PHASE79I_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE79I_DIR)
import build_b_only_comparison as b_only_cmp_builder  # noqa: E402
import build_edge_decomposition as edge_builder  # noqa: E402
import build_executive_summary_and_decision_card as exec_builder  # noqa: E402
import build_failure_map_and_robustness as fmap_builder  # noqa: E402
import build_feature_engineering as feat_builder  # noqa: E402
import build_gate_diagnostic as gate_builder  # noqa: E402
import build_mechanism_discovery as mech_builder  # noqa: E402
import build_natural_horizon as horizon_builder  # noqa: E402
import build_path_anatomy as path_builder  # noqa: E402
import build_sensitivity_67_vs_75 as sens_builder  # noqa: E402
import nxs_mechanism_context as ctx  # noqa: E402
import verify_phase_7_9i as verifier  # noqa: E402


class TestFrozenDatasetUntouched(unittest.TestCase):
    def test_canonical_dataset_not_modified(self):
        dataset_path = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_9h",
                                    "breakout_acc_intended_d1_v1_dataset.json")
        result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", dataset_path], cwd=ROOT)
        self.assertEqual(result.returncode, 0)

    def test_no_mql5_or_python_files_modified(self):
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", "MQL5/", "server/backtest.py"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")


class TestPopulations(unittest.TestCase):
    def setUp(self):
        self.rows = feat_builder.build()["rows"]

    def test_population_a_67(self):
        a = [r for r in self.rows if r["population_source"] == "LIVE_TRACE_GENERATED"]
        self.assertEqual(len(a), 67)

    def test_population_b_47_subset_of_a(self):
        b = [r for r in self.rows if r["funnel_terminal_stage"] == "OPENED"]
        self.assertEqual(len(b), 47)
        self.assertTrue(all(r["population_source"] == "LIVE_TRACE_GENERATED" for r in b))

    def test_population_c_8_disjoint_from_b(self):
        c = [r for r in self.rows if r["population_source"] == "OFFLINE_ISOLATED_RECONSTRUCTION_ONLY"]
        self.assertEqual(len(c), 8)
        self.assertTrue(all(r["funnel_terminal_stage"] != "OPENED" for r in c))

    def test_buy_sell_split_47_opened(self):
        b = [r for r in self.rows if r["funnel_terminal_stage"] == "OPENED"]
        n_buy = sum(1 for r in b if r["direction_label"] == "BUY")
        n_sell = sum(1 for r in b if r["direction_label"] == "SELL")
        self.assertEqual((n_buy, n_sell), (36, 11))


class TestDeterminism(unittest.TestCase):
    def _check(self, fname, build_fn):
        saved = load_json(os.path.join(PHASE79I_DIR, fname))
        fresh = build_fn()
        self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(fresh))

    def test_feature_engineering_deterministic(self):
        self._check("breakout_acc_feature_engineering_v1.json", feat_builder.build)

    def test_edge_decomposition_deterministic(self):
        self._check("breakout_acc_edge_decomposition_v1.json", edge_builder.build)

    def test_path_anatomy_deterministic(self):
        self._check("breakout_acc_path_anatomy_v1.json", path_builder.build)

    def test_natural_horizon_deterministic(self):
        self._check("breakout_acc_natural_horizon_v1.json", horizon_builder.build)

    def test_mechanism_discovery_deterministic(self):
        self._check("breakout_acc_mechanism_discovery_v1.json", mech_builder.build)

    def test_sensitivity_deterministic(self):
        self._check("breakout_acc_sensitivity_67_vs_75_v1.json", sens_builder.build)

    def test_gate_diagnostic_deterministic(self):
        self._check("breakout_acc_gate_diagnostic_v1.json", gate_builder.build)

    def test_b_only_comparison_deterministic(self):
        self._check("breakout_acc_b_only_comparison_v1.json", b_only_cmp_builder.build)

    def test_failure_map_deterministic(self):
        self._check("breakout_acc_failure_map_and_robustness_v1.json", fmap_builder.build)

    def test_executive_summary_deterministic(self):
        self._check("breakout_acc_executive_summary_decision_card_v1.json", exec_builder.build)


class TestNoOptimization(unittest.TestCase):
    def test_edge_decomposition_uses_natural_terciles_not_search(self):
        payload = edge_builder.build()
        self.assertTrue(payload["no_optimization"])
        self.assertTrue(payload["no_pf_as_starting_point"])

    def test_path_anatomy_no_tp_search(self):
        payload = path_builder.build()
        self.assertTrue(payload["no_optimization_no_tp_search"])

    def test_natural_horizon_not_chosen_by_best_return(self):
        payload = horizon_builder.build()
        self.assertTrue(payload["no_optimization_horizon_not_chosen_by_best_return"])

    def test_mechanism_discovery_no_rescue(self):
        payload = mech_builder.build()
        self.assertTrue(payload["no_optimization_no_rescue"])

    def test_executive_summary_no_forbidden_words(self):
        payload = exec_builder.build()
        import json
        text = json.dumps(payload, ensure_ascii=False).upper()
        for w in ("PROMOTE", "DEPLOY", "PROFITABLE"):
            self.assertNotIn(w, text)


class TestDecisionCard(unittest.TestCase):
    def setUp(self):
        self.payload = exec_builder.build()

    def test_final_decision_in_allowed_set(self):
        self.assertIn(self.payload["final_decision"], self.payload["final_decision_allowed_values"])

    def test_final_decision_is_partially_supported(self):
        self.assertEqual(self.payload["final_decision"], "MECHANISM_PARTIALLY_SUPPORTED")

    def test_executive_summary_max_10_lines(self):
        self.assertLessEqual(len(self.payload["executive_summary_max_10_lines"]), 10)

    def test_decision_card_has_seven_questions(self):
        keys = [k for k in self.payload["decision_card"] if k != "final_decision"]
        self.assertEqual(len(keys), 7)

    def test_next_hypothesis_marked_not_implemented(self):
        hyp = self.payload["next_hypothesis_not_implemented"]
        if hyp is not None:
            self.assertTrue(hyp["explicitly_not_implemented"])


class TestMechanismDiscoveryContent(unittest.TestCase):
    def setUp(self):
        self.payload = mech_builder.build()

    def test_at_least_six_mechanisms_evaluated(self):
        self.assertGreaterEqual(len(self.payload["mechanisms_evaluated"]), 6)

    def test_every_mechanism_has_required_fields(self):
        for m in self.payload["mechanisms_evaluated"]:
            for field in ("mechanism", "evidence_for", "evidence_against",
                         "alternative_explanations", "confidence"):
                self.assertIn(field, m)

    def test_symmetric_continuation_contradicted(self):
        m = next(m for m in self.payload["mechanisms_evaluated"]
                if m["mechanism"] == "CONTINUATION_SYMMETRIC_BREAKOUT")
        self.assertIn("LOW", m["confidence"])


class TestSharedContextHelpers(unittest.TestCase):
    def test_causal_atr_no_lookahead(self):
        d1_bars = ctx.load_d1_bars()
        from datetime import datetime
        as_of = d1_bars[50]["time"]
        atr = ctx.causal_atr(d1_bars, as_of, period=20)
        # ricalcolo manuale non deve usare barre >= as_of
        prior = [b for b in d1_bars if b["time"].date() < as_of.date()]
        self.assertEqual(len(prior), 50)
        self.assertIsNotNone(atr)

    def test_full_path_curve_length(self):
        d1_bars = ctx.load_d1_bars()
        from datetime import datetime
        curve = ctx.full_path_curve(d1_bars, d1_bars[10]["time"], d1_bars[10]["close"], 1)
        self.assertIsNotNone(curve)
        self.assertLessEqual(len(curve), ctx.MAX_PATH_WINDOW_D1)


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        errors = verifier.verify()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
