#!/usr/bin/env python3
"""Phase 7.13 - suite di test per la diagnosi causale ORDER_BLOCK."""
import os
import subprocess
import sys
import unittest

PHASE713_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE713_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE713_DIR)
from nxs_order_block_replica import OBState, ob_update_side  # noqa: E402
import build_synthetic_causal_proof as synth_builder  # noqa: E402
import build_multi_tf_dataset as mtf_builder  # noqa: E402
import build_ab_simulation as ab_builder  # noqa: E402
import build_state_mutation_trace as trace_builder  # noqa: E402
import build_historical_evidence_impact_map as hist_builder  # noqa: E402
import build_breakout_acc_comparison as cmp_builder  # noqa: E402
import build_decision_card as card_builder  # noqa: E402
import verify_phase_7_13 as verifier  # noqa: E402

ARTIFACTS = [
    ("synthetic_causal_proof_v1.json", synth_builder.build),
    ("multi_tf_dataset_v1.json", mtf_builder.build),
    ("ab_simulation_v1.json", ab_builder.build),
    ("state_mutation_trace_v1.json", trace_builder.build),
    ("historical_evidence_impact_map_v1.json", hist_builder.build),
    ("breakout_acc_comparison_v1.json", cmp_builder.build),
    ("decision_card_order_block_v1.json", card_builder.build),
]


class TestDeterminism(unittest.TestCase):
    def test_all_artifacts_deterministic(self):
        for fname, build_fn in ARTIFACTS:
            saved = load_json(os.path.join(PHASE713_DIR, fname))
            fresh = build_fn()
            self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(fresh), fname)


class TestReplicaUnit(unittest.TestCase):
    """Unit test della state machine, con serie DIVERSE dalla prova
    sintetica causale (copertura aggiuntiva dei rami)."""

    def _bar(self, o, h, l, c, ot, ct):
        return {"open": o, "high": h, "low": l, "close": c, "open_time": ot, "close_time": ct}

    def test_idle_no_new_bar_returns_none(self):
        st = OBState()
        st.last_bar_time = "T0"
        bars = [self._bar(1, 2, 0, 1, "T0", "T0")]
        sig, reason, rec = ob_update_side(+1, st, bars, 0, 1.0, "T0")
        self.assertIsNone(sig)
        self.assertEqual(rec["op"], "NONE")

    def test_zone_expires_after_max_wait_bars(self):
        st = OBState()
        st.active, st.ob_lo, st.ob_hi, st.bars_waited = True, 100.0, 105.0, 20
        st.last_bar_time = "PREV"
        bars = [self._bar(110, 111, 109, 110, "T0", "T1")]
        sig, reason, rec = ob_update_side(+1, st, bars, 0, 1.0, "T1")
        self.assertIsNone(sig)
        self.assertEqual(rec["op"], "ZONE_EXPIRED")
        self.assertFalse(st.active)

    def test_zone_invalidated_on_wrong_direction_close(self):
        st = OBState()
        st.active, st.ob_lo, st.ob_hi, st.bars_waited = True, 100.0, 105.0, 0
        st.last_bar_time = "PREV"
        bars = [self._bar(102, 103, 90, 95, "T0", "T1")]  # chiude sotto ob_lo -> invalidata (BUY)
        sig, reason, rec = ob_update_side(+1, st, bars, 0, 1.0, "T1")
        self.assertIsNone(sig)
        self.assertEqual(rec["op"], "ZONE_INVALIDATED")
        self.assertFalse(st.active)

    def test_retest_fires_and_consumes_zone_one_shot(self):
        st = OBState()
        st.active, st.ob_lo, st.ob_hi, st.bars_waited = True, 100.0, 105.0, 0
        st.last_bar_time = "PREV"
        bars = [self._bar(103, 104.5, 102, 104, "T0", "T1")]  # tocca e chiude rialzista
        sig, reason, rec = ob_update_side(+1, st, bars, 0, 1.0, "T1")
        self.assertEqual(sig, "BUY")
        self.assertEqual(rec["op"], "RETEST_SIGNAL_FIRED")
        self.assertFalse(st.active)  # one-shot

    def test_sell_side_symmetric_logic(self):
        st = OBState()
        st.active, st.ob_lo, st.ob_hi, st.bars_waited = True, 100.0, 105.0, 0
        st.last_bar_time = "PREV"
        bars = [self._bar(103, 104, 101.5, 101, "T0", "T1")]  # tocca e chiude ribassista
        sig, reason, rec = ob_update_side(-1, st, bars, 0, 1.0, "T1")
        self.assertEqual(sig, "SELL")
        self.assertEqual(rec["op"], "RETEST_SIGNAL_FIRED")


class TestSyntheticCausalProof(unittest.TestCase):
    def setUp(self):
        self.payload = synth_builder.build()

    def test_matches_hand_computed_expectations(self):
        a = [(e["bar"], e["signal"]) for e in self.payload["stream_a_as_implemented"]]
        b = [(e["bar"], e["signal"]) for e in self.payload["stream_b_tf_scoped_diagnostic"]]
        self.assertEqual(a, synth_builder.EXPECTED_STREAM_A_SIGNALS)
        self.assertEqual(b, synth_builder.EXPECTED_STREAM_B_SIGNALS)

    def test_four_causal_phases_all_present(self):
        cd = self.payload["causal_demonstration"]
        for key in ("1_call_on_non_canonical_tf", "2_state_mutation", "3_output_discarded",
                   "4_effect_on_future_canonical_event"):
            self.assertIn(key, cd)
            self.assertTrue(len(cd[key]) > 0)

    def test_no_real_ea_modification(self):
        self.assertTrue(self.payload["no_ea_modification"])
        self.assertTrue(self.payload["no_guard_applied_to_real_source"])


class TestAbSimulation(unittest.TestCase):
    def setUp(self):
        self.payload = ab_builder.build()

    def test_structural_consistency(self):
        p = self.payload
        accounted = (len(p["only_in_a"]) + len(p["only_in_b"]) + p["both_same_direction"]
                    + len(p["both_different_direction"]))
        neither_fired = p["n_d1_events_evaluated"] - accounted
        self.assertGreaterEqual(neither_fired, 0)
        self.assertEqual(p["n_d1_events_evaluated"], accounted + neither_fired)
        # i quattro sottoinsiemi devono essere disgiunti e non superare il totale
        self.assertLessEqual(accounted, p["n_d1_events_evaluated"])

    def test_non_canonical_passes_dominate_raw_triggers(self):
        p = self.payload
        self.assertGreater(p["stream_a_raw_triggers_non_canonical_total"], 0)

    def test_material_impact_flag_matches_observed_divergence(self):
        p = self.payload
        divergence = len(p["only_in_a"]) + len(p["only_in_b"]) + len(p["both_different_direction"])
        self.assertEqual(p["defect_materially_changes_behavior"], divergence > 0)

    def test_gates_declared_not_modeled(self):
        self.assertIn("g_structH1_trend_filter", self.payload["gates_not_modeled_declared"])
        self.assertIn("InpUseSMCReactionGate/NXS_SMCReactionOK", self.payload["gates_not_modeled_declared"])

    def test_m5_pass_declared_excluded(self):
        self.assertIn("M5", self.payload["excluded_passes_declared"])

    def test_not_a_backtest_campaign_flags(self):
        self.assertTrue(self.payload["not_a_backtest_campaign"])
        self.assertTrue(self.payload["not_used_for_profitability"])
        self.assertTrue(self.payload["not_used_for_optimization"])


class TestHistoricalEvidenceMap(unittest.TestCase):
    def setUp(self):
        self.payload = hist_builder.build()

    def test_every_item_has_required_fields(self):
        for it in self.payload["items"]:
            for field in ("artifact", "kind", "classification", "reasoning", "implication"):
                self.assertIn(field, it)
            self.assertIn(it["classification"], self.payload["classifications_used"])

    def test_no_artifact_deleted(self):
        self.assertTrue(self.payload["no_artifact_deleted_or_modified"])
        self.assertTrue(self.payload["no_pf_reinterpreted_as_canonical_evidence"])

    def test_python_engine_classified_unaffected_but_not_representative(self):
        py_item = next(it for it in self.payload["items"] if "backtest.py" in it["artifact"])
        self.assertEqual(py_item["classification"], "UNAFFECTED_BUT_NOT_REPRESENTATIVE_OF_LIVE")


class TestBreakoutAccComparison(unittest.TestCase):
    def setUp(self):
        self.payload = cmp_builder.build()

    def test_not_transferable_assumptions_declared(self):
        self.assertGreater(len(self.payload["not_transferable_assumptions"]), 0)

    def test_state_mechanism_dimension_marked_different(self):
        row = next(c for c in self.payload["comparison_table"] if c["dimension"] == "Tipo di stato condiviso")
        self.assertFalse(row["identico"])

    def test_fix_form_transferable_but_not_applied(self):
        row = next(c for c in self.payload["comparison_table"]
                  if "Punto e forma del fix" in c["dimension"])
        self.assertEqual(row["identico"], "forma si, applicazione no")


class TestDecisionCard(unittest.TestCase):
    def setUp(self):
        self.payload = card_builder.build()

    def test_decision_in_allowed_set(self):
        self.assertIn(self.payload["decision"],
                      {"DEFECT_NOT_REPRODUCED", "DEFECT_CONFIRMED_LOW_IMPACT",
                       "DEFECT_CONFIRMED_MATERIAL_IMPACT", "INSUFFICIENT_EVIDENCE"})

    def test_distortion_direction_in_allowed_set(self):
        self.assertIn(self.payload["distortion_direction"],
                      {"FALSE_NEGATIVE_RISK", "FALSE_POSITIVE_RISK", "BOTH", "NONE_KNOWN", "UNKNOWN"})

    def test_fix_proposed_not_applied(self):
        self.assertTrue(self.payload["fix_proposal"]["proposed_only_not_applied"])
        self.assertTrue(self.payload["ea_source_untouched_this_phase"])

    def test_profitability_explicitly_not_assumed(self):
        sep = self.payload["fix_proposal"]["separazione_esplicita"]
        self.assertIn("NON PRESUNTA", sep["redditivita"].upper().replace("'", ""))

    def test_no_research_economics_flags(self):
        self.assertTrue(self.payload[
            "no_optimization_no_sltp_tuning_no_sweep_no_profitability_no_rescue_no_live_promotion"])


class TestOutcomeVsCoverageStyleDistinction(unittest.TestCase):
    """Coerenza con la disciplina gia' applicata in Phase 7.9K: distinguere
    sempre 'il difetto esiste' da 'il difetto cambia materialmente
    l'esito' invece di sommarli in un'unica cifra."""

    def test_decision_card_keeps_the_two_questions_separate(self):
        card = card_builder.build()
        both = card["defect_exists_vs_material_impact"]
        self.assertIn("defect_exists", both)
        self.assertIn("defect_materially_changes_behavior", both)
        self.assertIsInstance(both["defect_exists"], bool)
        self.assertIsInstance(both["defect_materially_changes_behavior"], bool)


class TestFrozenAssetsUntouched(unittest.TestCase):
    def test_no_mql5_modified(self):
        result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")

    def test_phase_7_9_to_7_12_frozen_dirs_untouched(self):
        for rel in ("server/research_scripts/phase7/phase7_9h",
                   "server/research_scripts/phase7/phase7_9i",
                   "server/research_scripts/phase7/phase7_9j",
                   "server/research_scripts/phase7/phase7_9k",
                   "server/research_scripts/phase7/phase7_10",
                   "server/research_scripts/phase7/phase7_11",
                   "server/research_scripts/phase7/phase7_12"):
            result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=ROOT)
            self.assertEqual(result.returncode, 0, f"{rel} risulta modificato")


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        self.assertEqual(verifier.verify(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
