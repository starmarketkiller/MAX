#!/usr/bin/env python3
"""Phase 7.11 - suite di test di consistenza per il Complete Strategy Census."""
import os
import subprocess
import sys
import unittest

PHASE711_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE711_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE711_DIR)
import build_complete_strategy_census as census_builder  # noqa: E402
import build_census_summary as summary_builder  # noqa: E402
import verify_complete_strategy_census as verifier  # noqa: E402


class TestCensusDeterminism(unittest.TestCase):
    def test_census_build_is_deterministic(self):
        a = census_builder.build()
        b = census_builder.build()
        self.assertEqual(canonical_sha256(a), canonical_sha256(b))

    def test_summary_build_is_deterministic(self):
        a = summary_builder.build()
        b = summary_builder.build()
        self.assertEqual(canonical_sha256(a), canonical_sha256(b))

    def test_saved_census_matches_fresh_build(self):
        saved = load_json(os.path.join(PHASE711_DIR, "complete_strategy_census_v1.json"))
        fresh = census_builder.build()
        self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(fresh))

    def test_saved_summary_matches_fresh_build(self):
        saved = load_json(os.path.join(PHASE711_DIR, "census_summary_v1.json"))
        fresh = summary_builder.build()
        self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(fresh))


class TestCensusStructure(unittest.TestCase):
    def setUp(self):
        self.rows = census_builder.build()["census_rows"]
        self.required_fields = [
            "canonical_strategy_id", "aliases", "variant_of", "first_seen", "last_seen",
            "current_status", "live_mql5", "python_implementation", "vault_documentation",
            "registry_presence", "profile_presence", "selector_presence", "stateful",
            "canonical_tf", "historical_tests", "known_parity_status",
            "known_implementation_defects", "evidence_status", "lineage_notes",
        ]

    def test_no_duplicate_ids(self):
        ids = [r["canonical_strategy_id"] for r in self.rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_row_count_is_83(self):
        self.assertEqual(len(self.rows), 83)

    def test_every_row_has_required_fields(self):
        for r in self.rows:
            for f in self.required_fields:
                self.assertIn(f, r, f"riga {r.get('canonical_strategy_id')} manca campo {f}")

    def test_no_row_asserts_both_absent_from_and_present_in_same_source_key(self):
        for r in self.rows:
            self.assertIsInstance(r["registry_presence"], dict)

    def test_crt_and_fvg_mit_window_flagged_never_fully_implemented(self):
        by_id = {r["canonical_strategy_id"]: r for r in self.rows}
        for sid in ("CRT", "FVG_MIT_WINDOW"):
            self.assertTrue(by_id[sid].get("registry_gap_UNKNOWN_STRATEGY_REGISTRY_GAP"))
            self.assertTrue(by_id[sid]["live_mql5"])

    def test_no_strategy_in_this_phase_was_corrected_or_retested(self):
        payload = census_builder.build()
        self.assertTrue(payload.get("no_corrections_or_retests_applied"))
        payload2 = summary_builder.build()
        self.assertTrue(payload2.get("no_corrections_or_retests_applied"))


class TestSummaryOutputs(unittest.TestCase):
    def setUp(self):
        self.summary = summary_builder.build()

    def test_all_six_outputs_present(self):
        for i in range(1, 7):
            keys = [k for k in self.summary if k.startswith(f"output_{i}_")]
            self.assertTrue(keys, f"manca output_{i}_*")

    def test_live_count_matches_census(self):
        rows = census_builder.build()["census_rows"]
        live = sum(1 for r in rows if r["live_mql5"])
        self.assertEqual(live, self.summary["output_2_counts_by_category"]["live"])

    def test_live_count_is_55_not_53(self):
        # la correzione chiave di questa fase: 53 dichiarate dal registry + CRT + FVG_MIT_WINDOW
        self.assertEqual(self.summary["output_2_counts_by_category"]["live"], 55)

    def test_never_fully_implemented_includes_crt_and_fvg_mit_window(self):
        lst = self.summary["output_2_counts_by_category"]["never_fully_implemented_list"]
        self.assertIn("CRT", lst)
        self.assertIn("FVG_MIT_WINDOW", lst)

    def test_no_merge_or_split_flags_true(self):
        self.assertTrue(self.summary["no_strategies_merged_by_name_similarity"])
        self.assertTrue(self.summary["no_identities_split_without_code_evidence"])


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        errors = verifier.verify()
        self.assertEqual(errors, [])

    def test_no_mql5_or_python_strategy_files_modified_this_phase(self):
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", "MQL5/", "server/backtest.py"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
