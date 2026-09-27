#!/usr/bin/env python3
"""Phase 7.18 - suite di test per il fix minimale TSI e la sua
validazione dinamica (trace EA reale pre/post fix)."""
import csv
import os
import subprocess
import sys
import unittest
from collections import Counter, defaultdict

PHASE718_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE718_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE718_DIR)
import build_tsi_parity_comparison as parity_builder  # noqa: E402
import build_tsi_decision_card_v2 as decision_builder  # noqa: E402
import build_tsi_historical_evidence_migration as hist_builder  # noqa: E402
import verify_phase_7_18 as verifier  # noqa: E402

CURATED_PREFIX = os.path.join(PHASE718_DIR, "nxs_tsi_realtrace_diag_prefix_curated.csv")
CURATED_POSTFIX = os.path.join(PHASE718_DIR, "nxs_tsi_realtrace_diag_postfix_curated.csv")
STRAT_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
BASELINE_COMMIT = "8590f63"


class TestArtifactsDeterministic(unittest.TestCase):
    def test_parity_comparison_deterministic(self):
        saved = load_json(os.path.join(PHASE718_DIR, "tsi_parity_comparison_v1.json"))
        self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(parity_builder.build()))

    def test_decision_card_deterministic(self):
        saved = load_json(os.path.join(PHASE718_DIR, "tsi_decision_card_v2.json"))
        self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(decision_builder.build()))

    def test_historical_migration_deterministic(self):
        saved = load_json(os.path.join(PHASE718_DIR, "tsi_historical_evidence_migration_v1.json"))
        self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(hist_builder.build()))


class TestGuardStaticProperties(unittest.TestCase):
    """Test statico della guardia PRIMA di qualunque mutazione di stato."""

    def setUp(self):
        self.text = open(STRAT_PATH, encoding="utf-8").read()

    def test_guard_present_exact_form(self):
        self.assertIn('if(tf != NXS_Profile_TF("TSI")) return s;', self.text)

    def test_guard_precedes_all_state_mutation(self):
        tsi_start = self.text.find("SNXSSignal NXS_Strat_TSI()")
        tsi_end = self.text.find("\n}\n", tsi_start)
        body = self.text[tsi_start:tsi_end]
        guard_pos = body.find('if(tf != NXS_Profile_TF("TSI")) return s;')
        self.assertGreater(guard_pos, 0)
        for mutation_token in ("g_tsiState.init = true", "g_tsiState.sm1 ", "g_tsiState.sm1Abs ",
                               "g_tsiState.sm2 ", "g_tsiState.sm2Abs ", "g_tsiState.signal ",
                               "g_tsiState.prevClose = c1", "g_tsiState.lastBarTime = curBar0",
                               "g_tsiState.barsSeen++"):
            pos = body.find(mutation_token)
            self.assertGreater(pos, guard_pos,
                               f"mutazione '{mutation_token}' precede la guardia")

    def test_no_diagnostic_instrumentation_left(self):
        self.assertNotIn("NXS_TSI_DIAG_TRACE", self.text)
        self.assertNotIn("NXS_TSI_DiagWrite", self.text)
        self.assertNotIn("NXS_TSI_DiagHandle", self.text)

    def test_formula_periods_thresholds_unchanged_tokens_present(self):
        for token in ("InpTSI_LongPeriod", "InpTSI_ShortPeriod", "InpTSI_SignalPeriod",
                     "TSI_cross_up", "TSI_cross_down", "NXS_DefaultSLTP(s)",
                     "g_tsiState.barsSeen < InpTSI_LongPeriod * 3",
                     "100.0 * g_tsiState.sm2 / g_tsiState.sm2Abs"):
            self.assertIn(token, self.text)

    def test_no_wrapper_reuse_by_other_strategies(self):
        result = subprocess.run(["git", "grep", "-n", "NXS_Strat_TSI()", "--", "MQL5/"],
                                cwd=ROOT, capture_output=True, text=True)
        lines = [l for l in result.stdout.strip().splitlines() if l]
        call_sites = [l for l in lines if "SNXSSignal NXS_Strat_TSI()" not in l]
        self.assertEqual(len(call_sites), 1)
        self.assertIn("NEXUS_EA_v2.mq5", call_sites[0])

    def test_only_tsi_function_modified_in_mql5_vs_baseline(self):
        result = subprocess.run(["git", "diff", "--name-only", BASELINE_COMMIT, "HEAD", "--", "MQL5/"],
                                cwd=ROOT, capture_output=True, text=True)
        changed = [l for l in result.stdout.strip().splitlines() if l]
        if changed:
            self.assertEqual(changed, ["MQL5/Include/NEXUS_v1/NXS_Strategies.mqh"])


class TestNonCanonicalNeverMutatesPostFix(unittest.TestCase):
    def test_postfix_trace_has_zero_non_canonical_rows(self):
        with open(CURATED_POSTFIX, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        self.assertGreater(len(rows), 0)
        non_canonical = [r for r in rows if r["tf"] != r["canonical_tf"]]
        self.assertEqual(len(non_canonical), 0)

    def test_postfix_still_produces_canonical_signals(self):
        with open(CURATED_POSTFIX, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        fired = [r for r in rows if r["signal_dir"] in ("BUY", "SELL")]
        self.assertGreater(len(fired), 0, "il fix non deve azzerare completamente i segnali D1")
        for r in fired:
            self.assertEqual(r["tf"], "PERIOD_D1")
            self.assertEqual(r["would_be_kept_by_router"], "1")


class TestPreFixDefectReproduced(unittest.TestCase):
    def test_prefix_trace_has_non_canonical_rows(self):
        with open(CURATED_PREFIX, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        non_canonical = [r for r in rows if r["tf"] != r["canonical_tf"]]
        self.assertGreater(len(non_canonical), 0)

    def test_prefix_shows_flip_flop_within_same_d1_close_time(self):
        """Evidenza diretta della contaminazione: lo stesso close_time_srv D1
        mostra piu' di un signal_dir distinto (perche' tick non canonici
        alterano g_tsiState fra due letture etichettate D1)."""
        with open(CURATED_PREFIX, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        groups = defaultdict(set)
        for r in rows:
            if r["tf"] == "PERIOD_D1":
                groups[r["close_time_srv"]].add(r["signal_dir"])
        multi = [k for k, v in groups.items() if len(v) > 1]
        self.assertGreater(len(multi), 0)

    def test_curation_is_lossless_for_signal_dir_transitions(self):
        """La curazione (transition-based) non deve mai avere due righe
        consecutive con lo stesso (close_time_srv, tf, signal_dir)."""
        with open(CURATED_PREFIX, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        last = {}
        for r in rows:
            key = (r["close_time_srv"], r["tf"])
            self.assertNotEqual(last.get(key), r["signal_dir"],
                               f"riga duplicata consecutiva non eliminata per {key}")
            last[key] = r["signal_dir"]


class TestParityComparison(unittest.TestCase):
    def setUp(self):
        self.payload = parity_builder.build()

    def test_guard_fully_effective(self):
        self.assertTrue(self.payload["guard_effectiveness_check"]["guard_fully_effective_zero_non_canonical_mutations"])
        self.assertEqual(self.payload["guard_effectiveness_check"]["non_canonical_rows_present_in_B"], 0)

    def test_b_signals_all_found_in_c(self):
        # zero segnali B (EA reale post-fix) assenti dalla ricostruzione C -
        # il cuore della validazione dinamica.
        self.assertEqual(self.payload["b_vs_c_structural_comparison"]["n_b_only_vs_c"], 0)

    def test_a_shows_far_more_spurious_canonical_events_than_b(self):
        ab = self.payload["a_vs_b_same_real_ticks_comparison"]
        self.assertGreater(ab["n_only_in_a"], ab["n_only_in_b"])

    def test_python_not_ground_truth_flag(self):
        self.assertTrue(self.payload["python_not_ground_truth_mt5_postfix_is_canonical"])

    def test_not_a_backtest_campaign(self):
        self.assertTrue(self.payload["not_a_backtest_campaign"])
        self.assertTrue(self.payload["not_used_for_profitability"])


class TestDecisionCardV2(unittest.TestCase):
    def setUp(self):
        self.card = load_json(os.path.join(PHASE718_DIR, "tsi_decision_card_v2.json"))["payload"]

    def test_decision_allowed(self):
        self.assertIn(self.card["decision"],
                      {"FIX_CAUSALLY_VALIDATED", "FIX_PARTIALLY_VALIDATED",
                       "FIX_NOT_VALIDATED", "INSUFFICIENT_RUNTIME_EVIDENCE"})

    def test_no_research_economics(self):
        self.assertTrue(self.card["no_optimization_no_sltp_tuning_no_parameter_sweep_no_profitability_no_promotion"])

    def test_fix_applied_matches_guard(self):
        self.assertEqual(self.card["fix_applied"]["change"], 'if(tf != NXS_Profile_TF("TSI")) return s;')

    def test_no_wrapper_reuse_declared(self):
        self.assertIn("no_wrapper_reuse_by_other_strategies", self.card["fix_applied"])


class TestHistoricalEvidenceMigration(unittest.TestCase):
    def setUp(self):
        self.payload = hist_builder.build()

    def test_no_artifact_deleted(self):
        self.assertTrue(self.payload["no_artifact_deleted"])

    def test_no_old_result_reused(self):
        self.assertTrue(self.payload["no_old_mt5_result_reused_as_evidence_of_new_implementation"])

    def test_python_engine_marked_partial(self):
        self.assertEqual(self.payload["python_backtest_engine_status"]["classification"],
                         "PARTIAL_STRUCTURAL_MODEL_NOT_EVENT_LEVEL_PARITY_VALIDATED")

    def test_prior_phase_7_17_classifications_carried_over(self):
        items = self.payload["implementations"]["TSI_IMPL_V1_CONTAMINATED"]["prior_classification_from_phase_7_17"]
        self.assertGreater(len(items), 0)


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        self.assertEqual(verifier.verify(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
