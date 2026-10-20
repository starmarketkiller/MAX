#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import unittest

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))


class Phase731Tests(unittest.TestCase):
    def test_prereg_frozen(self):
        with open(os.path.join(PHASE_DIR, "preregistration_v1.json"), encoding="utf-8") as f:
            p = json.load(f)["payload"]
        self.assertEqual(p["hypothesis_id"], "FVG-CONT-IDENTITY-ISOLATION-001")
        self.assertTrue(p["frozen_before_any_arm_result"])
        self.assertIn("ISOLATION_READY", p["allowed_decisions"])
        self.assertEqual(p["params"]["canonical_selector"], 8)

    def test_prereg_provenance_guard(self):
        import sys
        sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7"))
        from engine.preregistration_provenance_guard import assert_frozen_spec_committed_before_run
        sha = assert_frozen_spec_committed_before_run(
            ROOT,
            "server/research_scripts/phase7/phase7_31_fvg_cont_identity/preregistration_v1.json",
        )
        self.assertTrue(len(sha) >= 7)

    def test_identity_and_decision(self):
        with open(os.path.join(PHASE_DIR, "fvg_cont_identity_map_v1.json"), encoding="utf-8") as f:
            m = json.load(f)["payload"]
        self.assertEqual(m["canonical_strategy_identity"], "FVG_CONT")
        self.assertTrue(m["python_parity_flags"]["exit_mismatch"]["forbid_python_pf_as_evidence"])
        variants = {v["stratName"]: v for v in m["variants_sharing_enum_STRAT_FVG_CONT"]}
        self.assertEqual(variants["FVG_MIT_WINDOW"]["dependency_class"], "SEPARATE_FUNCTION")
        self.assertTrue(variants["FVG_MIT_WINDOW"]["own_persistent_state"])
        with open(os.path.join(PHASE_DIR, "decision_card_v1.json"), encoding="utf-8") as f:
            d = json.load(f)["payload"]
        self.assertEqual(d["decision"], "ISOLATION_READY")
        self.assertFalse(d["promotable"])
        self.assertFalse(d["live_ready"])


if __name__ == "__main__":
    unittest.main()
