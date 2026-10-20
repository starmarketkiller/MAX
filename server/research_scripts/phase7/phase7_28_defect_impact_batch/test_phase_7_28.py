#!/usr/bin/env python3
"""Phase 7.28 integrity tests — guards present + measured artifacts coherent."""
from __future__ import annotations

import json
import os
import unittest

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))


class Phase728Tests(unittest.TestCase):
    def test_bar_updn_material(self):
        p = json.load(open(os.path.join(PHASE_DIR, "bar_updn_abc_impact_v1.json"), encoding="utf-8"))
        self.assertEqual(p["payload"]["decision"], "DEFECT_CONFIRMED_MATERIAL_IMPACT")
        self.assertGreater(p["payload"]["stream_B_tf_scoped_signals"], p["payload"]["stream_A_contaminated_signals_on_profile_pass"])

    def test_bb_squeeze_artifact(self):
        p = json.load(open(os.path.join(PHASE_DIR, "bb_squeeze_abc_impact_v1.json"), encoding="utf-8"))
        self.assertIn(p["payload"]["decision"], {
            "DEFECT_CONFIRMED_LOW_IMPACT",
            "DEFECT_CONFIRMED_MATERIAL_IMPACT",
            "INSUFFICIENT_EVIDENCE",
        })

    def test_guards_in_source(self):
        cases = [
            ("NXS_Strategies.mqh", 'NXS_Profile_TF("BAR_UPDN")'),
            ("NXS_Strategies.mqh", 'NXS_Profile_TF("PMAX")'),
            ("NXS_Strategies.mqh", 'NXS_Profile_TF("PIVOT_WICK")'),
            ("NXS_Strategies.mqh", 'NXS_Profile_TF("BB_SQUEEZE")'),
            ("NXS_Strategies.mqh", 'NXS_Profile_TF("TSI")'),
            ("NXS_Strategies_SMC.mqh", 'NXS_Profile_TF("SH_BMS_RTO")'),
            ("NXS_Strategies_SMC.mqh", 'NXS_Profile_TF("SH_BMS_RTO_V2")'),
            ("NXS_Strategies_SMC.mqh", 'NXS_Profile_TF("SILVER_BULLET")'),
            ("NXS_Strategies_Institutional.mqh", 'NXS_Profile_TF("RANGE_FADE")'),
            ("NXS_StrategyProfiles.mqh", 'name == "SILVER_BULLET"'),
        ]
        for fname, needle in cases:
            text = open(os.path.join(ROOT, "MQL5/Include/NEXUS_v1", fname), encoding="utf-8").read()
            self.assertIn(needle, text, msg=f"missing {needle} in {fname}")

    def test_decision_batch_guards_ok(self):
        d = json.load(open(os.path.join(PHASE_DIR, "defect_impact_batch_decision_v1.json"), encoding="utf-8"))
        self.assertTrue(all(d["payload"]["structural_guard_applied"].values()))
        self.assertTrue(d["payload"]["silver_bullet_profile_tf_fixed"])


if __name__ == "__main__":
    unittest.main()
