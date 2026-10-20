#!/usr/bin/env python3
"""Phase 7.35 — isolation measure hardening tests."""
from __future__ import annotations

import csv
import json
import os
import shutil
import sys
import tempfile
import unittest

PHASE723 = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "phase7_23")
)
sys.path.insert(0, PHASE723)
ROOT = os.path.abspath(os.path.join(PHASE723, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import nxs_research_run_harness as harness  # noqa: E402
import confirmatory_density_gate as density  # noqa: E402


def _write_trades(path, rows):
    cols = ["time", "action", "ticket", "strategy", "price", "lots", "sl", "tp",
            "score_or_pnl", "reason", "hold_sec", "r_multiple", "resolved_tf"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        for r in rows:
            w.writerow([r.get(c, "") for c in cols])


class Phase735Harness(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="nxs_p735_")
        self.common = os.path.join(self.tmpdir, "CommonFiles")
        self.cert_dir = os.path.join(self.common, "NEXUS", "certificates")
        os.makedirs(self.cert_dir, exist_ok=True)
        self._oc = harness.COMMON_FILES_DIR
        self._od = harness.CERT_DIR
        harness.COMMON_FILES_DIR = self.common
        harness.CERT_DIR = self.cert_dir

    def tearDown(self):
        harness.COMMON_FILES_DIR = self._oc
        harness.CERT_DIR = self._od
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_preflight_archives_and_clears(self):
        src = os.path.join(self.common, harness.TRADES_CSV_NAME)
        _write_trades(src, [
            {"time": "2023.10.01 00:00:00", "action": "OPEN", "strategy": "FVG_CONT"},
            {"time": "2023.10.02 00:00:00", "action": "CLOSE", "strategy": "FVG_CONT"},
        ])
        run_dir = os.path.join(self.tmpdir, "run")
        report = harness.preflight_archive_trades_csv(run_dir)
        self.assertTrue(report["src_existed"])
        self.assertTrue(report["cleared"])
        self.assertFalse(os.path.exists(src))
        self.assertTrue(os.path.isfile(report["archived_to"]))

    def test_collect_strict_fails_on_raw_mismatch(self):
        run_dir = os.path.join(self.tmpdir, "run_m")
        m, p, _ = harness.build_ini(
            run_dir=run_dir, strategy_identity="FVG_CONT", selector=8,
            symbol="GOLD", period=("2026.07.01", "2026.10.19"), chart_period="H4",
        )
        # Contaminated CSV: old + new (Phase 7.34 pattern)
        _write_trades(os.path.join(self.common, harness.TRADES_CSV_NAME), [
            {"time": "2023.10.01 00:00:00", "action": "OPEN", "strategy": "FVG_CONT"},
            {"time": "2023.10.02 00:00:00", "action": "CLOSE", "strategy": "FVG_CONT"},
            {"time": "2026.08.01 00:00:00", "action": "OPEN", "strategy": "FVG_CONT"},
            {"time": "2026.08.02 00:00:00", "action": "CLOSE", "strategy": "FVG_CONT"},
        ])
        with open(os.path.join(self.cert_dir, "c.txt"), "w", encoding="utf-8") as f:
            f.write("OPENED=1\nVERDICT=PASS\n")
        m = harness.collect_after_run(m, p, strict_isolation=True)
        self.assertEqual(m["status"], "COLLECTED_ISOLATION_FAILED")
        self.assertFalse(m["reconciliation"]["isolation_ok"])
        self.assertTrue(m["reconciliation"]["window_match"])
        self.assertEqual(m["reconciliation"]["n_trade_closes_in_csv"], 2)
        self.assertEqual(m["reconciliation"]["n_trade_closes_in_csv_in_window"], 1)

    def test_density_gate_refuses_short_window(self):
        # FVG_CONT-like: ~2.5/mo, buy share ~0.4, 3.5 months → n_B≈3.5 < 30
        card = density.assess(
            trades_per_month=2.5, months=3.5, min_n=30, buy_share=0.4
        )
        self.assertEqual(card["verdict"], "REFUSE")
        self.assertFalse(card["allow"])
        self.assertGreater(card["months_needed_for_min_n_B"], 20)

    def test_density_gate_allows_long_enough(self):
        card = density.assess(
            trades_per_month=2.5, months=40, min_n=30, buy_share=0.4
        )
        self.assertEqual(card["verdict"], "ALLOW")
        self.assertTrue(card["allow"])

    def test_logging_mqh_has_rewrite_fallback(self):
        path = os.path.join(ROOT, "MQL5/Include/NEXUS_v1/NXS_Logging.mqh")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("FILE_REWRITE", text)
        self.assertIn("FileCopy", text)
        self.assertIn("Phase 7.35", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
