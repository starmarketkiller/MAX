#!/usr/bin/env python3
"""Phase 7.9J - suite di test di consistenza per la revisione
metodologica di Phase 7.9I (causalita' temporale, popolazioni,
allineamento, natural horizon, linguaggio)."""
import copy
import os
import subprocess
import sys
import unittest
from datetime import datetime

PHASE79J_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79I_DIR = os.path.abspath(os.path.join(PHASE79J_DIR, "..", "phase7_9i"))
ROOT = os.path.abspath(os.path.join(PHASE79J_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE79I_DIR)
sys.path.insert(0, PHASE79J_DIR)
import build_direction_alignment_outcome_table as alignment_builder  # noqa: E402
import build_executive_summary_and_decision_card as exec_builder  # noqa: E402
import build_feature_engineering as feat_builder  # noqa: E402
import build_mechanism_discovery as mech_builder  # noqa: E402
import build_natural_horizon_reconciliation as horizon_recon_builder  # noqa: E402
import build_sensitivity_67_vs_75_path_reconstruction as sens_path_builder  # noqa: E402
import build_temporal_causality_audit as temporal_audit_builder  # noqa: E402
import nxs_mechanism_context as ctx  # noqa: E402
import verify_phase_7_9j as verifier  # noqa: E402


class TestCausalNonLeakage(unittest.TestCase):
    """Punto 1 della revisione: modificare barre non ancora disponibili
    alla decisione non deve cambiare la feature di quell'evento."""

    def setUp(self):
        self.d1_bars = ctx.load_d1_bars()
        self.as_of = datetime(2019, 6, 5)

    def _mutate_future(self, bars, as_of):
        mutated = copy.deepcopy(bars)
        for b in mutated:
            if b["time"].date() >= as_of.date():
                b["close"] *= 1000.0
                b["high"] *= 1000.0
                b["low"] *= 1000.0
        return mutated

    def test_causal_ema_unaffected_by_future_bars(self):
        before = ctx.causal_ema(self.d1_bars, self.as_of, period=100)
        mutated = self._mutate_future(self.d1_bars, self.as_of)
        after = ctx.causal_ema(mutated, self.as_of, period=100)
        self.assertEqual(before, after)

    def test_causal_atr_unaffected_by_future_bars(self):
        before = ctx.causal_atr(self.d1_bars, self.as_of, period=20)
        mutated = self._mutate_future(self.d1_bars, self.as_of)
        after = ctx.causal_atr(mutated, self.as_of, period=20)
        self.assertEqual(before, after)

    def test_causal_ema_local_trend_unaffected_by_future_bars(self):
        before = ctx.causal_ema(self.d1_bars, self.as_of, period=20)
        mutated = self._mutate_future(self.d1_bars, self.as_of)
        after = ctx.causal_ema(mutated, self.as_of, period=20)
        self.assertEqual(before, after)

    def test_causal_ema_DOES_react_to_past_bar_changes(self):
        # sanity check inverso: se la funzione ignorasse TUTTI i dati (bug diverso),
        # il test di non-leakage passerebbe banalmente - verifichiamo che reagisca
        # correttamente a modifiche di barre PASSATE.
        before = ctx.causal_ema(self.d1_bars, self.as_of, period=100)
        mutated = copy.deepcopy(self.d1_bars)
        for b in mutated:
            if b["time"].date() < self.as_of.date():
                b["close"] *= 1.5
        after = ctx.causal_ema(mutated, self.as_of, period=100)
        self.assertNotEqual(before, after)

    def test_causal_ema_uses_strict_less_than_in_source(self):
        src = open(os.path.join(PHASE79I_DIR, "nxs_mechanism_context.py"), encoding="utf-8").read()
        fn_start = src.find("def causal_ema(")
        fn_body = src[fn_start:src.find("\n\n\n", fn_start)]
        self.assertNotIn("<= as_of_date.date()", fn_body)
        self.assertIn("< as_of_date.date()", fn_body)


class TestTemporalCausalityAuditContent(unittest.TestCase):
    def setUp(self):
        self.payload = temporal_audit_builder.build()

    def test_bug_documented_as_confirmed_and_fixed(self):
        self.assertIn("bug_confirmed_and_fixed", self.payload)

    def test_impact_measured_zero_flips(self):
        impact = self.payload["bug_confirmed_and_fixed"]["impact_measured"]
        self.assertEqual(impact["trend_aligned_flag_flips_out_of_75"], 0)

    def test_atr_confirmed_correct_from_origin(self):
        self.assertIn("causal_atr_checked_and_confirmed_correct_from_origin", self.payload)

    def test_bar_offset_issue_documented_not_corrected(self):
        finding = self.payload["bar_offset_in_forward_path_confirmed_not_corrected"]
        self.assertEqual(finding["status"], "CONFIRMED_NOT_CORRECTED_UPSTREAM_IN_FROZEN_7_9H")


class TestZeroVariationAlignment(unittest.TestCase):
    def setUp(self):
        self.payload = alignment_builder.build()

    def test_zero_variation_confirmed(self):
        self.assertTrue(self.payload["zero_variation_in_alignment_across_all_75_events"])
        self.assertEqual(self.payload["n_misaligned_ema100_regime_all75"], 0)
        self.assertEqual(self.payload["n_misaligned_ema20_local_all75"], 0)

    def test_confound_discussed(self):
        self.assertIn("CONFUSI", self.payload["confound_discussion"])

    def test_no_new_hypothesis_implemented(self):
        self.assertTrue(self.payload["new_hypothesis_not_implemented"])


class TestNaturalHorizonReconciliation(unittest.TestCase):
    def setUp(self):
        self.payload = horizon_recon_builder.build()

    def test_overlap_quantified(self):
        overlap = self.payload["window_overlap_analysis"]
        self.assertGreater(overlap["pct_consecutive_gaps_overlapping"], 0)

    def test_revised_horizon_not_identified(self):
        self.assertFalse(self.payload["revised_stable_horizon_identified"])

    def test_epistemic_downgrade_present(self):
        self.assertIn("DECLASSAMENTO", self.payload["epistemic_downgrade"])


class TestSensitivityPathReconstruction(unittest.TestCase):
    def setUp(self):
        self.payload = sens_path_builder.build()

    def test_reconstructable_for_all_8_b_only(self):
        self.assertTrue(self.payload["reconstructable_for_all_8_b_only"])

    def test_no_fill_or_pnl_attributed_to_non_opened(self):
        self.assertTrue(self.payload["no_fill_or_pnl_attributed_to_non_opened_events"])

    def test_real_and_counterfactual_kept_separate(self):
        profile = self.payload["population_A_67_path_profile"]
        self.assertIn("n_real_fill", profile)
        self.assertIn("n_counterfactual_proxy", profile)
        self.assertEqual(profile["n_real_fill"], 47)
        self.assertEqual(profile["n_counterfactual_proxy"], 20)


class TestLanguageRevision(unittest.TestCase):
    def test_mechanism_discovery_has_lineage_note(self):
        payload = mech_builder.build()
        self.assertIn("lineage_note", payload)

    def test_executive_summary_has_lineage_note(self):
        payload = exec_builder.build()
        self.assertIn("lineage_note", payload)

    def test_final_decision_unchanged(self):
        payload = exec_builder.build()
        self.assertEqual(payload["final_decision"], "MECHANISM_PARTIALLY_SUPPORTED")

    def test_no_forbidden_words(self):
        import json
        payload = exec_builder.build()
        text = json.dumps(payload, ensure_ascii=False).upper()
        for w in ("PROMOTE", "DEPLOY", "PROFITABLE"):
            self.assertNotIn(w, text)


class TestFrozenAssetsUntouched(unittest.TestCase):
    def test_phase_7_9h_dataset_not_modified(self):
        dataset_path = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_9h",
                                    "breakout_acc_intended_d1_v1_dataset.json")
        result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", dataset_path], cwd=ROOT)
        self.assertEqual(result.returncode, 0)

    def test_no_mql5_or_python_files_modified(self):
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", "MQL5/", "server/backtest.py"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")

    def test_pre_fix_originals_preserved(self):
        p = os.path.join(PHASE79J_DIR, "raw_data_pre_fix",
                         "breakout_acc_feature_engineering_v1_ORIGINAL_pre_temporal_fix.json")
        self.assertTrue(os.path.exists(p))
        doc = load_json(p)
        self.assertIn("payload", doc)


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        errors = verifier.verify()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
