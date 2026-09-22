#!/usr/bin/env python3
"""Phase 7.9D - suite di consistenza (stesso pattern delle fasi precedenti)."""
import json
import os
import sys
import unittest

PHASE79D_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79D_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
sys.path.insert(0, PHASE79D_DIR)
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402
import build_execution_funnel_map as funnel_builder  # noqa: E402
import build_execution_events_and_gate_counts as ev_builder  # noqa: E402
import build_execution_parity_decision as decision_builder  # noqa: E402
import verify_execution_gate_decomposition as verifier  # noqa: E402

FUNNEL_PATH = os.path.join(PHASE79D_DIR, "breakout_acc_execution_funnel_v1.json")
EVENTS_PATH = os.path.join(PHASE79D_DIR, "breakout_acc_execution_events_v1.json")
COUNTS_PATH = os.path.join(PHASE79D_DIR, "breakout_acc_execution_gate_counts_v1.json")
DECISION_PATH = os.path.join(PHASE79D_DIR, "breakout_acc_execution_parity_decision_v1.json")

ALLOWED_VERDICTS = {
    "EXISTING_POSITION_GATE_DOMINANT", "RISK_GATE_DOMINANT", "PREFLIGHT_GATE_DOMINANT",
    "ORDER_EXECUTION_FAILURE_DOMINANT", "ROUTER_GATE_DOMINANT", "MULTI_GATE_EXECUTION_LOSS",
    "EXECUTION_GAP_RESOLVED_OTHER", "EXECUTION_GAP_STILL_UNRESOLVED",
}
ALLOWED_NEXT_DECISIONS = {
    "REBUILD_CANONICAL_BREAKOUT_ACC_DATASET", "FIX_EXECUTION_IMPLEMENTATION_BEFORE_RESEARCH",
    "BLOCKED_EXECUTION_IDENTITY_UNRESOLVED",
}


class TestDeliverablesExist(unittest.TestCase):
    def test_all_files_present(self):
        for fname in (
            "breakout_acc_execution_funnel_v1.json", "breakout_acc_execution_events_v1.csv",
            "breakout_acc_execution_events_v1.json", "breakout_acc_execution_gate_counts_v1.json",
            "breakout_acc_execution_parity_decision_v1.json",
        ):
            p = os.path.join(PHASE79D_DIR, fname)
            self.assertTrue(os.path.exists(p), f"manca {fname}")
            self.assertGreater(os.path.getsize(p), 0, f"{fname} e' vuoto")


class TestFunnelMapStatic(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(FUNNEL_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_declares_preexisting_instrumentation(self):
        self.assertIn("PREESISTENTI", self.doc["payload"]["instrumentation_source"])

    def test_execution_path_is_strategy_profiles(self):
        self.assertEqual(self.doc["payload"]["execution_path_used"], "PROFILI_PER_STRATEGIA")

    def test_deterministic_rebuild(self):
        p1 = funnel_builder.build()
        p2 = funnel_builder.build()
        self.assertEqual(canonical_sha256(p1), canonical_sha256(p2))


class TestExecutionEventsAndAccounting(unittest.TestCase):
    def setUp(self):
        self.events_doc = load_json(EVENTS_PATH)
        self.counts_doc = load_json(COUNTS_PATH)

    def test_events_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.events_doc["payload"]), self.events_doc["canonical_sha256"])

    def test_counts_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.counts_doc["payload"]), self.counts_doc["canonical_sha256"])

    def test_funnel_accounting_invariant_holds(self):
        acc = self.counts_doc["payload"]["accounting"]
        self.assertEqual(acc["total_generated"], acc["opened"] + acc["blocked"] + acc["broker_reject"])
        self.assertTrue(acc["invariant_holds"])

    def test_certificate_cross_check_matches(self):
        cc = self.counts_doc["payload"]["certificate_cross_check"]
        self.assertTrue(cc["matches_journal_recomputation"])

    def test_four_real_trades_observed(self):
        acc = self.counts_doc["payload"]["accounting"]
        self.assertEqual(acc["opened"], 4)
        self.assertEqual(acc["blocked"], 0)
        self.assertEqual(acc["total_generated"], 4)


class TestReproducibilityVsPhaseE(unittest.TestCase):
    def setUp(self):
        self.payload = load_json(DECISION_PATH)["payload"]

    def test_count_matches_phase_e(self):
        self.assertTrue(self.payload["reproducibility_check_vs_phase_e"]["count_matches_phase_e"])

    def test_timestamps_match_phase_e_exactly(self):
        self.assertTrue(self.payload["reproducibility_check_vs_phase_e"]["timestamps_match_phase_e_exactly"])

    def test_phase_e_source_file_untouched(self):
        path = os.path.join(ROOT, "results", "cost_calibration_67_rerun", "phase_e_breakoutacc_findings.json")
        # non modificato in questa fase - solo verifichiamo che esista e sia leggibile
        self.assertTrue(os.path.exists(path))
        load_json(path)


class TestSignalReconstructionPairing(unittest.TestCase):
    def setUp(self):
        self.pairing = load_json(DECISION_PATH)["payload"]["signal_reconstruction_vs_real_ea_pairing"]

    def test_pairing_arithmetic_expected_side(self):
        p = self.pairing
        self.assertEqual(p["matched"] + p["missing_in_diagnostic_run"],
                          p["expected_signal_fire_from_7_9c_readonly_reconstruction"])

    def test_pairing_arithmetic_observed_side(self):
        p = self.pairing
        self.assertEqual(p["matched"] + p["extra_in_diagnostic_run"],
                          p["observed_generated_by_actual_ea_in_diagnostic_run"])

    def test_massive_discrepancy_confirmed(self):
        # La scoperta centrale: la maggioranza dei SIGNAL_FIRE stimati dalla 7.9C
        # non ha controparte nell'EA reale - non un piccolo residuo.
        p = self.pairing
        self.assertGreater(p["missing_in_diagnostic_run"] / p["expected_signal_fire_from_7_9c_readonly_reconstruction"], 0.5)


class TestVerdictAndDecisionAllowedSets(unittest.TestCase):
    def setUp(self):
        self.payload = load_json(DECISION_PATH)["payload"]

    def test_final_verdict_in_allowed_set(self):
        self.assertIn(self.payload["final_verdict"], ALLOWED_VERDICTS)

    def test_next_decision_in_allowed_set(self):
        self.assertIn(self.payload["next_decision"], ALLOWED_NEXT_DECISIONS)

    def test_next_step_not_executed(self):
        self.assertTrue(self.payload["next_step_not_executed"])

    def test_no_pnl_terms_in_artifact(self):
        text = json.dumps(self.payload).lower()
        for term in ("expectancy", "\"pf\":", "profit_factor", "win_rate"):
            self.assertNotIn(term, text)

    def test_scope_flags_preserved(self):
        self.assertTrue(self.payload["volbrk_not_reopened"])
        self.assertTrue(self.payload["h006_not_reopened"])
        self.assertTrue(self.payload["hvcw_backlog_only"])


class TestDecisionDeterministic(unittest.TestCase):
    def test_rebuild_is_deterministic(self):
        p1 = decision_builder.build()
        p2 = decision_builder.build()
        self.assertEqual(canonical_sha256(p1), canonical_sha256(p2))


class TestIndependentVerifierPasses(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        errors = verifier.verify()
        self.assertEqual(errors, [], f"il verificatore indipendente ha trovato problemi: {errors}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
