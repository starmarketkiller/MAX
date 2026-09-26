#!/usr/bin/env python3
"""Phase 7.9H - suite di test di consistenza per il dataset canonico
BREAKOUT_ACC_INTENDED_D1_V1."""
import os
import subprocess
import sys
import unittest

PHASE79H_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79H_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE79H_DIR)
import build_b_only_residual_classification as b_only_builder  # noqa: E402
import build_canonical_event_dataset as dataset_builder  # noqa: E402
import build_dataset_validation_and_deliverables as validation_builder  # noqa: E402
import verify_phase_7_9h as verifier  # noqa: E402


class TestDeterminism(unittest.TestCase):
    def test_dataset_build_deterministic(self):
        a = dataset_builder.build()
        b = dataset_builder.build()
        self.assertEqual(canonical_sha256(a), canonical_sha256(b))

    def test_saved_dataset_matches_fresh_build(self):
        saved = load_json(os.path.join(PHASE79H_DIR, "breakout_acc_intended_d1_v1_dataset.json"))
        fresh = dataset_builder.build()
        self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(fresh))

    def test_saved_validation_matches_fresh_build(self):
        saved = load_json(os.path.join(PHASE79H_DIR, "phase_7_9h_validation_and_decision_v1.json"))
        fresh = validation_builder.build()
        self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(fresh))


class TestEventIdUniquenessAndStability(unittest.TestCase):
    def setUp(self):
        self.events = dataset_builder.build()["events"]

    def test_all_ids_unique(self):
        ids = [e["event_id"] for e in self.events]
        self.assertEqual(len(ids), len(set(ids)))

    def test_id_is_deterministic_function_of_strategy_direction_date(self):
        for e in self.events:
            recomputed = dataset_builder.event_id("BREAKOUT_ACC", e["direction"], e["d1_bar_date"])
            self.assertEqual(e["event_id"], recomputed)

    def test_id_changes_if_direction_differs(self):
        a = dataset_builder.event_id("BREAKOUT_ACC", 1, "2020.01.01")
        b = dataset_builder.event_id("BREAKOUT_ACC", -1, "2020.01.01")
        self.assertNotEqual(a, b)

    def test_id_changes_if_date_differs(self):
        a = dataset_builder.event_id("BREAKOUT_ACC", 1, "2020.01.01")
        b = dataset_builder.event_id("BREAKOUT_ACC", 1, "2020.01.02")
        self.assertNotEqual(a, b)

    def test_id_stable_across_repeated_calls(self):
        a = dataset_builder.event_id("BREAKOUT_ACC", 1, "2020.01.01")
        b = dataset_builder.event_id("BREAKOUT_ACC", 1, "2020.01.01")
        self.assertEqual(a, b)


class TestFunnelPopulation(unittest.TestCase):
    def setUp(self):
        self.payload = dataset_builder.build()
        self.events = self.payload["events"]

    def test_total_75_events(self):
        self.assertEqual(len(self.events), 75)

    def test_funnel_counts(self):
        c = self.payload["counts_by_terminal_stage"]
        self.assertEqual(c["OPENED"], 47)
        self.assertEqual(c["BLOCKED"], 11)
        self.assertEqual(c["BROKER_REJECT"], 9)
        self.assertEqual(c["NEVER_OBSERVED_IN_LIVE_TRACE"], 8)

    def test_no_selection_bias_blocked_and_rejected_present(self):
        blocked = [e for e in self.events if e["funnel_terminal_stage"] == "BLOCKED"]
        rejected = [e for e in self.events if e["funnel_terminal_stage"] == "BROKER_REJECT"]
        self.assertEqual(len(blocked), 11)
        self.assertEqual(len(rejected), 9)

    def test_b_only_residual_retained(self):
        b_only = [e for e in self.events
                  if e["population_source"] == "OFFLINE_ISOLATED_RECONSTRUCTION_ONLY"]
        self.assertEqual(len(b_only), 8)


class TestFillAndSignalPriceDistinction(unittest.TestCase):
    def setUp(self):
        self.opened = [e for e in dataset_builder.build()["events"]
                       if e["funnel_terminal_stage"] == "OPENED"]

    def test_all_opened_have_verified_fill(self):
        self.assertTrue(all(e["fill_stage"] == "FILLED" for e in self.opened))
        self.assertEqual(len(self.opened), 47)

    def test_signal_price_and_fill_price_are_separate_fields(self):
        for e in self.opened:
            self.assertIn("signal_price", e)
            self.assertIn("entry_fill_price", e)
            self.assertIn("signal_to_fill_slippage_price_units", e)

    def test_non_opened_events_have_no_fill_fields(self):
        for e in dataset_builder.build()["events"]:
            if e["funnel_terminal_stage"] != "OPENED":
                self.assertNotIn("entry_fill_price", e)

    def test_fill_price_source_documented(self):
        for e in self.opened:
            self.assertIn("HistoryDealGetDouble", e["entry_fill_price_source"])


class TestPostEntryPathAnatomy(unittest.TestCase):
    def setUp(self):
        self.payload = dataset_builder.build()
        self.opened = [e for e in self.payload["events"] if e["funnel_terminal_stage"] == "OPENED"]

    def test_all_opened_have_path_anatomy(self):
        self.assertTrue(all("post_entry_path_anatomy" in e for e in self.opened))

    def test_horizons_are_preregistered_not_tp_sl_based(self):
        expected = {f"fwd_return_{h}d1_price_units" for h in self.payload["preregistered_horizons_d1_bars"]}
        for e in self.opened:
            path = e["post_entry_path_anatomy"]
            if path.get("status") == "OK":
                self.assertEqual(set(path["horizons"].keys()), expected)

    def test_mfe_mae_present_when_status_ok(self):
        for e in self.opened:
            path = e["post_entry_path_anatomy"]
            if path.get("status") == "OK":
                self.assertIn("mfe_price_units", path)
                self.assertIn("mae_price_units", path)
                self.assertGreaterEqual(path["mfe_price_units"], 0)
                self.assertGreaterEqual(path["mae_price_units"], 0)


class TestBOnlyResidualClassification(unittest.TestCase):
    def setUp(self):
        self.payload = b_only_builder.build()

    def test_8_events_classified(self):
        self.assertEqual(len(self.payload["events"]), 8)

    def test_no_ea_modification_flag(self):
        self.assertTrue(self.payload["no_ea_modification_this_phase"])

    def test_cross_tf_contamination_ruled_out_for_all(self):
        for e in self.payload["events"]:
            mechanisms = [r["mechanism"] for r in e["ruled_out"]]
            self.assertIn("CROSS_TIMEFRAME_STATE_CONTAMINATION (il meccanismo originale "
                          "IMPLEMENTATION_DEFECT_CONFIRMED di Phase 7.9E/F/G)", mechanisms)

    def test_no_events_asserted_with_false_certainty(self):
        for e in self.payload["events"]:
            self.assertEqual(e["causal_status"],
                             "PARTIALLY_EXPLAINED_NOT_ENOUGH_EVIDENCE_FOR_EXACT_MECHANISM")

    def test_pre_fix_overlap_dates_flagged(self):
        by_date = {e["d1_bar_date"]: e for e in self.payload["events"]}
        self.assertTrue(by_date["2019.04.18"]["previously_analyzed_pre_fix"])
        self.assertTrue(by_date["2019.05.15"]["previously_analyzed_pre_fix"])
        self.assertFalse(by_date["2019.05.15"]["resolved_by_7_9g_fix"])


class TestValidationAndDecision(unittest.TestCase):
    def setUp(self):
        self.payload = validation_builder.build()

    def test_all_checks_pass(self):
        self.assertTrue(self.payload["all_checks_passed"])

    def test_final_decision_in_allowed_set(self):
        self.assertIn(self.payload["final_decision"], self.payload["final_decision_allowed_values"])

    def test_final_decision_is_ready(self):
        self.assertEqual(self.payload["final_decision"],
                         "CANONICAL_DATASET_READY_FOR_MECHANISM_RESEARCH")

    def test_no_profitability_verdict_flag(self):
        self.assertTrue(self.payload["no_profitability_verdict"])

    def test_ten_deliverables_present(self):
        keys = [k for k in self.payload["deliverables"] if k[0].isdigit()]
        self.assertEqual(len(keys), 10)

    def test_next_step_not_executed(self):
        self.assertIn("NON iniziato", self.payload["next_step_not_executed"])


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        errors = verifier.verify()
        self.assertEqual(errors, [])

    def test_no_mql5_or_python_files_modified_this_phase(self):
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", "MQL5/", "server/backtest.py"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
