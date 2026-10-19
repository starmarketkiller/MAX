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


if __name__ == "__main__":
    unittest.main()
