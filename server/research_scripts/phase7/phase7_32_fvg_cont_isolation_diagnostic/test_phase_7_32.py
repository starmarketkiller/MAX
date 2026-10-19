#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import unittest

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))


class Phase732Tests(unittest.TestCase):
    def test_prereg(self):
        with open(os.path.join(PHASE_DIR, "preregistration_v1.json"), encoding="utf-8") as f:
            p = json.load(f)["payload"]
        self.assertEqual(p["hypothesis_id"], "FVG-CONT-MT5-ISOLATION-DIAG-001")
        self.assertEqual(p["params"]["selector"], 8)
        self.assertEqual(p["params"]["period_from"], "2023.10.02")
        self.assertIn("SAMPLE_READY_FOR_EDGE_PREREG", p["allowed_decisions"])

    def test_prereg_guard(self):
        import sys
        sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7"))
        from engine.preregistration_provenance_guard import assert_frozen_spec_committed_before_run
        sha = assert_frozen_spec_committed_before_run(
            ROOT,
            "server/research_scripts/phase7/phase7_32_fvg_cont_isolation_diagnostic/preregistration_v1.json",
        )
        self.assertTrue(len(sha) >= 7)

    def test_status_prepared(self):
        path = os.path.join(PHASE_DIR, "diagnostic_run_status_v1.json")
        self.assertTrue(os.path.isfile(path))
        with open(path, encoding="utf-8") as f:
            s = json.load(f)
        self.assertEqual(s["status"], "PREPARED_AWAITING_WINDOWS_MT5")
        self.assertEqual(s["hypothesis_id"], "FVG-CONT-MT5-ISOLATION-DIAG-001")

    def test_analyze_early(self):
        import sys
        if PHASE_DIR not in sys.path:
            sys.path.insert(0, PHASE_DIR)
        from analyze_diagnostic_run import analyze
        p = analyze()
        self.assertEqual(p["decision"], "INSUFFICIENT_SAMPLE")
        self.assertFalse(p["promotable"])


if __name__ == "__main__":
    unittest.main()
