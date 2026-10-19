#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import unittest

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))


class Phase730Tests(unittest.TestCase):
    def test_prereg_frozen_fields(self):
        with open(os.path.join(PHASE_DIR, "preregistration_v1.json"), encoding="utf-8") as f:
            p = json.load(f)["payload"]
        self.assertEqual(p["hypothesis_id"], "LIQ-SWEEP-BUY-TREND-RM-001")
        self.assertTrue(p["frozen_before_any_arm_result"])
        self.assertIn("SIGNAL_SUPPORTED_AS_HYPOTHESIS", p["allowed_decisions"])
        self.assertEqual(p["params"]["random_seed"], 73001)

    def test_prereg_provenance_guard(self):
        import sys
        sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7"))
        from engine.preregistration_provenance_guard import assert_frozen_spec_committed_before_run
        sha = assert_frozen_spec_committed_before_run(
            ROOT, "server/research_scripts/phase7/phase7_30_liq_sweep_buy_trend/preregistration_v1.json"
        )
        self.assertTrue(len(sha) >= 7)

    def test_exploratory_not_promotable(self):
        with open(os.path.join(PHASE_DIR, "exploratory_replay_result_v1.json"), encoding="utf-8") as f:
            p = json.load(f)["payload"]
        self.assertFalse(p["promotable"])
        self.assertEqual(p["evidence_grade"], "DISCOVERY_REUSE")
        self.assertEqual(p["run_mode"], "EXPLORATORY_REPLAY_ON_EXPOSED_DATA")
        self.assertGreaterEqual(p["arm_B_buy_trend_recipe_R"]["n"], 1)

    def test_decision_card(self):
        with open(os.path.join(PHASE_DIR, "decision_card_v1.json"), encoding="utf-8") as f:
            p = json.load(f)["payload"]
        self.assertFalse(p["promotable"])
        self.assertTrue(p["not_ready_for_deploy"])

    def test_confirmatory_scripts_exist(self):
        for name in (
            "launch_confirmatory_forward_run.py",
            "collect_confirmatory_forward_run.py",
            "analyze_confirmatory_forward.py",
            "RUNBOOK_CONFIRMATORY_WINDOWS.md",
        ):
            self.assertTrue(
                os.path.isfile(os.path.join(PHASE_DIR, name)), f"missing {name}"
            )

    def test_confirmatory_status_prepared(self):
        path = os.path.join(PHASE_DIR, "confirmatory_run_status_v1.json")
        self.assertTrue(os.path.isfile(path), "run launch --prepare-only first")
        with open(path, encoding="utf-8") as f:
            s = json.load(f)
        self.assertIn(
            s["status"],
            (
                "PREPARED_AWAITING_WINDOWS_MT5",
                "LAUNCHED",
                "COLLECTED",
                "ANALYZED",
                "ANALYZED_D1_COVERAGE_INCOMPLETE",
                "TRADES_CSV_MISSING",
            ),
        )
        if s["status"] == "PREPARED_AWAITING_WINDOWS_MT5":
            self.assertEqual(s["hypothesis_id"], "LIQ-SWEEP-BUY-TREND-RM-001")
            self.assertEqual(s["period"], ["2026.09.28", "2026.10.19"])
        elif s.get("hypothesis_id"):
            self.assertEqual(s["hypothesis_id"], "LIQ-SWEEP-BUY-TREND-RM-001")

    def test_analyze_before_collect_is_insufficient(self):
        import sys
        if PHASE_DIR not in sys.path:
            sys.path.insert(0, PHASE_DIR)
        from analyze_confirmatory_forward import analyze
        d1 = os.path.join(
            ROOT, "server/research_scripts/phase7/phase7_9h/raw_data/nxs_d1_gold_phase79h.csv"
        )
        p = analyze(d1)
        self.assertIn(
            p["status"],
            (
                "RUN_NOT_YET_COLLECTED",
                "RUN_NOT_YET_PREPARED",
                "TRADES_CSV_MISSING",
                "ANALYZED",
                "ANALYZED_D1_COVERAGE_INCOMPLETE",
            ),
        )
        self.assertEqual(p["decision"], "INSUFFICIENT_EVIDENCE")
        self.assertFalse(p.get("live_ready", False))


if __name__ == "__main__":
    unittest.main()
