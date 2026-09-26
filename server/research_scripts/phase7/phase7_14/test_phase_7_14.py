#!/usr/bin/env python3
"""Phase 7.14 - suite di test per il trace reale ORDER_BLOCK e
l'adjudication del fix."""
import csv
import os
import subprocess
import sys
import unittest

PHASE714_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE714_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE714_DIR)
import build_ob_mit_dependency_map as obmit_builder  # noqa: E402
import build_historical_evidence_migration as hist_builder  # noqa: E402
import verify_phase_7_14 as verifier  # noqa: E402

CURATED_PREFIX = os.path.join(PHASE714_DIR, "nxs_orderblock_realtrace_diag_prefix_curated.csv")
CURATED_POSTFIX = os.path.join(PHASE714_DIR, "nxs_orderblock_realtrace_diag_postfix_curated.csv")
STRAT_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")


class TestStaticArtifactsDeterministic(unittest.TestCase):
    def test_ob_mit_map_deterministic(self):
        saved = load_json(os.path.join(PHASE714_DIR, "ob_mit_dependency_map_v1.json"))
        self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(obmit_builder.build()))

    def test_historical_migration_deterministic(self):
        saved = load_json(os.path.join(PHASE714_DIR, "historical_evidence_migration_v1.json"))
        self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(hist_builder.build()))


class TestGuardStaticProperties(unittest.TestCase):
    """Test statico della guardia PRIMA di qualunque mutazione (punto 9,
    'test statico della guardia prima delle mutazioni')."""

    def setUp(self):
        self.text = open(STRAT_PATH, encoding="utf-8").read()

    def test_guard_present_exact_form(self):
        self.assertIn('if(tf != NXS_Profile_TF("ORDER_BLOCK")) return s;', self.text)

    def test_guard_precedes_state_reads(self):
        ob_start = self.text.find("SNXSSignal NXS_Strat_OrderBlock()")
        ob_end = self.text.find("\n}\n", ob_start)
        body = self.text[ob_start:ob_end]
        guard_pos = body.find('if(tf != NXS_Profile_TF("ORDER_BLOCK")) return s;')
        # cerca l'uso IN CODICE (chiamata reale), non la menzione nel commento
        # esplicativo sopra la guardia stessa.
        first_g_obbuy_call = body.find("g_obBuy, tf")
        self.assertGreater(guard_pos, 0)
        self.assertGreater(first_g_obbuy_call, guard_pos,
                           "la guardia deve precedere ogni lettura/chiamata reale su g_obBuy")

    def test_no_diagnostic_instrumentation_left(self):
        self.assertNotIn("NXS_OB_DIAG_TRACE", self.text)
        self.assertNotIn("NXS_OB_DiagWrite", self.text)

    def test_other_strategy_logic_unchanged_tokens_present(self):
        for token in ("1.2 * atr", "InpOB_MaxWaitBars", "OB_retest_bull", "OB_retest_bear",
                     "NXS_DefaultSLTP(s)", "InpOB_SwingLookback"):
            self.assertIn(token, self.text)

    def test_only_order_block_function_modified_in_mql5(self):
        result = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", "MQL5/"],
                                cwd=ROOT, capture_output=True, text=True)
        changed = [l for l in result.stdout.strip().splitlines() if l]
        self.assertEqual(changed, ["MQL5/Include/NEXUS_v1/NXS_Strategies.mqh"])


class TestNonCanonicalNeverMutatesPostFix(unittest.TestCase):
    """Test che i TF non canonici non alterino lo stato (punto 9)."""

    def test_postfix_trace_has_zero_non_canonical_rows(self):
        with open(CURATED_POSTFIX, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        self.assertGreater(len(rows), 0)
        non_canonical = [r for r in rows if r["tf"] != r["canonical_tf"]]
        self.assertEqual(len(non_canonical), 0)


class TestD1BehaviorPreservedPostFix(unittest.TestCase):
    """Test che D1 conservi il comportamento previsto (punto 9)."""

    def test_postfix_still_produces_canonical_signals(self):
        with open(CURATED_POSTFIX, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        fired = [r for r in rows if r["op"] == "RETEST_SIGNAL_FIRED"]
        self.assertGreater(len(fired), 0, "il fix non deve azzerare completamente i segnali D1")
        for r in fired:
            self.assertEqual(r["tf"], "PERIOD_D1")
            self.assertEqual(r["would_be_kept_by_router"], "1")

    def test_postfix_zone_lifecycle_ops_still_occur(self):
        with open(CURATED_POSTFIX, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        ops = {r["op"] for r in rows}
        self.assertIn("ZONE_CREATED", ops)


class TestPreFixDefectReproduced(unittest.TestCase):
    def test_prefix_trace_has_non_canonical_mutations(self):
        with open(CURATED_PREFIX, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        non_canonical = [r for r in rows if r["tf"] != r["canonical_tf"]]
        self.assertGreater(len(non_canonical), 0)

    def test_prefix_shows_repeated_fires_same_day(self):
        with open(CURATED_PREFIX, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        fired_d1 = [r for r in rows if r["op"] == "RETEST_SIGNAL_FIRED" and r["tf"] == "PERIOD_D1"]
        from collections import Counter
        c = Counter((r["close_time_srv"], r["side"]) for r in fired_d1)
        self.assertTrue(any(v > 1 for v in c.values()),
                        "pre-fix deve mostrare almeno un giorno D1 con fire multipli")


class TestOBMitDependencyMap(unittest.TestCase):
    def setUp(self):
        self.payload = obmit_builder.build()

    def test_no_own_state(self):
        self.assertFalse(self.payload["ob_mit_has_own_state"])

    def test_calls_order_block_directly(self):
        self.assertTrue(self.payload["ob_mit_calls_order_block_directly"])

    def test_no_separate_fix_needed(self):
        self.assertTrue(self.payload["no_separate_fix_needed_for_ob_mit"])


class TestHistoricalEvidenceMigration(unittest.TestCase):
    def setUp(self):
        self.payload = hist_builder.build()

    def test_no_artifact_deleted(self):
        self.assertTrue(self.payload["no_artifact_deleted"])

    def test_no_old_result_reused(self):
        self.assertTrue(self.payload["no_old_mt5_result_reused_as_evidence_of_new_implementation"])

    def test_python_engine_marked_separate(self):
        self.assertEqual(self.payload["python_backtest_engine_status"]["classification"],
                         "UNAFFECTED_BY_THIS_BUG_NOT_SEMANTIC_PARITY_PROVEN")


class TestDecisionCardV2(unittest.TestCase):
    def setUp(self):
        self.card = load_json(os.path.join(PHASE714_DIR, "decision_card_v2_order_block_v1.json"))["payload"]

    def test_decision_allowed(self):
        self.assertIn(self.card["decision"],
                      {"FIX_CAUSALLY_VALIDATED", "FIX_PARTIALLY_VALIDATED",
                       "FIX_NOT_VALIDATED", "TRACE_INSUFFICIENT"})

    def test_ob_mit_status_reported_separately(self):
        self.assertIn("ob_mit_status", self.card)
        self.assertIn("conclusion", self.card["ob_mit_status"])

    def test_no_research_economics(self):
        self.assertTrue(self.card["no_optimization_no_sltp_tuning_no_parameter_sweep_no_profitability_no_promotion"])


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        self.assertEqual(verifier.verify(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
