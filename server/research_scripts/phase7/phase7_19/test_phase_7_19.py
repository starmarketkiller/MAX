#!/usr/bin/env python3
"""Phase 7.19 - suite di test per EVENT_AUDIT_PACKET_V1 + VISUAL_AUDIT_
PROTOCOL_V1."""
import json
import os
import subprocess
import sys
import unittest

PHASE719_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE719_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE719_DIR)
import build_visual_audit_protocol as vap_builder  # noqa: E402
import build_fidelity_framework as fid_builder  # noqa: E402
import build_sampling_protocol as samp_builder  # noqa: E402
import build_anti_leakage_specification as leak_builder  # noqa: E402
import build_source_of_truth_hierarchy as sot_builder  # noqa: E402
import build_anti_bias_rules as bias_builder  # noqa: E402
import build_example_packets as ex_builder  # noqa: E402
import build_gap_analysis as gap_builder  # noqa: E402
import build_implementation_roadmap as road_builder  # noqa: E402
import build_decision as dec_builder  # noqa: E402
import verify_phase_7_19 as verifier  # noqa: E402

ARTIFACTS = [
    ("visual_audit_protocol_v1.json", vap_builder.build),
    ("fidelity_framework_v1.json", fid_builder.build),
    ("sampling_protocol_v1.json", samp_builder.build),
    ("anti_leakage_specification_v1.json", leak_builder.build),
    ("source_of_truth_hierarchy_v1.json", sot_builder.build),
    ("anti_bias_rules_v1.json", bias_builder.build),
    ("example_packets_v1.json", ex_builder.build),
    ("gap_analysis_v1.json", gap_builder.build),
    ("implementation_roadmap_v1.json", road_builder.build),
    ("audit_standard_decision_v1.json", dec_builder.build),
]

SCHEMA_FILES = ["event_audit_packet_v1.schema.json", "runtime_identity_manifest_v1.schema.json",
                "visual_audit_result_v1.schema.json", "matched_non_event_v1.schema.json"]


class TestDeterminism(unittest.TestCase):
    def test_all_artifacts_deterministic(self):
        for fname, build_fn in ARTIFACTS:
            saved = load_json(os.path.join(PHASE719_DIR, fname))
            fresh = build_fn()
            self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(fresh), fname)


class TestSchemasWellFormed(unittest.TestCase):
    def test_all_4_schemas_valid_json(self):
        for fname in SCHEMA_FILES:
            path = os.path.join(PHASE719_DIR, "schemas", fname)
            with open(path, encoding="utf-8") as f:
                schema = json.load(f)
            self.assertEqual(schema.get("$schema"), "http://json-schema.org/draft-07/schema#", fname)
            self.assertIn("required", schema, fname)
            self.assertIn("properties", schema, fname)

    def test_event_packet_schema_has_absence_reason_definition(self):
        path = os.path.join(PHASE719_DIR, "schemas", "event_audit_packet_v1.schema.json")
        with open(path, encoding="utf-8") as f:
            schema = json.load(f)
        reasons = schema["definitions"]["absence_reason"]["enum"]
        self.assertEqual(set(reasons), {"NOT_AVAILABLE", "NOT_APPLICABLE", "NOT_RECORDED", "UNKNOWN", "CENSORED"})

    def test_matched_non_event_forbids_outcome_in_selection(self):
        path = os.path.join(PHASE719_DIR, "schemas", "matched_non_event_v1.schema.json")
        with open(path, encoding="utf-8") as f:
            schema = json.load(f)
        self.assertEqual(schema["properties"]["outcome_used_in_selection"]["const"], False)


class TestVisualAuditProtocol(unittest.TestCase):
    def setUp(self):
        self.payload = vap_builder.build()

    def test_three_stages_present(self):
        for stage in ("stage_a_blind_review", "stage_b_future_reveal", "stage_c_outcome_review"):
            self.assertIn(stage, self.payload["stages"])

    def test_forbidden_question_declared(self):
        self.assertIn("Vincera'?", self.payload["stages"]["stage_a_blind_review"]["forbidden_questions"])

    def test_stage_b_requires_stage_a_locked(self):
        self.assertIn("precondition", self.payload["stages"]["stage_b_future_reveal"])

    def test_decision_outcome_matrix_has_4_categories(self):
        cats = self.payload["stages"]["stage_c_outcome_review"]["decision_outcome_matrix"]["categories"]
        self.assertEqual(len(cats), 4)


class TestFidelityFramework(unittest.TestCase):
    def setUp(self):
        self.payload = fid_builder.build()

    def test_four_tiers_present(self):
        self.assertEqual(set(self.payload["tiers"].keys()), {"A", "B", "C", "D"})

    def test_tier_d_has_explicit_limitation(self):
        self.assertIn("explicit_limitation", self.payload["tiers"]["D"])

    def test_fidelity_never_a_vote_on_strategy(self):
        self.assertIn("non la strategia", self.payload["principle"])


class TestExamplePackets(unittest.TestCase):
    def setUp(self):
        self.payload = ex_builder.build()

    def test_three_packets_present(self):
        self.assertEqual(set(self.payload["packets"].keys()), {"BREAKOUT_ACC", "ORDER_BLOCK", "SH_BMS_RTO"})

    def test_tsi_not_used(self):
        self.assertNotIn("TSI", self.payload["packets"])
        self.assertIn("why_not_tsi", self.payload["packets"]["SH_BMS_RTO"])

    def test_no_fabricated_data_flag(self):
        self.assertTrue(self.payload["no_fabricated_data"])

    def test_packets_have_different_state_kinds(self):
        kinds = {name: p["strategy_state"]["state_before"]["strategy_state_kind"]
                for name, p in self.payload["packets"].items()}
        self.assertEqual(kinds["BREAKOUT_ACC"], "COOLDOWN_TIMER")
        self.assertEqual(kinds["ORDER_BLOCK"], "DISCRETE_ZONE")
        self.assertEqual(kinds["SH_BMS_RTO"], "STATE_MACHINE")

    def test_breakout_acc_uses_real_fill_data(self):
        pkt = self.payload["packets"]["BREAKOUT_ACC"]
        self.assertFalse(pkt["prices"]["actual_fill_price"]["is_proxy"])
        self.assertEqual(pkt["prices"]["actual_fill_price"]["value"], 1333.51)

    def test_fidelity_tiers_span_the_range(self):
        tiers = {p["fidelity"]["tier"] for p in self.payload["packets"].values()}
        self.assertIn("D", tiers)  # almeno un esempio a bassa fedelta', dichiarato

    def test_absent_fields_never_bare_null(self):
        def walk(obj):
            if isinstance(obj, dict):
                if obj.get("status") == "ABSENT":
                    self.assertIn("reason", obj)
                    self.assertIn(obj["reason"], {"NOT_AVAILABLE", "NOT_APPLICABLE",
                                                  "NOT_RECORDED", "UNKNOWN", "CENSORED"})
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)
        for pkt in self.payload["packets"].values():
            walk(pkt)


class TestGapAnalysis(unittest.TestCase):
    def setUp(self):
        self.payload = gap_builder.build()

    def test_four_categories_present(self):
        for cat in ("ALREADY_AVAILABLE", "DERIVABLE", "MISSING_BUT_NEEDED", "OPTIONAL"):
            self.assertIn(cat, self.payload)

    def test_runtime_identity_flagged_missing(self):
        found = any("RUNTIME_IDENTITY_MANIFEST" in str(b) for b in self.payload["MISSING_BUT_NEEDED"])
        self.assertTrue(found)


class TestImplementationRoadmap(unittest.TestCase):
    def setUp(self):
        self.payload = road_builder.build()

    def test_five_levels_present(self):
        self.assertEqual(set(self.payload["levels"].keys()),
                         {"1_MQL5", "2_python_backend", "3_product_platform", "4_jarvis", "5_research_engine"})

    def test_every_level_has_dependencies_declared(self):
        for level in self.payload["levels"].values():
            self.assertIn("depends_on", level)
            self.assertIn("blocked_by", level)

    def test_no_implementation_performed(self):
        self.assertIn("Nessuno", self.payload["explicit_non_goal_this_phase"])


class TestDecision(unittest.TestCase):
    def setUp(self):
        self.payload = dec_builder.build()

    def test_decision_allowed(self):
        self.assertIn(self.payload["decision"], {"AUDIT_STANDARD_READY", "AUDIT_STANDARD_NEEDS_REVISION"})

    def test_no_edge_claim(self):
        self.assertTrue(self.payload["no_edge_claim_made"])

    def test_scope_declared(self):
        self.assertIn("NON giudica se una qualunque strategia", self.payload["scope_of_this_decision"])


class TestNoScopeViolations(unittest.TestCase):
    def test_no_unexpected_mql5_product_platform_changes(self):
        result = subprocess.run(["git", "status", "--porcelain", "--", "Product-Platform/", "contracts/"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")

    def test_tsi_phase_7_17_untouched(self):
        result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--",
                                "server/research_scripts/phase7/phase7_17"], cwd=ROOT)
        self.assertEqual(result.returncode, 0)


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        self.assertEqual(verifier.verify(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
