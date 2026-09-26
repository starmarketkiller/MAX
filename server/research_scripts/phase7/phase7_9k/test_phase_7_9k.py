#!/usr/bin/env python3
"""Phase 7.9K - suite di test di consistenza + verifiche indipendenti
con serie piccole calcolabili A MANO (i valori attesi sono stati
calcolati manualmente PRIMA di eseguire il codice, non generati dalla
stessa funzione verificata - vedi i commenti con l'aritmetica)."""
import os
import subprocess
import sys
import unittest
from datetime import datetime

PHASE79K_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79I_DIR = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "phase7_9i"))
ROOT = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE79I_DIR)
sys.path.insert(0, PHASE79K_DIR)
import build_dataset_v2 as dataset_v2_builder  # noqa: E402
import build_decision_card_v2 as decision_builder  # noqa: E402
import build_edge_decomposition_v2 as edge_v2_builder  # noqa: E402
import build_failure_map_v2 as fmap_v2_builder  # noqa: E402
import build_gate_diagnostic_v2 as gate_v2_builder  # noqa: E402
import build_natural_horizon_v2 as horizon_v2_builder  # noqa: E402
import build_path_anatomy_v2 as path_v2_builder  # noqa: E402
import build_sensitivity_v2 as sens_v2_builder  # noqa: E402
import build_temporal_contract as contract_builder  # noqa: E402
import nxs_forward_path_v2 as fp  # noqa: E402
import verify_phase_7_9k as verifier  # noqa: E402


def _mk(t, o, h, l, c):
    return {"time": t, "open": o, "high": h, "low": l, "close": c}


# --- Serie sintetica condivisa dai test "a mano" ---
# 2024-01-01 (lun) ha H/L VOLUTAMENTE estremi (200/10): se una barra
# parziale/precedente al fill venisse mai inclusa nel calcolo, MFE/MAE
# assumerebbero questi valori sbagliati - una spia diretta del difetto.
SYNTH_BARS = [
    _mk(datetime(2024, 1, 1), 100, 200, 10, 102),   # lun - barra d'ingresso, MAI usata
    _mk(datetime(2024, 1, 2), 102, 108, 101, 106),  # mar - bar 1 (ingresso intraday)
    _mk(datetime(2024, 1, 3), 106, 107, 99, 100),   # mer - bar 2
    _mk(datetime(2024, 1, 4), 100, 120, 100, 115),  # gio - bar 3
    _mk(datetime(2024, 1, 5), 115, 116, 110, 112),  # ven - bar 4
    # weekend: 6-7 gennaio assenti dal feed (nessuna barra sintetica)
    _mk(datetime(2024, 1, 8), 112, 118, 111, 117),  # lun successivo - bar 5
]


class TestHandComputableSeries(unittest.TestCase):
    """Ogni valore atteso e' calcolato A MANO nel commento accanto
    all'assert - non generato da fp.* (che e' il codice sotto test)."""

    def test_intraday_fill_never_uses_entry_day_extremes(self):
        # Fill 2024-01-01 14:00 (intraday), BUY, reference_price=101, max_h=5.
        # bar1=2024-01-02 (idx=1, salta la barra d'ingresso del 1 gennaio).
        # A MANO: fav/adv/ret per ciascuna barra 1..5 (vedi derivazione nel
        # messaggio della task) danno MFE=19 (bar 3, 2024-01-04: 120-101),
        # MAE=2 (bar 2, 2024-01-03: 101-99), fwd(1)=5, fwd(3)=14, fwd(5)=16.
        # Se il 1 gennaio (H=200) fosse erroneamente incluso, MFE sarebbe 99
        # (200-101) invece di 19 - la spia diretta del difetto.
        entry_time = datetime(2024, 1, 1, 14, 0, 0)
        result = fp.path_anatomy_v2(SYNTH_BARS, entry_time, 101, 1,
                                    horizons=[1, 3, 5], max_h=5)
        self.assertEqual(result["status"], "FULL_COVERAGE")
        self.assertEqual(result["coverage_bars"], 5)
        self.assertEqual(result["mfe_price_units"], 19)
        self.assertEqual(result["mae_price_units"], 2)
        self.assertEqual(result["bars_to_mfe_d1"], 3)
        self.assertEqual(result["bars_to_mae_d1"], 2)
        self.assertEqual(result["horizons"]["fwd_return_1d1_price_units"], 5)
        self.assertEqual(result["horizons"]["fwd_return_3d1_price_units"], 14)
        self.assertEqual(result["horizons"]["fwd_return_5d1_price_units"], 16)
        # MFE non deve MAI raggiungere 99 (il valore che si otterrebbe includendo
        # erroneamente l'High=200 della barra d'ingresso del 1 gennaio).
        self.assertNotEqual(result["mfe_price_units"], 99)

    def test_fill_exactly_at_d1_open_uses_that_bar_as_bar_1(self):
        # Fill ESATTAMENTE all'apertura del 2024-01-03 (mercoledi'), BUY,
        # reference_price=106 (=open), max_h=3. In questo caso bar1 = LA
        # BARRA STESSA del 3 gennaio (idx punta a lei, non alla successiva),
        # perche' l'intero suo OHLC e' temporalmente >= al fill (fill=open).
        # A MANO: bar1=2024-01-03 (H107,L99,C100): fav=1,adv=7,ret=-6.
        #         bar2=2024-01-04 (H120,L100,C115): fav=14,adv=6->stays7,ret=9.
        #         bar3=2024-01-05 (H116,L110,C112): fav=10->stays14,adv=-4->stays7,ret=6.
        # MFE=14 (bar2), MAE=7 (bar1).
        entry_time = datetime(2024, 1, 3, 0, 0, 0)
        result = fp.path_anatomy_v2(SYNTH_BARS, entry_time, 106, 1,
                                    horizons=[1, 2, 3], max_h=3)
        self.assertEqual(result["status"], "FULL_COVERAGE")
        self.assertEqual(result["mfe_price_units"], 14)
        self.assertEqual(result["mae_price_units"], 7)
        self.assertEqual(result["bars_to_mfe_d1"], 2)
        self.assertEqual(result["bars_to_mae_d1"], 1)
        self.assertEqual(result["horizons"]["fwd_return_1d1_price_units"], -6)
        self.assertEqual(result["horizons"]["fwd_return_2d1_price_units"], 9)
        self.assertEqual(result["horizons"]["fwd_return_3d1_price_units"], 6)

    def test_weekend_gap_counts_market_bars_not_calendar_days(self):
        # Stessa finestra del primo test (bar1..bar5 = 2/1,3/1,4/1,5/1,8/1) -
        # "bar 5" cade il 8 gennaio (lunedi'), 3 giorni di CALENDARIO dopo il
        # 5 gennaio (venerdi'), ma e' comunque la QUINTA barra di MERCATO -
        # nessuna barra sintetica per il weekend 6-7/1.
        entry_time = datetime(2024, 1, 1, 14, 0, 0)
        curve_doc = fp.build_forward_curve_v2(SYNTH_BARS, entry_time, 101, 1, max_h=5)
        self.assertEqual(len(curve_doc["curve"]), 5)
        self.assertEqual(curve_doc["curve"][-1]["bar"], 5)
        # bar 5 usa la barra dell'8 gennaio (close=117): ret = 117-101 = 16.
        self.assertEqual(curve_doc["curve"][-1]["close_to_close_return"], 16)

    def test_insufficient_future_bars_is_censored_not_failure(self):
        # Stesso ingresso, ma max_h=10 con solo 5 barre disponibili nella serie
        # sintetica - l'orizzonte 10 DEVE essere censurato (None), MAI un
        # valore forzato o interpretato come FAILURE.
        entry_time = datetime(2024, 1, 1, 14, 0, 0)
        result = fp.path_anatomy_v2(SYNTH_BARS, entry_time, 101, 1,
                                    horizons=[5, 10], max_h=10)
        self.assertEqual(result["status"], "CENSORED_INSUFFICIENT_BARS")
        self.assertEqual(result["coverage_bars"], 5)
        self.assertEqual(result["horizons"]["fwd_return_5d1_price_units"], 16)  # ancora valido
        self.assertIsNone(result["horizons"]["fwd_return_10d1_price_units"])  # censurato
        self.assertIn(10, result["horizons_censored"])
        self.assertNotIn(5, result["horizons_censored"])
        cls = fp.classify_continuation_failure_v2(result, 10)
        self.assertEqual(cls, "UNKNOWN_CENSORED")  # MAI "FAILURE" per un orizzonte censurato

    def test_no_bars_available_returns_explicit_status(self):
        entry_time = datetime(2030, 1, 1)  # ben oltre l'ultima barra sintetica
        result = fp.path_anatomy_v2(SYNTH_BARS, entry_time, 100, 1, max_h=5)
        self.assertEqual(result["status"], "NO_BARS_AVAILABLE")
        self.assertEqual(result["coverage_bars"], 0)

    def test_sell_direction_mirrors_buy_logic(self):
        # Stessa serie, direzione SELL: fav/adv si scambiano di ruolo.
        # bar1=2024-01-02 (H108,L101,C106), reference_price=101, SELL:
        # fav = ref-L = 101-101=0, adv = H-ref = 108-101=7, ret = ref-C = 101-106=-5.
        entry_time = datetime(2024, 1, 1, 14, 0, 0)
        result = fp.path_anatomy_v2(SYNTH_BARS, entry_time, 101, -1,
                                    horizons=[1], max_h=1)
        self.assertEqual(result["mfe_price_units"], 0)
        self.assertEqual(result["mae_price_units"], 7)
        self.assertEqual(result["horizons"]["fwd_return_1d1_price_units"], -5)


class TestMeasurementConventionEquivalence(unittest.TestCase):
    """Le misurazioni A e B devono passare per la STESSA funzione
    (nessuna doppia implementazione che potrebbe divergere)."""

    def test_measurement_a_and_b_use_same_underlying_function(self):
        import inspect
        src_a = inspect.getsource(fp.measurement_a_reference)
        src_module = inspect.getsource(fp)
        # entrambe le misurazioni vengono poi passate a path_anatomy_v2 dai builder -
        # verificato staticamente che non esista una seconda implementazione parallela
        # di build_forward_curve_v2 nel modulo.
        self.assertEqual(src_module.count("def build_forward_curve_v2("), 1)
        self.assertEqual(src_module.count("def path_anatomy_v2("), 1)


class TestDeterminism(unittest.TestCase):
    def _check(self, fname, build_fn):
        saved = load_json(os.path.join(PHASE79K_DIR, fname))
        fresh = build_fn()
        self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(fresh))

    def test_temporal_contract_deterministic(self):
        self._check("breakout_acc_temporal_contract_v1.json", contract_builder.build)

    def test_dataset_v2_deterministic(self):
        self._check("breakout_acc_intended_d1_v2_dataset.json", dataset_v2_builder.build)

    def test_path_anatomy_v2_deterministic(self):
        self._check("breakout_acc_path_anatomy_v2.json", path_v2_builder.build)

    def test_natural_horizon_v2_deterministic(self):
        self._check("breakout_acc_natural_horizon_v2.json", horizon_v2_builder.build)

    def test_edge_decomposition_v2_deterministic(self):
        self._check("breakout_acc_edge_decomposition_v2.json", edge_v2_builder.build)

    def test_gate_diagnostic_v2_deterministic(self):
        self._check("breakout_acc_gate_diagnostic_v2.json", gate_v2_builder.build)

    def test_sensitivity_v2_deterministic(self):
        self._check("breakout_acc_sensitivity_v2.json", sens_v2_builder.build)

    def test_failure_map_v2_deterministic(self):
        self._check("breakout_acc_failure_map_v2.json", fmap_v2_builder.build)

    def test_decision_card_v2_deterministic(self):
        self._check("breakout_acc_decision_card_v2.json", decision_builder.build)


class TestDatasetV2Identity(unittest.TestCase):
    def setUp(self):
        self.payload = dataset_v2_builder.build()

    def test_dataset_name_unchanged(self):
        self.assertEqual(self.payload["dataset_name"], "BREAKOUT_ACC_INTENDED_D1_V1")

    def test_schema_version_is_v2(self):
        self.assertEqual(self.payload["dataset_schema_version"], "V2")

    def test_supersedes_v1_by_hash(self):
        v1 = load_json(os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_9h",
                                    "breakout_acc_intended_d1_v1_dataset.json"))
        self.assertEqual(self.payload["supersedes_sha256"], v1["canonical_sha256"])

    def test_event_ids_conserved_from_v1(self):
        v1 = load_json(os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_9h",
                                    "breakout_acc_intended_d1_v1_dataset.json"))
        v1_ids = {e["event_id"] for e in v1["payload"]["events"]}
        v2_ids = {e["event_id"] for e in self.payload["events"]}
        self.assertEqual(v1_ids, v2_ids)

    def test_funnel_fields_unchanged_from_v1(self):
        v1 = load_json(os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_9h",
                                    "breakout_acc_intended_d1_v1_dataset.json"))
        v1_by_id = {e["event_id"]: e for e in v1["payload"]["events"]}
        for e in self.payload["events"]:
            v1e = v1_by_id[e["event_id"]]
            self.assertEqual(e["funnel_terminal_stage"], v1e["funnel_terminal_stage"])
            self.assertEqual(e.get("entry_fill_price"), v1e.get("entry_fill_price"))
            self.assertEqual(e.get("realized_pnl"), v1e.get("realized_pnl"))

    def test_measurement_a_present_for_all_75(self):
        self.assertEqual(len(self.payload["events"]), 75)
        for e in self.payload["events"]:
            self.assertIn("measurement_A_post_signal_path", e)

    def test_measurement_b_only_for_opened(self):
        for e in self.payload["events"]:
            if e["funnel_terminal_stage"] == "OPENED":
                self.assertNotEqual(e["measurement_B_post_fill_path"]["status"],
                                    "NOT_APPLICABLE_NOT_OPENED")
            else:
                self.assertEqual(e["measurement_B_post_fill_path"]["status"],
                                 "NOT_APPLICABLE_NOT_OPENED")

    def test_synthetic_timestamps_labeled_explicitly(self):
        for e in self.payload["events"]:
            if e["population_source"] == "OFFLINE_ISOLATED_RECONSTRUCTION_ONLY":
                self.assertEqual(
                    e["measurement_A_post_signal_path"]["reference_timestamp_source"],
                    "SYNTHETIC_NOT_OBSERVED_NOON_PLACEHOLDER")
            elif e["population_source"] == "LIVE_TRACE_GENERATED":
                self.assertEqual(
                    e["measurement_A_post_signal_path"]["reference_timestamp_source"],
                    "REAL_SIGNAL_TIMESTAMP_FROM_LIVE_TRACE")


class TestBeforeAfterComparison(unittest.TestCase):
    def setUp(self):
        self.payload = path_v2_builder.build()

    def test_reclassification_count_reported(self):
        self.assertIn("n_reclassified_continuation_failure",
                      self.payload["aggregate_before_after"])
        self.assertGreaterEqual(
            self.payload["aggregate_before_after"]["n_reclassified_continuation_failure"], 0)

    def test_censored_events_excluded_from_denominator(self):
        by_dir = self.payload["by_direction_continuation_before_after"]
        for d in ("BUY", "SELL"):
            self.assertEqual(by_dir[d]["denominator_v2_excludes_censored"],
                             by_dir[d]["n"] - by_dir[d]["n_censored_v2"])

    def test_per_event_has_both_v1_and_v2_fields(self):
        for p in self.payload["per_event_before_after"]:
            self.assertIn("v1_mfe", p)
            self.assertIn("v2_mfe", p)
            self.assertIn("v1_classification", p)
            self.assertIn("v2_classification", p)


class TestDecisionCardV2(unittest.TestCase):
    def setUp(self):
        self.payload = decision_builder.build()

    def test_final_decision_allowed(self):
        self.assertIn(self.payload["final_decision"], self.payload["final_decision_allowed_values"])

    def test_reevaluation_note_present_and_explicit(self):
        self.assertIn("RIVALUTATO", self.payload["reevaluation_note"])

    def test_ema100_precision_distinguishes_72_from_3(self):
        prec = self.payload["ema100_precision"]
        self.assertEqual(prec["n_evaluable_for_ema100"], 72)
        self.assertEqual(prec["n_not_evaluable_insufficient_warmup"], 3)
        self.assertTrue(prec["not_evaluable_are_all_in_b_only"])

    def test_alignment_not_treated_as_proof(self):
        text = self.payload["ema100_precision"]["alignment_constant_interpretation"]
        self.assertIn("NON E' IDENTIFICABILE", text)

    def test_no_forbidden_words(self):
        import json
        text = json.dumps(self.payload, ensure_ascii=False).upper()
        for w in ("PROMOTE", "DEPLOY", "PROFITABLE"):
            self.assertNotIn(w, text)


class TestFrozenAssetsUntouched(unittest.TestCase):
    def test_phase_7_9h_dataset_not_modified(self):
        dataset_path = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_9h",
                                    "breakout_acc_intended_d1_v1_dataset.json")
        result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", dataset_path], cwd=ROOT)
        self.assertEqual(result.returncode, 0)

    def test_phase_7_9i_and_7_9j_not_modified(self):
        for rel in ("server/research_scripts/phase7/phase7_9i",
                   "server/research_scripts/phase7/phase7_9j"):
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
