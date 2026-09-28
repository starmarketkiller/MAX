#!/usr/bin/env python3
"""Phase 7.26 - suite di test: determinismo di tutti i registry, regole
di leakage, engine riusabili (path anatomy, pre-entry feature store,
matched non-event, visual audit), sintesi cross-strategy, priority
queue, multiple testing registry, verificatore, nessuna violazione di
perimetro."""
import os
import sys
import unittest
from datetime import datetime

PHASE726_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE726_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE726_DIR)
import build_data_exposure_registry as exposure_builder  # noqa: E402
import build_experiment_registry as experiment_builder  # noqa: E402
import build_hypothesis_registry as hypothesis_builder  # noqa: E402
import build_failure_map as failure_builder  # noqa: E402
import build_cross_strategy_learning_packet as packet_builder  # noqa: E402
import build_cross_strategy_synthesis as synthesis_builder  # noqa: E402
import build_research_priority_queue as priority_builder  # noqa: E402
import build_multiple_testing_registry as mtr_builder  # noqa: E402
import verify_leakage  # noqa: E402
import verify_phase_7_26 as verifier  # noqa: E402
from nxs_schemas import (DATA_EXPOSURE_REQUIRED_FIELDS, EXPERIMENT_REQUIRED_FIELDS,  # noqa: E402
                        HYPOTHESIS_REQUIRED_FIELDS, LEARNING_PACKET_REQUIRED_FIELDS,
                        FAILURE_MODE_TAXONOMY, missing_required, NOT_AVAILABLE)
from nxs_pre_entry_feature_store import make_feature, FeatureLeakageError, verify_feature_set_causal  # noqa: E402
from nxs_matched_non_event_builder import (select_matched_non_event, select_near_miss,  # noqa: E402
                                           verify_no_outcome_fields_used)
from nxs_path_anatomy_engine import PathAnatomyEvent, compute_path_metrics, build_event_report  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_25"))
from nxs_liq_sweep_edge_dataset_loader import m15_slice, resample_ohlc  # noqa: E402
from nxs_visual_audit_engine import render_event_stages  # noqa: E402

ARTIFACTS = [
    ("data_exposure_registry_v1.json", lambda: exposure_builder.build()[0]),
    ("experiment_registry_v1.json", experiment_builder.build),
    ("hypothesis_registry_v1.json", hypothesis_builder.build),
    ("failure_map_v1.json", failure_builder.build),
    ("cross_strategy_learning_packets_v1.json", packet_builder.build),
    ("cross_strategy_synthesis_v1.json", synthesis_builder.build),
    ("research_priority_queue_v1.json", priority_builder.build),
    ("multiple_testing_registry_v1.json", mtr_builder.build),
]


class TestDeterminism(unittest.TestCase):
    def test_all_artifacts_deterministic(self):
        for fname, build_fn in ARTIFACTS:
            saved = load_json(os.path.join(PHASE726_DIR, fname))
            self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(build_fn()), fname)


class TestDataExposureRegistry(unittest.TestCase):
    def test_all_records_have_required_fields(self):
        payload, _ = exposure_builder.build()
        for r in payload["records"]:
            self.assertEqual(missing_required(r, DATA_EXPOSURE_REQUIRED_FIELDS), [])

    def test_4_strategies_backfilled(self):
        payload, _ = exposure_builder.build()
        self.assertEqual(set(payload["backfilled_strategies"]),
                        {"BREAKOUT_ACC", "ORDER_BLOCK", "TSI", "LIQ_SWEEP"})

    def test_is_genuinely_untouched_query(self):
        payload, by_id = exposure_builder.build()
        self.assertFalse(exposure_builder.is_genuinely_untouched("LIQ_SWEEP::2023.10.02_2026.06.30", by_id))
        self.assertIsNone(exposure_builder.is_genuinely_untouched("NONEXISTENT::X", by_id))


class TestExperimentRegistry(unittest.TestCase):
    def test_all_experiments_have_required_fields(self):
        payload = experiment_builder.build()
        for e in payload["experiments"]:
            self.assertEqual(missing_required(e, EXPERIMENT_REQUIRED_FIELDS), [])

    def test_no_experiment_orphaned_hypothesis(self):
        hyp_ids = {h["hypothesis_id"] for h in hypothesis_builder.build()["hypotheses"]}
        for e in experiment_builder.build()["experiments"]:
            self.assertIn(e["hypothesis_id"], hyp_ids)

    def test_no_experiment_orphaned_dataset(self):
        _, by_id = exposure_builder.build()
        for e in experiment_builder.build()["experiments"]:
            self.assertIn(e["dataset_id"], by_id)


class TestHypothesisRegistry(unittest.TestCase):
    def test_all_lifecycle_states_valid(self):
        from nxs_schemas import HYPOTHESIS_LIFECYCLE_STATES
        for h in hypothesis_builder.build()["hypotheses"]:
            self.assertIn(h["lifecycle_state"], HYPOTHESIS_LIFECYCLE_STATES)

    def test_discovery_validation_separation_enforced(self):
        errors = verify_leakage.verify_hypothesis_discovery_validation_separation()
        self.assertEqual(errors, [])

    def test_h2_buy_sell_asymmetry_is_post_hoc_not_validated(self):
        hyp = {h["hypothesis_id"]: h for h in hypothesis_builder.build()["hypotheses"]}
        h2 = hyp["H2_BREAKOUT_ACC_BUY_MORE_ROBUST_THAN_SELL"]
        self.assertIn(h2["lifecycle_state"], ("HYPOTHESIS", "TESTING", "INCONCLUSIVE"))
        self.assertNotIn(h2["lifecycle_state"], ("SUPPORTED", "REJECTED"))


class TestFailureMap(unittest.TestCase):
    def test_all_tags_in_taxonomy(self):
        payload = failure_builder.build()
        for strat, d in payload["strategies"].items():
            for t in d["failure_modes"]:
                self.assertIn(t["mode"], FAILURE_MODE_TAXONOMY)

    def test_tsi_has_no_economic_failure_modes(self):
        payload = failure_builder.build()
        tsi_modes = [t["mode"] for t in payload["strategies"]["TSI"]["failure_modes"]]
        self.assertEqual(tsi_modes, ["IMPLEMENTATION_DEFECT"])


class TestLearningPackets(unittest.TestCase):
    def test_all_4_strategies_present(self):
        payload = packet_builder.build()
        self.assertEqual(set(payload["packets"].keys()),
                        {"BREAKOUT_ACC", "ORDER_BLOCK", "TSI", "LIQ_SWEEP"})

    def test_all_required_fields_present_per_packet(self):
        payload = packet_builder.build()
        for strat, packet in payload["packets"].items():
            self.assertEqual(missing_required(packet, LEARNING_PACKET_REQUIRED_FIELDS), [], strat)

    def test_tsi_packet_mostly_not_available(self):
        payload = packet_builder.build()
        tsi = payload["packets"]["TSI"]
        self.assertEqual(tsi["mfe_mae"], NOT_AVAILABLE)
        self.assertEqual(tsi["concentration"], NOT_AVAILABLE)


class TestCrossStrategySynthesis(unittest.TestCase):
    def test_no_edge_found_verdicts(self):
        errors = verify_leakage.verify_synthesis_never_declares_edge_found()
        self.assertEqual(errors, [])

    def test_at_least_one_cross_strategy_pattern_found(self):
        payload = synthesis_builder.build()
        kinds = [f["kind"] for f in payload["findings"]]
        self.assertIn("CROSS_STRATEGY_PATTERN", kinds)

    def test_tsi_excluded_from_economic_comparison(self):
        payload = synthesis_builder.build()
        self.assertNotIn("TSI", payload["strategies_included"])


class TestResearchPriorityQueue(unittest.TestCase):
    def test_pf_not_a_criterion(self):
        payload = priority_builder.build()
        for c in payload["criteria_declared_before_scoring"]:
            self.assertNotIn("profit_factor", c.lower())
            self.assertNotIn("pf", c.lower().split("_"))
        self.assertTrue(payload["pf_explicitly_not_a_criterion"])

    def test_ranked_descending(self):
        payload = priority_builder.build()
        scores = [c["total_score_unweighted"] for c in payload["ranked_candidates"]]
        self.assertEqual(scores, sorted(scores, reverse=True))


class TestMultipleTestingRegistry(unittest.TestCase):
    def test_counts_present_and_consistent(self):
        payload = mtr_builder.build()
        self.assertEqual(payload["n_hypotheses_tested"],
                        hypothesis_builder.build()["n_hypotheses"])
        self.assertFalse(payload["no_p_value_correction_applied_this_phase"] is not True)


class TestPreEntryFeatureStore(unittest.TestCase):
    def test_valid_feature_accepted(self):
        f = make_feature(value=1.0, source="x", timestamp=datetime(2026, 1, 1),
                         availability_time=datetime(2026, 1, 1), timeframe="D1",
                         forming_or_closed_bar="CLOSED", fidelity="EVENT_LEVEL_FAITHFUL",
                         decision_timestamp=datetime(2026, 1, 2))
        self.assertTrue(f["causal_verified"])

    def test_future_feature_rejected(self):
        with self.assertRaises(FeatureLeakageError):
            make_feature(value=1.0, source="x", timestamp=datetime(2026, 1, 3),
                        availability_time=datetime(2026, 1, 3), timeframe="D1",
                        forming_or_closed_bar="CLOSED", fidelity="EVENT_LEVEL_FAITHFUL",
                        decision_timestamp=datetime(2026, 1, 2))

    def test_verify_feature_set_causal_catches_missing_fields(self):
        errors = verify_feature_set_causal([{"source": "bad"}], datetime(2026, 1, 2))
        self.assertTrue(errors)


class TestMatchedNonEventBuilder(unittest.TestCase):
    def test_no_outcome_fields_referenced(self):
        self.assertEqual(verify_no_outcome_fields_used(), [])

    def test_select_matched_non_event_uses_only_timing(self):
        events = [
            {"entry_time": "2024.01.01 00:00:00", "exit_time": "2024.01.02 00:00:00"},
            {"entry_time": "2024.02.01 00:00:00", "exit_time": "2024.02.02 00:00:00"},
        ]
        control_dt, rule_note, evidence = select_matched_non_event(events)
        self.assertIsInstance(control_dt, datetime)
        self.assertIn("gap_days", evidence)

    def test_select_near_miss_declares_gap_when_empty(self):
        result = select_near_miss([])
        self.assertEqual(result["status"], "GAP_DICHIARATO_NON_FABBRICATO")


class TestPathAnatomyEngine(unittest.TestCase):
    def test_censored_event_flagged(self):
        e = PathAnatomyEvent(event_id="e1", direction="BUY", entry_time=datetime(2026, 1, 1),
                            exit_time=None, signal_price=100.0, planned_sl=95.0,
                            censored=True, censor_reason="still open")
        report = build_event_report(e, [], [], actual_pnl=None)
        self.assertTrue(report["censored"])

    def test_signal_vs_fill_relative_separated(self):
        e = PathAnatomyEvent(event_id="e2", direction="BUY", entry_time=datetime(2026, 1, 1),
                            exit_time=datetime(2026, 1, 2), signal_price=100.0,
                            fill_price=100.5, planned_sl=95.0)
        bars = [{"time": datetime(2026, 1, 1, 12), "high": 102.0, "low": 99.0}]
        report = build_event_report(e, bars, bars, actual_pnl=50.0)
        self.assertTrue(report["signal_relative"]["data_available"])
        self.assertTrue(report["fill_relative"]["data_available"])
        self.assertNotEqual(report["signal_relative"]["ref_price"], report["fill_relative"]["ref_price"])


class TestVisualAuditEngine(unittest.TestCase):
    def test_renders_real_svg_for_synthetic_event(self):
        import tempfile
        event = {"event_id": "test_evt", "direction": "BUY", "entry_time": datetime(2024, 3, 5, 16, 15),
                "exit_time": datetime(2024, 3, 8, 19, 5), "signal_reference_price": 2150.0,
                "planned_sl": 2140.0, "planned_tp": 2170.0, "exit_reason": "tp", "actual_pnl": 55.5}
        with tempfile.TemporaryDirectory() as d:
            result = render_event_stages(event, m15_slice, resample_ohlc, d, "EVENT_LEVEL_FAITHFUL")
            self.assertTrue(result["data_available"])
            self.assertFalse(result["censored"])
            self.assertEqual(set(result["files"].keys()), {"stage_A", "stage_B", "stage_C"})
            for stage_files in result["files"].values():
                for p in stage_files.values():
                    self.assertTrue(os.path.exists(p))

    def test_missing_price_returns_not_available_no_file_written(self):
        import tempfile
        event = {"event_id": "no_price", "direction": "BUY", "entry_time": datetime(2024, 3, 5),
                "exit_time": datetime(2024, 3, 8), "signal_reference_price": None}
        with tempfile.TemporaryDirectory() as d:
            result = render_event_stages(event, m15_slice, resample_ohlc, d, "NA")
            self.assertFalse(result["data_available"])
            self.assertEqual(os.listdir(d), [])


class TestNoScopeViolations(unittest.TestCase):
    def test_no_mql5_product_platform_changes(self):
        import subprocess
        result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                                "contracts/"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")

    def test_prior_phases_untouched(self):
        import subprocess
        for phase_dir in verifier.FROZEN_PHASE_DIRS:
            result = subprocess.run(["git", "diff", "--name-only", "--",
                                    f"server/research_scripts/phase7/{phase_dir}"],
                                   cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.stdout.strip(), "", phase_dir)


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        self.assertEqual(verifier.verify(), [])

    def test_leakage_verifier_reports_zero_errors(self):
        self.assertEqual(verify_leakage.verify(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
