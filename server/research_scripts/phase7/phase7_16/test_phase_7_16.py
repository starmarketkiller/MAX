#!/usr/bin/env python3
"""Phase 7.16 - suite di test per la diagnosi breve EA/Python
ORDER_BLOCK."""
import os
import subprocess
import sys
import unittest

PHASE716_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE713_DIR = os.path.abspath(os.path.join(PHASE716_DIR, "..", "phase7_13"))
ROOT = os.path.abspath(os.path.join(PHASE716_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE713_DIR)
from nxs_order_block_replica import OBState, ob_update_side  # noqa: E402

sys.path.insert(0, PHASE716_DIR)
from nxs_order_block_replica_corrected import ob_update_side_corrected  # noqa: E402
import build_semantic_contract_matrix as matrix_builder  # noqa: E402
import build_first_divergence as divergence_builder  # noqa: E402
import build_minimal_episodes as episodes_builder  # noqa: E402
import build_fidelity_classification_and_proposal as classification_builder  # noqa: E402
import verify_phase_7_16 as verifier  # noqa: E402

ARTIFACTS = [
    ("semantic_contract_matrix_v1.json", matrix_builder.build),
    ("first_divergence_v1.json", divergence_builder.build),
    ("minimal_episodes_v1.json", episodes_builder.build),
    ("fidelity_classification_and_proposal_v1.json", classification_builder.build),
]


class TestDeterminism(unittest.TestCase):
    def test_all_artifacts_deterministic(self):
        for fname, build_fn in ARTIFACTS:
            saved = load_json(os.path.join(PHASE716_DIR, fname))
            fresh = build_fn()
            self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(fresh), fname)


class TestSemanticContractMatrix(unittest.TestCase):
    def setUp(self):
        self.payload = matrix_builder.build()

    def test_funnel_level_confirmed_not_assumed(self):
        self.assertTrue(self.payload["no_assumption_that_8_and_7_are_same_funnel_level"])

    def test_touched_bar_dimension_flags_the_bug(self):
        dim = next(m for m in self.payload["matrix"] if "Tick/Bid" in m["dimension"])
        self.assertIn("ERRORE DI ALLINEAMENTO", dim["verdict"])

    def test_structural_flow_dimensions_marked_identical(self):
        creation = next(m for m in self.payload["matrix"] if "Creazione zona" in m["dimension"])
        self.assertIn("IDENTICO", creation["verdict"])


class TestFirstDivergence(unittest.TestCase):
    def setUp(self):
        self.payload = divergence_builder.build()

    def test_correction_improves_match_with_ea(self):
        self.assertTrue(self.payload["correction_improves_match_rate"])
        self.assertGreater(self.payload["n_matches_corrected_vs_ea"], self.payload["n_matches_original_vs_ea"])

    def test_first_divergence_found_on_local_series(self):
        self.assertTrue(self.payload["first_divergence_original_vs_corrected_on_same_local_series"]["found"])

    def test_missing_field_blocker_declared(self):
        self.assertIn("blocker_for_direct_ea_vs_python_state_trace", self.payload)
        self.assertGreater(len(self.payload["blocker_for_direct_ea_vs_python_state_trace"]), 0)

    def test_no_new_long_run(self):
        self.assertTrue(self.payload["no_new_long_run_launched"])


class TestMinimalEpisodesIndependentOracle(unittest.TestCase):
    """Ri-esegue i 4 episodi e confronta con gli op attesi scritti a mano
    nel builder - stessa disciplina di verify_phase_7_16.py ma come test
    unitario dedicato."""

    def setUp(self):
        self.episodes = episodes_builder.build()["episodes"]

    def test_four_episodes_present(self):
        self.assertEqual(len(self.episodes), 4)

    def test_each_episode_matches_hand_derivation(self):
        for ep in self.episodes:
            dirn = 1 if ep["direction"] == "BUY" else -1
            ob_lo, ob_hi = ep["input_common"]["ob_lo"], ep["input_common"]["ob_hi"]
            bars = [ep["input_common"]["bar_shift1_bars_i"], ep["input_common"]["bar_shift0_bars_i_plus_1"]]
            atr = ep["atr_at_this_point"]
            st_o = OBState()
            st_o.active, st_o.ob_lo, st_o.ob_hi = True, ob_lo, ob_hi
            st_o.bars_waited = ep["state_initial"]["bars_waited"]
            st_o.last_bar_time = ep["state_initial"]["last_bar_time"]
            st_c = OBState()
            st_c.active, st_c.ob_lo, st_c.ob_hi = True, ob_lo, ob_hi
            st_c.bars_waited = ep["state_initial"]["bars_waited"]
            st_c.last_bar_time = ep["state_initial"]["last_bar_time"]
            curbar0 = bars[1]["open_time"]
            _, _, rec_o = ob_update_side(dirn, st_o, bars, 0, atr, curbar0)
            _, _, rec_c = ob_update_side_corrected(dirn, st_c, bars, 0, atr, curbar0)
            self.assertIn(rec_o["op"], ep["hand_derivation"]["original_expected_op"], ep["id"])
            self.assertIn(rec_c["op"], ep["hand_derivation"]["corrected_expected_op"], ep["id"])

    def test_episode_4_is_true_negative_control(self):
        ep4 = next(e for e in self.episodes if e["id"].startswith("EP4"))
        self.assertIn("RETEST_SIGNAL_FIRED", ep4["hand_derivation"]["original_expected_op"])
        self.assertIn("RETEST_SIGNAL_FIRED", ep4["hand_derivation"]["corrected_expected_op"])


class TestFidelityClassification(unittest.TestCase):
    def setUp(self):
        self.payload = classification_builder.build()

    def test_classification_in_allowed_set(self):
        self.assertIn(self.payload["classification"], self.payload["classification_allowed_values"])

    def test_order_block_validation_preserved(self):
        self.assertTrue(self.payload["order_block_pre_post_fix_validation_preserved"])

    def test_valid_uses_and_invalid_uses_both_present(self):
        vu = self.payload["valid_uses"]
        self.assertIn("mechanism_research", vu)
        self.assertIn("profitability_or_pf_estimation", vu)
        self.assertIn("MAI VALIDO", vu["profitability_or_pf_estimation"])

    def test_architectural_proposal_scoped_not_global(self):
        prop = self.payload["architectural_proposal"]
        self.assertIn("PROPOSTA METODOLOGICA", prop["scope_of_proposal"])
        self.assertIn("stateless", prop["scope_of_proposal"].lower())

    def test_single_next_action_present(self):
        self.assertIn("single_recommended_action", self.payload["next_action"])


class TestNoScopeViolations(unittest.TestCase):
    def test_no_mql5_modified(self):
        result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")

    def test_no_new_tester_ini_created(self):
        inis = [f for f in os.listdir(PHASE716_DIR) if f.endswith(".ini")]
        self.assertEqual(inis, [])

    def test_phase_7_13_and_7_14_frozen_artifacts_untouched_except_declared(self):
        # phase7_13/nxs_order_block_replica.py deve restare INVARIATO (congelato) -
        # questa fase crea SOLO una copia corretta separata, non lo modifica.
        result = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--",
            "server/research_scripts/phase7/phase7_13/nxs_order_block_replica.py"],
            cwd=ROOT)
        self.assertEqual(result.returncode, 0, "nxs_order_block_replica.py originale modificato")


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        self.assertEqual(verifier.verify(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
