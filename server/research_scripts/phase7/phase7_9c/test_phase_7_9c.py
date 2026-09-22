#!/usr/bin/env python3
"""Phase 7.9C - suite di consistenza (stesso pattern delle fasi precedenti)."""
import json
import os
import sys
import unittest

PHASE79C_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79C_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
sys.path.insert(0, PHASE79C_DIR)
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402
import build_breakoutacc_parity_decomposition as builder  # noqa: E402
import verify_breakoutacc_parity_decomposition as verifier  # noqa: E402

MATRIX_PATH = os.path.join(PHASE79C_DIR, "breakout_acc_event_parity_matrix_v1.json")
DECISION_PATH = os.path.join(PHASE79C_DIR, "breakout_acc_parity_decision_v1.json")


class TestDeliverablesExist(unittest.TestCase):
    def test_all_deliverable_files_present(self):
        for fname in (
            "breakout_acc_python_event_stream_v1.csv", "breakout_acc_python_event_stream_v1.json",
            "breakout_acc_mt5_event_stream_v1.csv", "breakout_acc_mt5_event_stream_v1.json",
            "breakout_acc_event_parity_matrix_v1.json", "breakout_acc_parity_decision_v1.json",
        ):
            p = os.path.join(PHASE79C_DIR, fname)
            self.assertTrue(os.path.exists(p), f"manca {fname}")
            self.assertGreater(os.path.getsize(p), 0, f"{fname} e' vuoto")


class TestCanonicalHashIntegrity(unittest.TestCase):
    def test_matrix_hash_matches_payload(self):
        env = load_json(MATRIX_PATH)
        self.assertEqual(canonical_sha256(env["payload"]), env["canonical_sha256"])

    def test_decision_hash_matches_payload(self):
        env = load_json(DECISION_PATH)
        self.assertEqual(canonical_sha256(env["payload"]), env["canonical_sha256"])

    def test_rebuild_is_deterministic(self):
        p1 = builder.build()
        p2 = builder.build()
        self.assertEqual(canonical_sha256(p1), canonical_sha256(p2))


class TestScopeConstraints(unittest.TestCase):
    def setUp(self):
        self.payload = load_json(MATRIX_PATH)["payload"]

    def test_no_serious_backtest_flags(self):
        for flag in ("no_new_serious_backtest", "no_optimization", "no_strategy_modification",
                     "no_pnl_used_for_diagnosis"):
            self.assertTrue(self.payload[flag], flag)

    def test_frozen_candidates_not_reopened(self):
        self.assertTrue(self.payload["volbrk_not_reopened"])
        self.assertTrue(self.payload["h006_not_reopened"])
        self.assertTrue(self.payload["hvcw_backlog_only"])

    def test_no_pnl_terms_in_artifact(self):
        text = json.dumps(self.payload).lower()
        for term in ("expectancy", "\"pf\":", "profit_factor", "win_rate"):
            self.assertNotIn(term, text)

    def test_phase_e_source_untouched(self):
        path = os.path.join(ROOT, "results", "cost_calibration_67_rerun", "phase_e_breakoutacc_findings.json")
        declared = self.payload["source_artifacts_untouched"]["phase_e_findings"]["sha256"]
        self.assertEqual(file_sha256(path), declared)


class TestVerdictAndDecisionAllowedSets(unittest.TestCase):
    def setUp(self):
        self.payload = load_json(MATRIX_PATH)["payload"]
        self.decision = load_json(DECISION_PATH)["payload"]

    def test_final_verdict_in_allowed_set(self):
        allowed = {"SIGNAL_PARITY_CONFIRMED", "SIGNAL_PARITY_PARTIAL", "SIGNAL_PARITY_FAILED",
                   "EXECUTION_GAP_DOMINANT", "DATA_FEED_GAP_DOMINANT", "MULTI_CAUSE_PARITY_GAP"}
        self.assertIn(self.payload["final_verdict"], allowed)

    def test_next_decision_in_allowed_set(self):
        allowed = {"REANALYZE_EXISTING_RAW_RESULTS", "FIX_PARITY_BEFORE_STATISTICS", "DATA_SOURCE_SENSITIVITY_STUDY"}
        self.assertIn(self.payload["next_decision"]["decision"], allowed)

    def test_decision_artifact_consistent_with_matrix(self):
        self.assertEqual(self.decision["final_verdict"], self.payload["final_verdict"])
        self.assertEqual(self.decision["next_decision"], self.payload["next_decision"]["decision"])

    def test_next_step_not_executed(self):
        self.assertTrue(self.decision["next_step_not_executed"])


class TestPairingArithmetic(unittest.TestCase):
    def setUp(self):
        self.pairing = load_json(MATRIX_PATH)["payload"]["pairing"]

    def test_matched_plus_only_equals_totals(self):
        self.assertEqual(self.pairing["matched"] + self.pairing["mt5_only"], self.pairing["mt5_signal_fire_total"])
        self.assertEqual(self.pairing["matched"] + self.pairing["python_only"], self.pairing["python_signal_total"])

    def test_signal_scale_comparable_not_orders_of_magnitude_apart(self):
        # La scoperta centrale di questa fase: gli stream di SEGNALE sono
        # comparabili in scala (non un fattore 5-25x come 27-vs-4/101-vs-4).
        ratio = self.pairing["mt5_signal_fire_total"] / self.pairing["python_signal_total"]
        self.assertGreater(ratio, 0.5)
        self.assertLess(ratio, 2.0)


class TestExecutionGapIsTheRealFinding(unittest.TestCase):
    def setUp(self):
        self.exec_parity = load_json(MATRIX_PATH)["payload"]["signal_vs_execution_parity"]["execution_parity"]

    def test_mt5_trades_executed_phase_e_is_4(self):
        self.assertEqual(self.exec_parity["mt5_trades_executed_phase_e"], 4)

    def test_execution_rate_is_small_fraction_of_signal_fire(self):
        self.assertLess(self.exec_parity["execution_rate_pct"], 15.0)

    def test_naive_simulation_does_not_explain_full_gap(self):
        sim = self.exec_parity["one_position_at_a_time_naive_simulation"]
        self.assertGreater(sim["simulated_executed"], self.exec_parity["mt5_trades_executed_phase_e"] * 5)


class TestIndependentVerifierPasses(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        errors = verifier.verify()
        self.assertEqual(errors, [], f"il verificatore indipendente ha trovato problemi: {errors}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
