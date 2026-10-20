#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import unittest

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))


class Phase734Tests(unittest.TestCase):
    def test_scripts_exist(self):
        for name in (
            "launch_confirmatory_forward_run.py",
            "collect_confirmatory_forward_run.py",
            "analyze_confirmatory_forward.py",
            "RUNBOOK_CONFIRMATORY_WINDOWS.md",
        ):
            self.assertTrue(os.path.isfile(os.path.join(PHASE_DIR, name)), name)

    def test_uses_frozen_733_prereg(self):
        import sys
        sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7"))
        from engine.preregistration_provenance_guard import assert_frozen_spec_committed_before_run
        sha = assert_frozen_spec_committed_before_run(
            ROOT,
            "server/research_scripts/phase7/phase7_33_fvg_cont_habitat/preregistration_v1.json",
        )
        self.assertTrue(len(sha) >= 7)
        with open(
            os.path.join(ROOT, "server/research_scripts/phase7/phase7_33_fvg_cont_habitat/preregistration_v1.json"),
            encoding="utf-8",
        ) as f:
            p = json.load(f)["payload"]
        self.assertEqual(p["hypothesis_id"], "FVG-CONT-HABITAT-RM-001")

    def test_status_prepared(self):
        path = os.path.join(PHASE_DIR, "confirmatory_run_status_v1.json")
        self.assertTrue(os.path.isfile(path))
        with open(path, encoding="utf-8") as f:
            s = json.load(f)
        self.assertEqual(s["status"], "PREPARED_AWAITING_WINDOWS_MT5")
        self.assertEqual(s["period"], ["2026.07.01", "2026.10.19"])
        self.assertEqual(s["hypothesis_id"], "FVG-CONT-HABITAT-RM-001")

    def test_analyze_early(self):
        import sys
        if PHASE_DIR not in sys.path:
            sys.path.insert(0, PHASE_DIR)
        from analyze_confirmatory_forward import analyze
        d1 = os.path.join(
            ROOT,
            "server/research_scripts/phase7/phase7_30_liq_sweep_buy_trend/runs/"
            "liq_sweep_confirmatory_forward/nxs_d1_gold_refresh_20261019.csv",
        )
        p = analyze(d1)
        self.assertEqual(p["decision"], "INSUFFICIENT_EVIDENCE")
        self.assertFalse(p["live_ready"])


if __name__ == "__main__":
    unittest.main()
