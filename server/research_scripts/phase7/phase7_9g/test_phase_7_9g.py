#!/usr/bin/env python3
"""Phase 7.9G - suite di consistenza (stesso pattern delle fasi precedenti)."""
import json
import os
import sys
import unittest

PHASE79G_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79G_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
sys.path.insert(0, PHASE79G_DIR)
from canonical_utils import canonical_sha256, load_json  # noqa: E402
import build_bar_updn_structural_warning as bar_updn_builder  # noqa: E402
import build_stale_evidence_reclassification as stale_builder  # noqa: E402
import build_phase7_9g_decision as decision_builder  # noqa: E402
import verify_live_fix_and_parity as verifier  # noqa: E402

COMBINED_PATH = os.path.join(PHASE79G_DIR, "breakout_acc_live_fix_before_after_v1.json")
FIXED_IDENTITY_PATH = os.path.join(PHASE79G_DIR, "breakout_acc_fixed_identity_v1.json")
PARITY_PATH = os.path.join(PHASE79G_DIR, "breakout_acc_postfix_signal_parity_v1.json")
STALE_PATH = os.path.join(PHASE79G_DIR, "breakout_acc_stale_evidence_reclassification_v1.json")
DECISION_PATH = os.path.join(PHASE79G_DIR, "breakout_acc_phase7_9g_decision_v1.json")
BAR_UPDN_PATH = os.path.join(PHASE79G_DIR, "breakout_acc_bar_updn_structural_warning_v1.json")


class TestDeliverablesExist(unittest.TestCase):
    def test_all_files_present(self):
        for p in (COMBINED_PATH, FIXED_IDENTITY_PATH, PARITY_PATH, STALE_PATH, DECISION_PATH, BAR_UPDN_PATH):
            self.assertTrue(os.path.exists(p), p)
            self.assertGreater(os.path.getsize(p), 0, p)


class TestLiveFixBeforeAfter(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(COMBINED_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_only_strategies_file_changed(self):
        d = self.doc["payload"]["diff_summary"]
        self.assertTrue(d["NXS_Strategies.mqh_changed"])
        self.assertFalse(d["NEXUS_EA_v2.mq5_changed"])
        self.assertFalse(d["backtest.py_changed"])

    def test_compile_zero_errors(self):
        self.assertEqual(self.doc["payload"]["compile_result"]["errors"], 0)

    def test_static_verification_guard_before_all_state_touches(self):
        sv = self.doc["payload"]["static_verification"]
        self.assertTrue(sv["guard_present"])
        self.assertTrue(sv["all_state_touches_occur_after_guard"])

    def test_per_timeframe_proof_covers_all_six(self):
        per_tf = self.doc["payload"]["static_verification_per_timeframe"]
        self.assertEqual(len(per_tf), 6)
        self.assertIn("CONSENTITO", per_tf["PERIOD_D1"])
        for tf in ("PERIOD_H1", "PERIOD_M30", "PERIOD_M15", "PERIOD_H4", "PERIOD_M5"):
            self.assertIn("NON TOCCATO", per_tf[tf])

    def test_no_optimization_flags(self):
        p = self.doc["payload"]
        self.assertTrue(p["no_optimization"])
        self.assertTrue(p["no_parameter_tuning"])
        self.assertTrue(p["no_performance_driven_design_change"])
        self.assertTrue(p["bar_updn_not_touched"])


class TestBarUpdnWarning(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(BAR_UPDN_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_not_fixed(self):
        self.assertTrue(self.doc["payload"]["not_fixed_in_this_phase"])

    def test_deterministic_rebuild(self):
        p1 = bar_updn_builder.build()
        p2 = bar_updn_builder.build()
        self.assertEqual(canonical_sha256(p1), canonical_sha256(p2))


class TestPostfixSignalParity(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(PARITY_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_live_ea_count_massively_higher_than_prefix(self):
        counts = self.doc["payload"]["exact_parity_target"]["counts"]
        self.assertGreater(counts["A_live_ea"], 40)   # pre-fix era 4

    def test_same_feed_pairing_arithmetic(self):
        pairing = self.doc["payload"]["exact_parity_target"]["same_feed_parity_A_vs_B"]["pairing"]
        counts = self.doc["payload"]["exact_parity_target"]["counts"]
        self.assertEqual(pairing["matched"] + pairing["only_b"], counts["A_live_ea"])
        self.assertEqual(pairing["matched"] + pairing["only_a"], counts["B_mql5_offline"])

    def test_all_live_events_explained_by_offline_reconstruction(self):
        pairing = self.doc["payload"]["exact_parity_target"]["same_feed_parity_A_vs_B"]["pairing"]
        self.assertEqual(pairing["only_b"], 0)

    def test_diagnostic_only_flag(self):
        p = self.doc["payload"]
        self.assertTrue(p["diagnostic_only_not_serious_backtest"])
        self.assertTrue(p["no_pnl_used_for_parity"])


class TestStaleEvidenceReclassification(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(STALE_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_no_artifacts_modified(self):
        self.assertTrue(self.doc["payload"]["no_artifacts_modified"])

    def test_deterministic_rebuild(self):
        p1 = stale_builder.build()
        p2 = stale_builder.build()
        self.assertEqual(canonical_sha256(p1), canonical_sha256(p2))

    def test_phase_e_marked_historical(self):
        entries = self.doc["payload"]["reclassified_entries"]
        phase_e = next(e for e in entries if "phase_e_breakoutacc_findings" in e["artifact"])
        self.assertEqual(phase_e["reclassification"], "HISTORICAL_IMPLEMENTATION_EVIDENCE")
        self.assertEqual(phase_e["applies_to_canonical_d1"], "NOT_EVIDENCE_FOR_CANONICAL_D1")


class TestPhase79GDecision(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(DECISION_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_deterministic_rebuild(self):
        p1 = decision_builder.build()
        p2 = decision_builder.build()
        self.assertEqual(canonical_sha256(p1), canonical_sha256(p2))

    def test_next_decision_in_allowed_set(self):
        self.assertIn(self.doc["payload"]["next_decision"],
                      ("BUILD_CANONICAL_BREAKOUT_ACC_DATASET", "CONTINUE_PARITY_DEBUG"))

    def test_parity_passed_implies_build_dataset_decision(self):
        p = self.doc["payload"]
        if p["parity_passed"]:
            self.assertEqual(p["next_decision"], "BUILD_CANONICAL_BREAKOUT_ACC_DATASET")

    def test_canonical_identity_not_promoted_to_validated_evidence(self):
        p = self.doc["payload"]
        if p["parity_passed"]:
            self.assertEqual(p["canonical_identity_migration"]["BREAKOUT_ACC_INTENDED_D1_V1"]["evidence_status"],
                             "NOT_YET_VALIDATED")

    def test_next_step_not_executed(self):
        self.assertTrue(self.doc["payload"]["next_step_not_executed"])

    def test_no_pnl_terms_outside_disclaimer(self):
        payload_copy = json.loads(json.dumps(self.doc["payload"]))
        payload_copy.get("parity_decision_criteria", {}).pop("explicitly_not_used", None)
        text = json.dumps(payload_copy).lower()
        for term in ("expectancy", "\"pf\":", "profit_factor", "win_rate"):
            self.assertNotIn(term, text)

    def test_scope_flags_preserved(self):
        p = self.doc["payload"]
        self.assertTrue(p["volbrk_not_reopened"])
        self.assertTrue(p["h006_not_reopened"])
        self.assertTrue(p["hvcw_backlog_only"])


class TestFrozenArtifactsUntouched(unittest.TestCase):
    def test_7_9c_9d_9e_9f_readable_and_present(self):
        for rel in (
            "server/research_scripts/phase7/phase7_9c/breakout_acc_event_parity_matrix_v1.json",
            "server/research_scripts/phase7/phase7_9d/breakout_acc_execution_parity_decision_v1.json",
            "server/research_scripts/phase7/phase7_9e/breakout_acc_reconstruction_decision_v1.json",
            "server/research_scripts/phase7/phase7_9f/breakout_acc_identity_adjudication_v1.json",
        ):
            p = os.path.join(ROOT, rel)
            self.assertTrue(os.path.exists(p))
            load_json(p)


class TestIndependentVerifierPasses(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        errors = verifier.verify()
        self.assertEqual(errors, [], f"il verificatore indipendente ha trovato problemi: {errors}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
