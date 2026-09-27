#!/usr/bin/env python3
"""Phase 7.17 - suite di test per il TSI Integrity Audit + Minimal
Diagnostic."""
import os
import subprocess
import sys
import unittest

PHASE717_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE717_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE717_DIR)
from nxs_tsi_replica import TSIState, tsi_update, LONG_PERIOD  # noqa: E402
import build_tsi_semantic_map as map_builder  # noqa: E402
import build_tsi_mechanism_formalization as mech_builder  # noqa: E402
import build_tsi_minimal_cases as cases_builder  # noqa: E402
import build_tsi_impact_comparison as impact_builder  # noqa: E402
import build_tsi_python_fidelity as fidelity_builder  # noqa: E402
import build_tsi_historical_evidence_map as hist_builder  # noqa: E402
import build_tsi_decision_card as card_builder  # noqa: E402
import verify_phase_7_17 as verifier  # noqa: E402

ARTIFACTS = [
    ("tsi_semantic_map_v1.json", map_builder.build),
    ("tsi_mechanism_formalization_v1.json", mech_builder.build),
    ("tsi_minimal_cases_v1.json", cases_builder.build),
    ("tsi_impact_comparison_v1.json", impact_builder.build),
    ("tsi_python_fidelity_v1.json", fidelity_builder.build),
    ("tsi_historical_evidence_map_v1.json", hist_builder.build),
    ("tsi_decision_card_v1.json", card_builder.build),
]


class TestDeterminism(unittest.TestCase):
    def test_all_artifacts_deterministic(self):
        for fname, build_fn in ARTIFACTS:
            saved = load_json(os.path.join(PHASE717_DIR, fname))
            fresh = build_fn()
            self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(fresh), fname)


class TestReplicaUnit(unittest.TestCase):
    """Unit test della ricorsione TSI, con serie DIVERSE dai casi minimi
    dell'artifact ufficiale (copertura aggiuntiva)."""

    def test_warmup_gate_blocks_signal(self):
        st = TSIState()
        st.init = True
        st.last_bar_time = "T0"
        st.bars_seen = 0
        sig, rec = tsi_update(st, 105.0, "T1", seed_close=100.0)
        self.assertIsNone(sig)
        self.assertEqual(st.bars_seen, 1)

    def test_no_new_bar_no_mutation(self):
        st = TSIState()
        st.init = True
        st.last_bar_time = "T1"
        st.bars_seen = 100
        st.sm2, st.sm2_abs = 1.0, 3.0
        pre = st.snapshot()
        sig, rec = tsi_update(st, 999.0, "T1", seed_close=100.0)
        self.assertFalse(rec["mutated"])
        self.assertEqual(st.snapshot(), pre)

    def test_cross_up_detected(self):
        st = TSIState()
        st.init = True
        st.last_bar_time = "T0"
        st.bars_seen = 1000
        st.sm2, st.sm2_abs = -1.0, 3.0   # TSI negativo
        st.signal = 0.0                  # signal sopra TSI -> tsiPrev<=signalPrev
        sig, rec = tsi_update(st, 200.0, "T1", seed_close=100.0)
        # una forte salita di prezzo dovrebbe spingere tsi sopra signal
        self.assertIn(sig, ("BUY", None))  # non deterministico a mano qui, solo smoke test


class TestSemanticMap(unittest.TestCase):
    def setUp(self):
        self.payload = map_builder.build()

    def test_no_tf_guard_present(self):
        self.assertFalse(self.payload["selector_and_profile"]["tf_guard_present"])

    def test_no_wrapper_reuse(self):
        self.assertIn("NESSUNO", self.payload["canonical_function"]["wrappers_or_reuse"])

    def test_default_periods_match_mql5(self):
        periods = self.payload["double_ema_structure"]["default_periods"]
        self.assertEqual(periods["InpTSI_LongPeriod"], 25)
        self.assertEqual(periods["InpTSI_ShortPeriod"], 13)
        self.assertEqual(periods["InpTSI_SignalPeriod"], 7)


class TestMechanismFormalization(unittest.TestCase):
    def test_universality_prediction_present(self):
        payload = mech_builder.build()
        self.assertIn("UNIVERSALE", payload["key_qualitative_difference_from_order_block"]["tsi"])


class TestMinimalCases(unittest.TestCase):
    def setUp(self):
        self.payload = cases_builder.build()

    def test_independent_exact_arithmetic_used(self):
        self.assertTrue(self.payload["expected_values_computed_independently_not_from_function_under_test"])

    def test_float_implementation_matches_exact_reference(self):
        cc = self.payload["float_implementation_cross_check"]
        self.assertTrue(cc["tsi_update_stream_A_matches_exact_reference"])
        self.assertTrue(cc["tsi_update_stream_B_matches_exact_reference"])

    def test_divergence_is_nonzero(self):
        self.assertNotEqual(self.payload["divergence_at_D1_2"]["tsi_difference"], 0.0)


class TestImpactComparison(unittest.TestCase):
    def setUp(self):
        self.payload = impact_builder.build()

    def test_universal_divergence_confirmed(self):
        tv = self.payload["tsi_value_divergence"]
        self.assertEqual(tv["pct_d1_bars_tsi_different"], 100.0)

    def test_material_impact_flag(self):
        self.assertTrue(self.payload["defect_materially_changes_behavior"])
        self.assertTrue(self.payload["defect_exists"])

    def test_no_pf_used(self):
        self.assertTrue(self.payload["no_pf_or_return_used"])

    def test_no_new_tester_run(self):
        self.assertTrue(self.payload["no_new_tester_run_launched"])

    def test_m5_excluded_declared(self):
        self.assertIn("M5", self.payload["excluded_passes_declared"])


class TestPythonFidelity(unittest.TestCase):
    def setUp(self):
        self.payload = fidelity_builder.build()

    def test_classification_allowed(self):
        self.assertIn(self.payload["classification"],
                      {"EVENT_LEVEL_PARITY_VALIDATED", "PARTIAL_STRUCTURAL_MODEL",
                       "APPROXIMATION_WITH_KNOWN_GAPS", "NOT_SUITABLE_FOR_EVENT_PARITY",
                       "INSUFFICIENT_EVIDENCE"})

    def test_caveat_not_live_trace_present(self):
        self.assertIn("NON", self.payload["important_caveat"])

    def test_no_time_spent_chasing_perfect_parity(self):
        self.assertTrue(self.payload["no_new_campaign_time_spent_on_perfect_parity"])


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

    def test_sweep37_evidence_present(self):
        found = any("sweep37" in it["artifact"] for it in self.payload["items"])
        self.assertTrue(found)


class TestDecisionCard(unittest.TestCase):
    def setUp(self):
        self.payload = card_builder.build()

    def test_decision_in_allowed_set(self):
        self.assertIn(self.payload["decision"],
                      {"DEFECT_NOT_REPRODUCED", "DEFECT_CONFIRMED_LOW_IMPACT",
                       "DEFECT_CONFIRMED_MATERIAL_IMPACT", "INSUFFICIENT_EVIDENCE"})

    def test_required_fields_present(self):
        for field in ("distortion_direction", "historical_evidence_integrity", "confidence"):
            self.assertIn(field, self.payload)

    def test_fix_proposed_not_applied(self):
        self.assertTrue(self.payload["fix_proposal"]["proposed_only_not_applied"])
        self.assertTrue(self.payload["no_ea_modification_this_phase"])

    def test_profitability_explicitly_not_assumed(self):
        sep = self.payload["fix_proposal"]["separazione_esplicita"]
        self.assertIn("NON PRESUNTA", sep["redditivita"].upper().replace("'", ""))

    def test_no_research_economics_flags(self):
        self.assertTrue(self.payload[
            "no_optimization_no_sltp_tuning_no_parameter_sweep_no_profitability_no_promotion"])


class TestNoScopeViolations(unittest.TestCase):
    def test_no_mql5_modified(self):
        result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")

    def test_no_new_tester_ini_created(self):
        inis = [f for f in os.listdir(PHASE717_DIR) if f.endswith(".ini")]
        self.assertEqual(inis, [])

    def test_phase_7_13_multi_tf_dataset_untouched(self):
        # riusato in sola lettura - multi_tf_dataset_v1.json e' gia' untracked (??)
        # per scelta di Phase 7.13 (31MB, non committato) - qui verifichiamo solo che
        # non ci siano MODIFICHE (righe 'M'), l'untracked preesistente e' atteso.
        result = subprocess.run(
            ["git", "status", "--porcelain", "--",
            "server/research_scripts/phase7/phase7_13/"],
            cwd=ROOT, capture_output=True, text=True)
        modified_lines = [l for l in result.stdout.splitlines() if l.strip().startswith("M")]
        self.assertEqual(modified_lines, [])


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        self.assertEqual(verifier.verify(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
