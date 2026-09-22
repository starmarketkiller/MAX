#!/usr/bin/env python3
"""Phase 7.9E - suite di consistenza (stesso pattern delle fasi precedenti)."""
import json
import os
import sys
import unittest

PHASE79E_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79E_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
sys.path.insert(0, PHASE79E_DIR)
from canonical_utils import canonical_sha256, load_json  # noqa: E402
import build_offline_vs_live_semantics_diff as diff_builder  # noqa: E402
import build_missing_event_forensics as forensics_builder  # noqa: E402
import build_reconstruction_parity_and_decision as decision_builder  # noqa: E402
import verify_reconstruction_semantics as verifier  # noqa: E402

DIFF_PATH = os.path.join(PHASE79E_DIR, "breakout_acc_live_vs_offline_semantics_diff_v1.json")
FORENSICS_PATH = os.path.join(PHASE79E_DIR, "breakout_acc_missing_event_forensics_v1.json")
PARITY_PATH = os.path.join(PHASE79E_DIR, "breakout_acc_reconstruction_parity_v1.json")
DECISION_PATH = os.path.join(PHASE79E_DIR, "breakout_acc_reconstruction_decision_v1.json")

ALLOWED_VERDICTS = {
    "OFFLINE_RECONSTRUCTION_PARITY_CONFIRMED", "OFFLINE_RECONSTRUCTION_PARITY_PARTIAL",
    "EVALUATION_CADENCE_MISMATCH", "STATE_SEMANTICS_MISMATCH", "HTF_TIMING_MISMATCH",
    "MULTI_CAUSE_RECONSTRUCTION_FAILURE", "OFFLINE_RECONSTRUCTION_ROOT_CAUSE_UNRESOLVED",
}
ALLOWED_NEXT_DECISIONS = {"REBUILD_CANONICAL_BREAKOUT_ACC_DATASET", "BLOCK_RESEARCH_UNTIL_RECONSTRUCTION_PARITY"}


class TestDeliverablesExist(unittest.TestCase):
    def test_all_files_present(self):
        for p in (DIFF_PATH, FORENSICS_PATH, PARITY_PATH, DECISION_PATH):
            self.assertTrue(os.path.exists(p))
            self.assertGreater(os.path.getsize(p), 0)


class TestSemanticsDiff(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(DIFF_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_deterministic_rebuild(self):
        p1 = diff_builder.build()
        p2 = diff_builder.build()
        self.assertEqual(canonical_sha256(p1), canonical_sha256(p2))

    def test_cadence_ruled_out(self):
        s = self.doc["payload"]["2_timing_semantics_verified_empirically"]
        self.assertEqual(s["n_activation_fail"], 0)
        self.assertEqual(s["n_new_d1_bar_detected_after_success"], 1944)

    def test_shared_state_collapse_documented(self):
        s = self.doc["payload"]["5_htf_gate_placement_and_counts"]
        self.assertEqual(s["post_cooldown_with_cross_tf_shared_state"], 0)
        self.assertGreater(s["post_cooldown_isolated_D1_only"], 50)

    def test_no_strategy_or_live_ea_modification_flags(self):
        p = self.doc["payload"]
        self.assertTrue(p["no_strategy_modification"])
        self.assertTrue(p["no_live_ea_modification"])


class TestMissingEventForensics(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(FORENSICS_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_three_events_present(self):
        self.assertEqual(len(self.doc["payload"]["events"]), 3)

    def test_all_valid_in_isolation(self):
        for e in self.doc["payload"]["events"]:
            self.assertTrue(e["would_fire_in_isolation"])

    def test_deterministic_rebuild(self):
        p1 = forensics_builder.build()
        p2 = forensics_builder.build()
        self.assertEqual(canonical_sha256(p1), canonical_sha256(p2))


class TestParityAndDecision(unittest.TestCase):
    def setUp(self):
        self.parity = load_json(PARITY_PATH)["payload"]
        self.decision = load_json(DECISION_PATH)["payload"]

    def test_parity_not_achieved(self):
        self.assertFalse(self.parity["achieved"])

    def test_final_verdict_in_allowed_set(self):
        self.assertIn(self.decision["final_verdict"], ALLOWED_VERDICTS)

    def test_final_verdict_is_state_semantics_mismatch(self):
        self.assertEqual(self.decision["final_verdict"], "STATE_SEMANTICS_MISMATCH")

    def test_next_decision_in_allowed_set(self):
        self.assertIn(self.decision["next_decision"], ALLOWED_NEXT_DECISIONS)

    def test_next_decision_is_block_research(self):
        self.assertEqual(self.decision["next_decision"], "BLOCK_RESEARCH_UNTIL_RECONSTRUCTION_PARITY")

    def test_next_step_not_executed(self):
        self.assertTrue(self.decision["next_step_not_executed"])

    def test_live_ea_unchanged_flag(self):
        self.assertTrue(self.decision["live_ea_strategy_logic_unchanged"])

    def test_supersedes_note_present(self):
        self.assertIn("7_9c_assumption", self.decision["supersedes_note"])
        self.assertIn("7_9d_finding", self.decision["supersedes_note"])
        self.assertIn("7_9e_finding", self.decision["supersedes_note"])

    def test_no_pnl_terms(self):
        text = json.dumps(self.decision).lower()
        for term in ("expectancy", "\"pf\":", "profit_factor", "win_rate"):
            self.assertNotIn(term, text)

    def test_scope_flags_preserved(self):
        self.assertTrue(self.decision["volbrk_not_reopened"])
        self.assertTrue(self.decision["h006_not_reopened"])
        self.assertTrue(self.decision["hvcw_backlog_only"])


class TestFrozenArtifactsUntouched(unittest.TestCase):
    def test_7_9c_and_7_9d_readable_and_present(self):
        for rel in (
            "server/research_scripts/phase7/phase7_9c/breakout_acc_event_parity_matrix_v1.json",
            "server/research_scripts/phase7/phase7_9d/breakout_acc_execution_parity_decision_v1.json",
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
