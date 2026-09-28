#!/usr/bin/env python3
"""Phase 7.23 - suite di test (Fase A run isolation gia' coperta da
test_run_isolation.py - qui i test di Fase B + integrazione)."""
import os
import sys
import unittest

PHASE723_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE723_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE723_DIR)
import build_run_isolation_spec as spec_builder  # noqa: E402
import build_liq_sweep_identity_map as identity_builder  # noqa: E402
import build_liq_sweep_historical_evidence_map as historical_builder  # noqa: E402
import build_liq_sweep_semantic_parity_matrix as parity_builder  # noqa: E402
import build_liq_sweep_diagnostic_findings as diagnostic_builder  # noqa: E402
import build_liq_sweep_diagnostic_run as run_builder  # noqa: E402
import build_liq_sweep_decision_card as decision_builder  # noqa: E402
import verify_phase_7_23 as verifier  # noqa: E402

ARTIFACTS = [
    ("run_isolation_spec_v1.json", spec_builder.build),
    ("liq_sweep_identity_map_v1.json", identity_builder.build),
    ("liq_sweep_historical_evidence_map_v1.json", historical_builder.build),
    ("liq_sweep_semantic_parity_matrix_v1.json", parity_builder.build),
    ("liq_sweep_diagnostic_findings_v1.json", diagnostic_builder.build),
    ("liq_sweep_diagnostic_run_v1.json", run_builder.build),
    ("liq_sweep_decision_card_v1.json", decision_builder.build),
]


class TestDeterminism(unittest.TestCase):
    def test_all_artifacts_deterministic(self):
        for fname, build_fn in ARTIFACTS:
            saved = load_json(os.path.join(PHASE723_DIR, fname))
            self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(build_fn()), fname)


class TestRunIsolationSpec(unittest.TestCase):
    def setUp(self):
        self.payload = spec_builder.build()

    def test_no_strategy_logic_modified(self):
        self.assertTrue(self.payload["no_strategy_logic_modified"])

    def test_all_requirements_covered(self):
        req = self.payload["requirements_covered"]
        for k in ("run_id_univoco", "directory_dedicata", "timestamp_start_end",
                 "strategy_identity", "code_build_sha", "config_hash", "periodo_testato",
                 "file_trade_dedicato", "certificato_dedicato", "provenance_completa"):
            self.assertIn(k, req)

    def test_historical_artifacts_never_deleted_documented(self):
        self.assertIn("historical_artifacts_never_deleted", self.payload)


class TestLiqSweepIdentityMap(unittest.TestCase):
    def setUp(self):
        self.payload = identity_builder.build()

    def test_stateless_confirmed(self):
        self.assertIn("STATELESS", self.payload["mql5_implementation"]["persistent_state"])

    def test_htf_mismatch_investigated_and_cleared(self):
        htf_finding = next(m for m in self.payload["mismatches_verified_in_this_phase"]
                          if m["area"].startswith("HTF"))
        self.assertTrue(htf_finding["severity"].startswith("NESSUNA"))
        self.assertIn("VERIFICATO E SMENTITO", htf_finding["finding"])

    def test_exit_mismatch_confirmed(self):
        exit_finding = next(m for m in self.payload["mismatches_verified_in_this_phase"]
                           if m["area"].startswith("EXIT"))
        self.assertTrue(exit_finding["severity"].startswith("ALTA"))
        self.assertIn("CONFERMATO", exit_finding["finding"])

    def test_no_strategy_modification_flag(self):
        self.assertTrue(self.payload["no_strategy_logic_modified_in_this_phase"])


class TestLiqSweepHistoricalEvidenceMap(unittest.TestCase):
    def setUp(self):
        self.payload = historical_builder.build()

    def test_all_items_classified(self):
        allowed = {"REUSABLE", "PARTIALLY_REUSABLE", "CONTAMINATED", "CANNOT_DETERMINE"}
        for item in self.payload["items"]:
            self.assertIn(item["classification"], allowed)

    def test_pf104_not_used_as_edge_proof(self):
        sweep37_item = next(i for i in self.payload["items"] if "sweep37" in i["artifact"])
        self.assertEqual(sweep37_item["classification"], "CONTAMINATED")

    def test_no_reusable_evidence_flag(self):
        self.assertTrue(self.payload["no_reusable_evidence_found_for_current_canonical_identity"])

    def test_dates_are_git_verified_not_assumed(self):
        dates = self.payload["key_dates_verified_via_git"]
        self.assertEqual(len(dates), 5)


class TestLiqSweepSemanticParityMatrix(unittest.TestCase):
    def setUp(self):
        self.payload = parity_builder.build()

    def test_5_funnel_levels_present(self):
        self.assertEqual(len(self.payload["funnel_levels_compared"]), 5)

    def test_exit_level_structurally_different(self):
        exit_level = self.payload["funnel_levels_compared"]["5_exit_sl_tp"]
        self.assertEqual(exit_level["parity_status"], "STRUCTURALLY_DIFFERENT_NOT_COMPARABLE")

    def test_python_not_event_level_faithful(self):
        self.assertTrue(self.payload["not_event_level_faithful_overall"])

    def test_mt5_ground_truth_declared(self):
        self.assertIn("mt5_remains_ground_truth", self.payload)


class TestLiqSweepDiagnosticFindings(unittest.TestCase):
    def setUp(self):
        self.payload = diagnostic_builder.build()

    def test_deterministic_case_present(self):
        self.assertIn("case_1_htf_filter_sequencing", self.payload["1_deterministic_cases"])

    def test_no_automatic_multi_year_run(self):
        self.assertTrue(self.payload["minimum_mt5_run_needed"]["no_automatic_multi_year_run"])

    def test_python_classification_partial(self):
        self.assertEqual(self.payload["5_python_classification"]["classification"],
                         "PARTIAL_STRUCTURAL_MODEL")


class TestLiqSweepDiagnosticRun(unittest.TestCase):
    def test_run_status_known(self):
        payload = run_builder.build()
        self.assertIn(payload.get("status"),
                      {"RUN_NOT_YET_LAUNCHED", "RUN_NOT_YET_COLLECTED", "COLLECTED"})

    def test_no_edge_validation_claim_if_collected(self):
        payload = run_builder.build()
        if payload.get("status") == "COLLECTED":
            self.assertIn("no_edge_validation_performed", payload)


class TestLiqSweepDecisionCard(unittest.TestCase):
    def test_decision_allowed(self):
        payload = decision_builder.build()
        allowed = {"INTEGRITY_VALIDATED_READY_FOR_EDGE_VALIDATION", "INTEGRITY_PARTIALLY_VALIDATED",
                  "IMPLEMENTATION_DEFECT_CONFIRMED", "INSUFFICIENT_EVIDENCE"}
        self.assertIn(payload["decision"], allowed)

    def test_not_ready_for_edge_validation_flag(self):
        payload = decision_builder.build()
        self.assertTrue(payload["not_ready_for_edge_validation_yet"])

    def test_no_optimization_flag(self):
        payload = decision_builder.build()
        self.assertTrue(payload["no_optimization_no_edge_tuning_no_deploy"])


class TestNoScopeViolations(unittest.TestCase):
    def test_no_mql5_product_platform_changes(self):
        import subprocess
        result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                                "contracts/"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        self.assertEqual(verifier.verify(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
