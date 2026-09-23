#!/usr/bin/env python3
"""Phase 7.9F - suite di consistenza (stesso pattern delle fasi precedenti)."""
import json
import os
import sys
import unittest

PHASE79F_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79F_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
sys.path.insert(0, PHASE79F_DIR)
from canonical_utils import canonical_sha256, load_json  # noqa: E402
import build_strategy_identity_authority as authority_builder  # noqa: E402
import build_implemented_vs_intended_semantics as semantics_builder  # noqa: E402
import build_identity_adjudication as adjudication_builder  # noqa: E402
import verify_identity_adjudication as verifier  # noqa: E402

AUTHORITY_PATH = os.path.join(PHASE79F_DIR, "breakout_acc_strategy_identity_authority_v1.json")
SEMANTICS_PATH = os.path.join(PHASE79F_DIR, "breakout_acc_implemented_vs_intended_semantics_v1.json")
ROUTER_PATH = os.path.join(PHASE79F_DIR, "breakout_acc_exact_router_replication_v1.json")
ADJUDICATION_PATH = os.path.join(PHASE79F_DIR, "breakout_acc_identity_adjudication_v1.json")

ALLOWED_VERDICTS = {
    "IMPLEMENTATION_DEFECT_CONFIRMED", "IMPLEMENTATION_BEHAVIOR_INTENDED",
    "SPEC_AMBIGUOUS_IMPLEMENTATION_DIVERGENCE", "ROOT_CAUSE_CONFIRMED_BUT_INTENT_UNRESOLVED",
}


class TestDeliverablesExist(unittest.TestCase):
    def test_all_files_present(self):
        for p in (AUTHORITY_PATH, SEMANTICS_PATH, ROUTER_PATH, ADJUDICATION_PATH):
            self.assertTrue(os.path.exists(p))
            self.assertGreater(os.path.getsize(p), 0)


class TestStrategyIdentityAuthority(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(AUTHORITY_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_deterministic_rebuild(self):
        p1 = authority_builder.build()
        p2 = authority_builder.build()
        self.assertEqual(canonical_sha256(p1), canonical_sha256(p2))

    def test_at_least_five_sources(self):
        self.assertGreaterEqual(len(self.doc["payload"]["sources_chronological"]), 5)

    def test_multitf_predates_cooldown_fix(self):
        gap = self.doc["payload"]["multitf_architecture_predates_cooldown_fix"]["gap_days_approx"]
        self.assertGreater(gap, 30)

    def test_bar_updn_analogy_present(self):
        self.assertTrue(self.doc["payload"]["bar_updn_structural_analogy"]["same_structural_pattern"])


class TestImplementedVsIntendedSemantics(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(SEMANTICS_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_deterministic_rebuild(self):
        p1 = semantics_builder.build()
        p2 = semantics_builder.build()
        self.assertEqual(canonical_sha256(p1), canonical_sha256(p2))

    def test_cooldown_semantics_discrepancy_confirmed(self):
        s = self.doc["payload"]["2_cooldown_semantics_answer"]
        self.assertIn("DISCREPANZA CONFERMATA", s["verdict"])

    def test_causal_example_present(self):
        ex = self.doc["payload"]["3_side_effect_before_filter_architecture"]["minimal_causal_example_from_real_run"]
        self.assertIsNotNone(ex)
        self.assertIsNotNone(ex["triggering_non_d1_fire"])

    def test_exact_pass_order_has_six_distinct_tfs(self):
        passes = self.doc["payload"]["4_exact_router_replication"]["exact_pass_order_verified"]
        self.assertEqual(len(passes), 6)
        tfs = {p["tf"] for p in passes}
        self.assertEqual(len(tfs), 6)

    def test_exact_parity_target_not_achieved_and_declared(self):
        r = self.doc["payload"]["4_exact_router_replication"]
        self.assertFalse(r["target_achieved"])

    def test_two_identities_neither_validated(self):
        ti = self.doc["payload"]["5_two_identities"]
        self.assertFalse(ti["BREAKOUT_ACC_IMPLEMENTED_V1"]["validated"])
        self.assertFalse(ti["BREAKOUT_ACC_INTENDED_D1_V1"]["validated"])

    def test_no_modification_flags(self):
        p = self.doc["payload"]
        self.assertTrue(p["no_live_ea_modification"])
        self.assertTrue(p["no_python_modification"])
        self.assertTrue(p["no_performance_backtest"])
        self.assertTrue(p["no_optimization"])


class TestIdentityAdjudication(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(ADJUDICATION_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_deterministic_rebuild(self):
        p1 = adjudication_builder.build()
        p2 = adjudication_builder.build()
        self.assertEqual(canonical_sha256(p1), canonical_sha256(p2))

    def test_verdict_in_allowed_set(self):
        self.assertIn(self.doc["payload"]["final_verdict"], ALLOWED_VERDICTS)

    def test_verdict_is_implementation_defect_confirmed(self):
        self.assertEqual(self.doc["payload"]["final_verdict"], "IMPLEMENTATION_DEFECT_CONFIRMED")

    def test_next_decision_matches_verdict_mapping(self):
        self.assertEqual(self.doc["payload"]["next_decision"], "FIX_LIVE_IMPLEMENTATION_THEN_REESTABLISH_PARITY")

    def test_next_step_not_executed(self):
        self.assertTrue(self.doc["payload"]["next_step_not_executed"])

    def test_no_python_bug_replication_performed(self):
        self.assertTrue(self.doc["payload"]["no_python_bug_replication_performed"])

    def test_no_live_ea_modification(self):
        self.assertTrue(self.doc["payload"]["no_live_ea_modification"])

    def test_historical_chronology_has_four_phases(self):
        chron = self.doc["payload"]["historical_chronology_preserved"]
        for key in ("7_9c", "7_9d", "7_9e", "7_9f"):
            self.assertIn(key, chron)

    def test_no_pnl_terms(self):
        text = json.dumps(self.doc["payload"]).lower()
        for term in ("expectancy", "\"pf\":", "profit_factor", "win_rate"):
            self.assertNotIn(term, text)

    def test_scope_flags_preserved(self):
        p = self.doc["payload"]
        self.assertTrue(p["volbrk_not_reopened"])
        self.assertTrue(p["h006_not_reopened"])
        self.assertTrue(p["hvcw_backlog_only"])


class TestFrozenArtifactsUntouched(unittest.TestCase):
    def test_7_9c_9d_9e_readable_and_present(self):
        for rel in (
            "server/research_scripts/phase7/phase7_9c/breakout_acc_event_parity_matrix_v1.json",
            "server/research_scripts/phase7/phase7_9d/breakout_acc_execution_parity_decision_v1.json",
            "server/research_scripts/phase7/phase7_9e/breakout_acc_reconstruction_decision_v1.json",
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
