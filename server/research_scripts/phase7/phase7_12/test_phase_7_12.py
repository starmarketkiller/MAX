#!/usr/bin/env python3
"""Phase 7.12 - suite di test di consistenza per la matrice di
copertura, i gap, la coda delle priorita' e il protocollo diagnostico.
"""
import os
import subprocess
import sys
import unittest

PHASE712_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE712_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE712_DIR)
import build_coverage_gaps_and_candidates as gaps_builder  # noqa: E402
import build_coverage_matrix as matrix_builder  # noqa: E402
import build_diagnostic_protocol_order_block as protocol_builder  # noqa: E402
import build_priority_queue as queue_builder  # noqa: E402
import verify_phase_7_12 as verifier  # noqa: E402


class TestDeterminism(unittest.TestCase):
    def _check(self, fname, build_fn):
        saved = load_json(os.path.join(PHASE712_DIR, fname))
        fresh = build_fn()
        self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(fresh))

    def test_coverage_matrix_deterministic(self):
        self._check("strategy_coverage_matrix_v1.json", matrix_builder.build)

    def test_gaps_deterministic(self):
        self._check("coverage_gaps_and_new_candidates_v1.json", gaps_builder.build)

    def test_priority_queue_deterministic(self):
        self._check("strategy_priority_queue_v1.json", queue_builder.build)

    def test_protocol_deterministic(self):
        self._check("diagnostic_protocol_order_block_v1.json", protocol_builder.build)


class TestCoverageMatrix(unittest.TestCase):
    def setUp(self):
        self.payload = matrix_builder.build()

    def test_83_identities(self):
        self.assertEqual(self.payload["total_identities"], 83)
        self.assertEqual(len(self.payload["matrix"]), 83)

    def test_no_modification_flags(self):
        self.assertTrue(self.payload["no_modification_to_frozen_7_10_7_11"])
        self.assertTrue(self.payload["no_ea_registry_or_strategy_correction_this_phase"])

    def test_not_audited_does_not_imply_safe(self):
        for row in self.payload["matrix"]:
            if row["classification_phase_7_10"] == "NOT_AUDITED_IN_PHASE_7_10":
                self.assertTrue(row["not_audited_does_not_mean_safe"])

    def test_fvg_mit_window_correction_applied(self):
        row = next(r for r in self.payload["matrix"]
                  if r["canonical_strategy_id"] == "FVG_MIT_WINDOW")
        self.assertFalse(row["stateful_per_census_7_11"])
        self.assertTrue(row["stateful_verified_7_12"])
        self.assertTrue(row["stateful_correction_applied"])

    def test_ob_mit_correction_applied(self):
        row = next(r for r in self.payload["matrix"]
                  if r["canonical_strategy_id"] == "OB_MIT")
        self.assertFalse(row["stateful_per_census_7_11"])
        self.assertTrue(row["stateful_verified_7_12"])

    def test_safe_scoped_caveat_present_for_safe_rows(self):
        found_safe = False
        for row in self.payload["matrix"]:
            if row["classification_phase_7_10"] == "SAFE":
                found_safe = True
                self.assertIsNotNone(row["safe_is_pattern_scoped_not_overall"])
        self.assertTrue(found_safe)

    def test_identity_kind_distinguishes_alias_variant_canonical(self):
        kinds = {r["identity_kind"] for r in self.payload["matrix"]}
        self.assertTrue(kinds.issubset({"ALIAS", "VARIANT", "CANONICAL_IDENTITY"}))


class TestCoverageGaps(unittest.TestCase):
    def setUp(self):
        self.payload = gaps_builder.build()

    def test_no_defect_confirmed_without_evidence_flag(self):
        self.assertTrue(self.payload["no_defect_confirmed_without_direct_evidence"])

    def test_fvg_mit_window_is_suspect_not_confirmed(self):
        f = next(x for x in self.payload["findings"] if x["candidate"] == "FVG_MIT_WINDOW")
        self.assertEqual(f["classification"], "SUSPECT")
        self.assertIn("why_not_defect_confirmed", f)

    def test_ob_mit_is_defect_confirmed_with_direct_evidence(self):
        f = next(x for x in self.payload["findings"] if x["candidate"] == "OB_MIT")
        self.assertEqual(f["classification"], "DEFECT_CONFIRMED")
        self.assertIn("why_confirmed_directly", f)

    def test_crt_verified_not_applicable(self):
        f = next(x for x in self.payload["findings"] if x["candidate"] == "CRT")
        self.assertEqual(f["classification"], "NOT_APPLICABLE")

    def test_residual_gap_declared(self):
        self.assertIn("residual_coverage_gap_declared", self.payload)


class TestPriorityQueue(unittest.TestCase):
    def setUp(self):
        self.payload = queue_builder.build()

    def test_no_pf_flag(self):
        self.assertTrue(self.payload["no_pf_or_contaminated_historical_return_used"])

    def test_not_defaulted_flag(self):
        self.assertTrue(self.payload["not_defaulted_to_tsi_or_bar_updn"])

    def test_top_priority_is_order_block(self):
        self.assertEqual(self.payload["top_priority"], "ORDER_BLOCK")

    def test_every_queue_entry_has_rank_rationale(self):
        for q in self.payload["queue"]:
            self.assertIn("rank_rationale", q)

    def test_registry_gaps_kept_separate(self):
        self.assertIn("registry_gaps_separate_category", self.payload)
        rg = self.payload["registry_gaps_separate_category"]
        ids = [c["strategy"] for c in rg["candidates"]]
        self.assertIn("CRT", ids)
        self.assertIn("FVG_MIT_WINDOW", ids)

    def test_ob_mit_not_a_separate_queue_task(self):
        ob_mit = next(q for q in self.payload["queue"] if q["candidate"] == "OB_MIT")
        self.assertTrue(ob_mit.get("not_a_separate_task"))
        self.assertNotIn("OB_MIT", self.payload["ordered_candidate_ids"])


class TestDiagnosticProtocol(unittest.TestCase):
    def setUp(self):
        self.payload = protocol_builder.build()

    def test_candidate_is_order_block(self):
        self.assertEqual(self.payload["candidate"], "ORDER_BLOCK")

    def test_not_executed_and_no_ea_modification(self):
        self.assertTrue(self.payload["not_executed_this_phase"])
        self.assertTrue(self.payload["no_ea_modification_this_phase"])

    def test_confirmation_and_falsification_criteria_present(self):
        c = self.payload["6_confirmation_vs_falsification_criteria"]
        self.assertIn("would_confirm", c)
        self.assertIn("would_falsify", c)
        self.assertIn("ambiguous_case_handling", c)

    def test_profitability_not_assumed(self):
        self.assertIn("REDDITIVITA", self.payload["7_fix_acceptance_criteria_if_confirmed"]
                      ["explicit_separation"].upper().replace("'", ""))
        self.assertIn("not_assumed", self.payload)

    def test_dependencies_and_blockers_present(self):
        self.assertGreater(len(self.payload["8_dependencies_and_blockers"]), 0)


class TestFrozenAssetsUntouched(unittest.TestCase):
    def test_phase_7_10_and_7_11_not_modified(self):
        for rel in ("server/research_scripts/phase7/phase7_10",
                   "server/research_scripts/phase7/phase7_11"):
            result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=ROOT)
            self.assertEqual(result.returncode, 0, f"{rel} risulta modificato")

    def test_no_mql5_or_python_strategy_files_modified(self):
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", "MQL5/", "server/backtest.py"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        errors = verifier.verify()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
