#!/usr/bin/env python3
"""Phase 7.10 - suite di consistenza (stesso pattern delle fasi precedenti)."""
import json
import os
import sys
import unittest

PHASE710_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE710_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
sys.path.insert(0, PHASE710_DIR)
from canonical_utils import canonical_sha256, load_json  # noqa: E402
import build_7_9g_label_correction_audit as label_builder  # noqa: E402
import build_cross_tf_contamination_failure_memory as memory_builder  # noqa: E402
import build_stateful_strategy_static_audit as audit_builder  # noqa: E402
import build_final_synthesis_report as report_builder  # noqa: E402
import verify_phase_7_10 as verifier  # noqa: E402

LABEL_PATH = os.path.join(PHASE710_DIR, "breakout_acc_7_9g_label_correction_v1.json")
MEMORY_PATH = os.path.join(PHASE710_DIR, "cross_timeframe_state_contamination_failure_memory_v1.json")
AUDIT_PATH = os.path.join(PHASE710_DIR, "stateful_strategy_static_audit_v1.json")
SCHEMA_PATH = os.path.join(PHASE710_DIR, "retroactive_strategy_integrity_audit_schema_v1.json")
REPORT_PATH = os.path.join(PHASE710_DIR, "phase_7_10_final_synthesis_report_v1.json")


class TestDeliverablesExist(unittest.TestCase):
    def test_all_files_present(self):
        for p in (LABEL_PATH, MEMORY_PATH, AUDIT_PATH, SCHEMA_PATH, REPORT_PATH):
            self.assertTrue(os.path.exists(p), p)
            self.assertGreater(os.path.getsize(p), 0, p)


class TestLabelCorrection(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(LABEL_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_deterministic_rebuild(self):
        p1 = label_builder.build()
        p2 = label_builder.build()
        self.assertEqual(canonical_sha256(p1), canonical_sha256(p2))

    def test_inversion_confirmed(self):
        v = self.doc["payload"]["verification"]
        self.assertEqual(v["root_cause_found_in_code"]["inversion_confirmed"], "SI - per la sezione "
                         "same_feed_parity_A_vs_B, il primo argomento passato era stream_B (offline), "
                         "il secondo stream_A (live) - quindi il campo restituito 'only_a' conteneva in "
                         "realta' il residuo di B (offline) e 'only_b' il residuo di A (live). Lo stesso "
                         "pattern di inversione si applicava identicamente alle altre due sezioni "
                         "(A_vs_C, B_vs_C).")

    def test_substance_unchanged(self):
        su = self.doc["payload"]["verification"]["substance_unchanged"]
        self.assertTrue(su["counts_top_level_unchanged"])
        self.assertTrue(su["verdict_unchanged"])
        self.assertTrue(su["residual_count_before"])
        self.assertTrue(su["residual_count_after"])


class TestFailureMemory(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(MEMORY_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_deterministic_rebuild(self):
        p1 = memory_builder.build()
        p2 = memory_builder.build()
        self.assertEqual(canonical_sha256(p1), canonical_sha256(p2))

    def test_pattern_id(self):
        self.assertEqual(self.doc["payload"]["pattern_id"], "CROSS_TIMEFRAME_STATE_CONTAMINATION")

    def test_severity_classes_present(self):
        sc = self.doc["payload"]["severity_classes_identified"]
        self.assertIn("COOLDOWN_STATE_CONTAMINATION", sc)
        self.assertIn("RECURSIVE_VALUE_STATE_CONTAMINATION", sc)
        self.assertIn("STATE_MACHINE_CONTAMINATION", sc)


class TestStatefulStrategyAudit(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(AUDIT_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_deterministic_rebuild(self):
        p1 = audit_builder.build()
        p2 = audit_builder.build()
        self.assertEqual(canonical_sha256(p1), canonical_sha256(p2))

    def test_no_corrections_applied(self):
        self.assertTrue(self.doc["payload"]["no_corrections_applied"])

    def test_at_least_15_candidates_audited(self):
        self.assertGreaterEqual(len(self.doc["payload"]["candidates"]), 15)

    def test_bar_updn_defect_confirmed(self):
        bar_updn = next(c for c in self.doc["payload"]["candidates"] if c["strategy"] == "BAR_UPDN")
        self.assertEqual(bar_updn["classification"], "DEFECT_CONFIRMED")
        self.assertEqual(bar_updn["status"], "NOT_FIXED_CONFIRMED_STRUCTURALLY")

    def test_breakout_acc_marked_fixed(self):
        ba = next(c for c in self.doc["payload"]["candidates"] if c["strategy"] == "BREAKOUT_ACC")
        self.assertEqual(ba["status"], "FIXED_IN_7_9G")

    def test_all_classifications_valid(self):
        allowed = {"SAFE", "SUSPECT", "DEFECT_CONFIRMED", "NOT_ENOUGH_EVIDENCE"}
        for c in self.doc["payload"]["candidates"]:
            self.assertIn(c["classification"], allowed)

    def test_safe_candidates_have_verified_evidence(self):
        for c in self.doc["payload"]["candidates"]:
            if c["classification"] == "SAFE":
                self.assertIn("HARDCODED", c["tf_source_in_function"])


class TestSchemaAndCaseStudy(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(SCHEMA_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_thirteen_pipeline_stages(self):
        self.assertEqual(len(self.doc["payload"]["schema"]["pipeline_stages_ordered"]), 13)

    def test_five_stage_status_values(self):
        self.assertEqual(len(self.doc["payload"]["schema"]["stage_status_values"]), 5)

    def test_seven_evidence_integrity_classes(self):
        self.assertEqual(len(self.doc["payload"]["schema"]["evidence_integrity_final_classification"]["values"]), 7)

    def test_four_distortion_directions(self):
        self.assertEqual(len(self.doc["payload"]["schema"]["distortion_direction"]["values"]), 4)

    def test_breakout_acc_case_study_complete(self):
        cs = self.doc["payload"]["breakout_acc_case_study"]
        self.assertEqual(cs["case_study_status"], "FIRST_COMPLETE_CASE_STUDY")
        stages = self.doc["payload"]["schema"]["pipeline_stages_ordered"]
        for stage in stages:
            self.assertIn(stage, cs["stages"])

    def test_breakout_acc_evidence_integrity_final(self):
        cs = self.doc["payload"]["breakout_acc_case_study"]
        self.assertEqual(cs["evidence_integrity_final"], "CONTAMINATED_EVIDENCE")
        self.assertEqual(cs["distortion_direction"], "FALSE_NEGATIVE_RISK")


class TestFinalSynthesisReport(unittest.TestCase):
    def setUp(self):
        self.doc = load_json(REPORT_PATH)

    def test_hash_matches_payload(self):
        self.assertEqual(canonical_sha256(self.doc["payload"]), self.doc["canonical_sha256"])

    def test_deterministic_rebuild(self):
        p1 = report_builder.build()
        p2 = report_builder.build()
        self.assertEqual(canonical_sha256(p1), canonical_sha256(p2))

    def test_all_six_questions_answered(self):
        p = self.doc["payload"]
        for key in ("q1_only_a_only_b_inversion", "q2_general_risk_class", "q3_other_exposed_strategies",
                    "q4_bar_updn_status", "q5_canonical_audit_schema", "q6_next_single_task"):
            self.assertIn(key, p)
            self.assertIn("answer", p[key])
            self.assertGreater(len(p[key]["answer"]), 10)

    def test_no_economic_dataset_built_flag(self):
        p = self.doc["payload"]
        self.assertTrue(p["no_economic_dataset_built"])
        self.assertTrue(p["no_optimization"])
        self.assertTrue(p["no_edge_seeking"])
        self.assertTrue(p["no_new_serious_backtest"])

    def test_historical_chronology_preserved(self):
        chron = self.doc["payload"]["historical_chronology_preserved"]
        for key in ("7_9c", "7_9d", "7_9e", "7_9f", "7_9g", "7_10"):
            self.assertIn(key, chron)
        self.assertTrue(chron["no_artifacts_deleted"])

    def test_scope_flags_preserved(self):
        p = self.doc["payload"]
        self.assertTrue(p["volbrk_not_reopened"])
        self.assertTrue(p["h006_not_reopened"])
        self.assertTrue(p["hvcw_backlog_only"])

    def test_no_pnl_terms(self):
        text = json.dumps(self.doc["payload"]).lower()
        for term in ("expectancy", "\"pf\":", "profit_factor", "win_rate"):
            self.assertNotIn(term, text)


class TestIndependentVerifierPasses(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        errors = verifier.verify()
        self.assertEqual(errors, [], f"il verificatore indipendente ha trovato problemi: {errors}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
