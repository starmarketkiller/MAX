#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import unittest

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Phase729Tests(unittest.TestCase):
    def test_failure_mode_card(self):
        with open(os.path.join(PHASE_DIR, "liq_sweep_oos_failure_mode_v1.json"), encoding="utf-8") as f:
            p = json.load(f)["payload"]
        self.assertEqual(p["decision"], "FAILURE_MODE_IDENTIFIED_REGIME_CONDITIONAL")
        self.assertIn("H1_HABITAT_REGIME", p["primary_failure_mode"])
        hyps = {h["id"]: h for h in p["hypotheses"]}
        self.assertTrue(hyps["H1_HABITAT_REGIME"]["supported"])
        self.assertTrue(hyps["H2_SETUP_MIX_SHIFT"]["supported"])
        self.assertTrue(hyps["H3_EXECUTION_BUG"]["rejected"])
        self.assertEqual(p["windows"]["OOS"]["stats"]["n"], 6)
        self.assertLess(p["windows"]["OOS"]["stats"]["mean_R"], 0)

    def test_decision_card(self):
        with open(os.path.join(PHASE_DIR, "liq_sweep_oos_failure_decision_card_v1.json"), encoding="utf-8") as f:
            p = json.load(f)["payload"]
        self.assertTrue(p["not_ready_for_deploy"])
        self.assertIn("H3_EXECUTION_BUG", p["rejected_hypotheses"])


if __name__ == "__main__":
    unittest.main()
