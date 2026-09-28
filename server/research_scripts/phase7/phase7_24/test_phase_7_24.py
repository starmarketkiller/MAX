#!/usr/bin/env python3
"""Phase 7.24 - suite di test: determinismo, adjudication, dataset
canonico, classificazione fedelta' Python, decision card, verificatore
indipendente, nessuna violazione di perimetro."""
import os
import sys
import unittest

PHASE724_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE724_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE724_DIR)
import build_funnel_accounting as funnel_builder  # noqa: E402
import build_canonical_dataset as dataset_builder  # noqa: E402
import build_python_fidelity_classification as fidelity_builder  # noqa: E402
import build_readiness_decision_card as decision_builder  # noqa: E402
import verify_phase_7_24 as verifier  # noqa: E402

ARTIFACTS = [
    ("funnel_accounting_v1.json", funnel_builder.build),
    ("liq_sweep_canonical_dataset_v1.json", dataset_builder.build),
    ("liq_sweep_python_fidelity_classification_v1.json", fidelity_builder.build),
    ("liq_sweep_readiness_decision_card_v1.json", decision_builder.build),
]


class TestDeterminism(unittest.TestCase):
    def test_all_artifacts_deterministic(self):
        for fname, build_fn in ARTIFACTS:
            saved = load_json(os.path.join(PHASE724_DIR, fname))
            self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(build_fn()), fname)


class TestFunnelAccounting(unittest.TestCase):
    def setUp(self):
        self.payload = funnel_builder.build()

    def test_arithmetic_holds(self):
        self.assertTrue(self.payload["all_arithmetic_checks_hold"])

    def test_8_funnel_stages_present(self):
        self.assertEqual(len(self.payload["funnel_stages"]), 8)

    def test_final_counts_43_42_1(self):
        fc = self.payload["final_counts"]
        self.assertEqual(fc["opened"], 43)
        self.assertEqual(fc["closed_within_window"], 42)
        self.assertEqual(fc["still_open_at_period_end"], 1)
        self.assertEqual(fc["events_used_economically"], 42)

    def test_no_reconciliation_forced_flag(self):
        self.assertTrue(self.payload["no_reconciliation_forced"])

    def test_residual_41_vs_42_classified_and_fixed(self):
        item = self.payload["residual_adjudication"][0]
        self.assertEqual(item["classification"], "LOGGING_ACCOUNTING_GAP_ROOT_CAUSE_FOUND_AND_FIXED")
        self.assertIsNotNone(item["fix_applied"])

    def test_residual_43_vs_42_classified_expected(self):
        item = self.payload["residual_adjudication"][1]
        self.assertEqual(item["classification"], "EXPECTED_FUNNEL_DIFFERENCE")

    def test_no_residual_classified_unknown_or_data_loss(self):
        for item in self.payload["residual_adjudication"]:
            self.assertNotIn(item["classification"], ("UNKNOWN", "DATA_LOSS"))


class TestCanonicalDataset(unittest.TestCase):
    def setUp(self):
        self.payload = dataset_builder.build()

    def test_python_not_used(self):
        self.assertFalse(self.payload["python_used_to_build_this_dataset"])

    def test_42_closed_1_open_43_total(self):
        self.assertEqual(self.payload["n_events_closed_economic"], 42)
        self.assertEqual(self.payload["n_events_open_at_period_end"], 1)
        self.assertEqual(self.payload["n_events_total"], 43)

    def test_required_fields_present_per_event(self):
        required = {"event_id", "run_id", "strategy_identity", "lifecycle", "direction",
                   "entry", "exit", "actual_pnl", "provenance_ref"}
        for e in self.payload["events"]:
            self.assertTrue(required.issubset(e.keys()), e.get("event_id"))

    def test_event_ids_unique(self):
        ids = [e["event_id"] for e in self.payload["events"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_closed_events_have_exit_and_pnl(self):
        for e in self.payload["events"]:
            if e["lifecycle"] == "CLOSED":
                self.assertIsNotNone(e["exit"])
                self.assertIsInstance(e["actual_pnl"], float)

    def test_open_at_end_event_has_no_pnl(self):
        open_events = [e for e in self.payload["events"] if e["lifecycle"] == "OPEN_AT_PERIOD_END"]
        self.assertEqual(len(open_events), 1)
        self.assertIsNone(open_events[0]["actual_pnl"])


class TestPythonFidelityClassification(unittest.TestCase):
    def setUp(self):
        self.payload = fidelity_builder.build()

    def test_exit_semantics_documented_separately(self):
        self.assertIn("mql5", self.payload["canonical_exit_definition"])
        self.assertIn("python_historical_proxy", self.payload["canonical_exit_definition"])

    def test_no_python_code_modified_flag(self):
        self.assertTrue(self.payload["no_python_code_modified_to_force_pnl_match"])

    def test_mt5_ground_truth_rule_stated(self):
        self.assertIn("ground truth", self.payload["rule_applied"])


class TestReadinessDecisionCard(unittest.TestCase):
    def setUp(self):
        self.payload = decision_builder.build()

    def test_decision_allowed(self):
        allowed = {"READY_FOR_EDGE_VALIDATION", "READY_WITH_DOCUMENTED_LIMITATION",
                  "NOT_READY_FOR_EDGE_VALIDATION"}
        self.assertIn(self.payload["decision"], allowed)

    def test_no_optimization_flag(self):
        self.assertTrue(self.payload["no_optimization_performed"])

    def test_no_further_economic_analysis_flag(self):
        self.assertTrue(self.payload["no_further_economic_analysis_this_phase"])


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
