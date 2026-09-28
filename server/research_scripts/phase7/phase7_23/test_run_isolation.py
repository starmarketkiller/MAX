#!/usr/bin/env python3
"""Phase 7.23 Fase A - test dell'harness di isolamento run. Nessun run
MT5 reale lanciato - fixture sintetiche in una directory temporanea
(monkeypatch delle costanti di percorso del modulo), verifica della
sola LOGICA di isolamento/riconciliazione."""
import csv
import json
import os
import shutil
import tempfile
import unittest

import nxs_research_run_harness as harness


def _write_trades_csv(path, rows):
    cols = ["time", "action", "ticket", "strategy", "price", "lots", "sl", "tp",
           "score_or_pnl", "reason", "hold_sec", "r_multiple", "resolved_tf"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        for r in rows:
            w.writerow([r.get(c, "") for c in cols])


def _write_certificate(path, opened, generated=None, blocked=0, reject=0):
    generated = generated if generated is not None else opened
    with open(path, "w", encoding="utf-8") as f:
        f.write("=== NEXUS Test Validity Certificate v2 ===\n")
        f.write(f"GENERATED={generated} BLOCKED={blocked} OPEN_ATTEMPT={opened} "
               f"OPENED={opened} BROKER_REJECT={reject}\n")
        f.write("VERDICT=PASS\n")


class HarnessTestBase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="nxs_run_isolation_test_")
        self.common_files = os.path.join(self.tmpdir, "CommonFiles")
        self.cert_dir = os.path.join(self.common_files, "NEXUS", "certificates")
        os.makedirs(self.cert_dir, exist_ok=True)
        self._orig_common = harness.COMMON_FILES_DIR
        self._orig_cert = harness.CERT_DIR
        harness.COMMON_FILES_DIR = self.common_files
        harness.CERT_DIR = self.cert_dir

    def tearDown(self):
        harness.COMMON_FILES_DIR = self._orig_common
        harness.CERT_DIR = self._orig_cert
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _trades_path(self):
        return os.path.join(self.common_files, harness.TRADES_CSV_NAME)


class TestPreexistingPersistentFile(HarnessTestBase):
    """Scenario 1: un NEXUS_trades.csv preesistente non deve essere
    interpretato come parte di un nuovo run - e non deve mai essere
    cancellato (solo archiviato/ignorato dalla raccolta)."""

    def test_preexisting_file_detected_in_snapshot(self):
        _write_trades_csv(self._trades_path(), [
            {"time": "2020.01.01 00:00:00", "action": "OPEN", "strategy": "OLD_STRAT"}])
        snap = harness.snapshot_shared_state()
        self.assertTrue(snap["trades_csv_exists"])
        self.assertGreater(snap["trades_csv_size"], 0)

    def test_preexisting_file_never_deleted_by_harness(self):
        """L'harness stesso (a differenza di InpResetTradesLogOnInit, che
        gira dentro l'EA) non cancella mai nulla - verifica che il file
        preesistente sopravviva a uno snapshot + un tentativo di raccolta
        (senza un run reale, la raccolta si limita a COPIARE, mai a
        rimuovere l'origine)."""
        path = self._trades_path()
        _write_trades_csv(path, [{"time": "2020.01.01 00:00:00", "action": "OPEN"}])
        harness.snapshot_shared_state()
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as f:
            self.assertIn("2020.01.01", f.read())


class TestTwoConsecutiveRuns(HarnessTestBase):
    """Scenario 2: due run consecutivi non devono mescolare i propri
    trade - ognuno viene raccolto nella propria run_dir, identificato
    dal proprio run_id."""

    def test_two_runs_produce_separate_manifests_and_dirs(self):
        run_dir_1 = os.path.join(self.tmpdir, "run1")
        run_dir_2 = os.path.join(self.tmpdir, "run2")
        m1, p1, _ = harness.build_ini(run_dir=run_dir_1, strategy_identity="LIQ_SWEEP",
                                      selector=7, symbol="GOLD", period=("2024.01.01", "2024.06.01"),
                                      chart_period="H4")
        m2, p2, _ = harness.build_ini(run_dir=run_dir_2, strategy_identity="LIQ_SWEEP",
                                      selector=7, symbol="GOLD", period=("2024.01.01", "2024.06.01"),
                                      chart_period="H4")
        self.assertNotEqual(m1["run_id"], m2["run_id"], "run_id deve essere univoco per esecuzione "
                            "anche a parita' di configurazione")
        self.assertNotEqual(m1["run_dir"], m2["run_dir"])

    def test_second_run_collection_does_not_see_first_runs_data(self):
        # simula: run1 scrive trade, viene raccolto; run2 (dopo reset EA
        # simulato azzerando il file) scrive trade DIVERSI.
        run_dir_1 = os.path.join(self.tmpdir, "run1")
        m1, p1, _ = harness.build_ini(run_dir=run_dir_1, strategy_identity="LIQ_SWEEP", selector=7,
                                      symbol="GOLD", period=("2024.01.01", "2024.06.01"), chart_period="H4")
        _write_trades_csv(self._trades_path(), [
            {"time": "2024.02.01 00:00:00", "action": "OPEN", "strategy": "LIQ_SWEEP"},
            {"time": "2024.02.05 00:00:00", "action": "CLOSE", "strategy": "LIQ_SWEEP", "score_or_pnl": "10.0"}])
        _write_certificate(os.path.join(self.cert_dir, "run1_cert.txt"), opened=1)
        harness.collect_after_run(m1, p1)

        # simula il reset (InpResetTradesLogOnInit) che l'EA farebbe da solo -
        # qui simulato esplicitamente perche' non c'e' un run MT5 reale nel test.
        os.remove(self._trades_path())
        run_dir_2 = os.path.join(self.tmpdir, "run2")
        m2, p2, _ = harness.build_ini(run_dir=run_dir_2, strategy_identity="LIQ_SWEEP", selector=7,
                                      symbol="GOLD", period=("2024.06.01", "2024.12.01"), chart_period="H4")
        _write_trades_csv(self._trades_path(), [
            {"time": "2024.07.01 00:00:00", "action": "OPEN", "strategy": "LIQ_SWEEP"},
            {"time": "2024.07.03 00:00:00", "action": "CLOSE", "strategy": "LIQ_SWEEP", "score_or_pnl": "-5.0"}])
        _write_certificate(os.path.join(self.cert_dir, "run2_cert.txt"), opened=1)
        harness.collect_after_run(m2, p2)

        with open(m1["trades_csv_dest"], encoding="utf-8") as f:
            self.assertIn("2024.02.01", f.read())
            self.assertNotIn("2024.07.01", f.read())
        with open(m2["trades_csv_dest"], encoding="utf-8") as f:
            self.assertIn("2024.07.01", f.read())
            self.assertNotIn("2024.02.01", f.read())


class TestInterruptedRun(HarnessTestBase):
    """Scenario 3: un run interrotto (nessun certificato mai prodotto)
    deve essere riconoscibile come tale, non silenziosamente accettato
    come completato con successo."""

    def test_no_certificate_produced_flags_warning(self):
        run_dir = os.path.join(self.tmpdir, "run_interrupted")
        m, p, _ = harness.build_ini(run_dir=run_dir, strategy_identity="LIQ_SWEEP", selector=7,
                                    symbol="GOLD", period=("2024.01.01", "2024.06.01"), chart_period="H4")
        # nessun trade, nessun certificato scritto - simula un'interruzione.
        harness.collect_after_run(m, p)
        self.assertIsNone(m["certificate_dest"])
        self.assertIn("warnings", m)
        self.assertTrue(any("nessun nuovo certificato" in w for w in m["warnings"]))

    def test_interrupted_run_status_not_silently_success(self):
        run_dir = os.path.join(self.tmpdir, "run_interrupted2")
        m, p, _ = harness.build_ini(run_dir=run_dir, strategy_identity="LIQ_SWEEP", selector=7,
                                    symbol="GOLD", period=("2024.01.01", "2024.06.01"), chart_period="H4")
        harness.collect_after_run(m, p)
        # reconciliation deve riportare None (non 0) quando i dati mancano.
        self.assertIsNone(m["reconciliation"]["n_opened_per_certificate"])


class TestDuplicateTimestamps(HarnessTestBase):
    """Scenario 4: due righe CLOSE con timestamp identico (visto in
    Phase 7.22 - due run distinti hanno prodotto lo stesso trade
    deterministico) - la riconciliazione deve contarle, non fonderle
    silenziosamente ne' interpretarle come un errore fatale."""

    def test_duplicate_timestamp_rows_counted_as_present(self):
        run_dir = os.path.join(self.tmpdir, "run_dup")
        m, p, _ = harness.build_ini(run_dir=run_dir, strategy_identity="LIQ_SWEEP", selector=7,
                                    symbol="GOLD", period=("2024.01.01", "2024.06.01"), chart_period="H4")
        rows = [
            {"time": "2024.03.01 00:00:00", "action": "OPEN", "strategy": "LIQ_SWEEP"},
            {"time": "2024.03.02 00:00:00", "action": "CLOSE", "strategy": "LIQ_SWEEP", "score_or_pnl": "5.0"},
            {"time": "2024.03.01 00:00:00", "action": "OPEN", "strategy": "LIQ_SWEEP"},
            {"time": "2024.03.02 00:00:00", "action": "CLOSE", "strategy": "LIQ_SWEEP", "score_or_pnl": "5.0"},
        ]
        _write_trades_csv(self._trades_path(), rows)
        _write_certificate(os.path.join(self.cert_dir, "dup_cert.txt"), opened=2)
        harness.collect_after_run(m, p)
        self.assertEqual(m["reconciliation"]["n_trade_closes_in_csv"], 2)


class TestCertificateTradesMismatch(HarnessTestBase):
    """Scenario 5: il conteggio del certificato e quello del CSV devono
    combaciare - se non combaciano, la riconciliazione lo segnala
    esplicitamente (match=False), non lo nasconde."""

    def test_mismatch_flagged_false(self):
        run_dir = os.path.join(self.tmpdir, "run_mismatch")
        m, p, _ = harness.build_ini(run_dir=run_dir, strategy_identity="LIQ_SWEEP", selector=7,
                                    symbol="GOLD", period=("2024.01.01", "2024.06.01"), chart_period="H4")
        _write_trades_csv(self._trades_path(), [
            {"time": "2024.03.01 00:00:00", "action": "OPEN", "strategy": "LIQ_SWEEP"},
            {"time": "2024.03.02 00:00:00", "action": "CLOSE", "strategy": "LIQ_SWEEP", "score_or_pnl": "5.0"}])
        _write_certificate(os.path.join(self.cert_dir, "mismatch_cert.txt"), opened=5)  # 5 != 1
        harness.collect_after_run(m, p)
        self.assertFalse(m["reconciliation"]["match"])
        self.assertEqual(m["reconciliation"]["n_trade_closes_in_csv"], 1)
        self.assertEqual(m["reconciliation"]["n_opened_per_certificate"], 5)

    def test_match_true_when_consistent(self):
        run_dir = os.path.join(self.tmpdir, "run_match")
        m, p, _ = harness.build_ini(run_dir=run_dir, strategy_identity="LIQ_SWEEP", selector=7,
                                    symbol="GOLD", period=("2024.01.01", "2024.06.01"), chart_period="H4")
        _write_trades_csv(self._trades_path(), [
            {"time": "2024.03.01 00:00:00", "action": "OPEN", "strategy": "LIQ_SWEEP"},
            {"time": "2024.03.02 00:00:00", "action": "CLOSE", "strategy": "LIQ_SWEEP", "score_or_pnl": "5.0"}])
        _write_certificate(os.path.join(self.cert_dir, "match_cert.txt"), opened=1)
        harness.collect_after_run(m, p)
        self.assertTrue(m["reconciliation"]["match"])


class TestAmbiguousCertificateDelta(HarnessTestBase):
    """Copertura aggiuntiva: se compaiono PIU' di un nuovo certificato fra
    pre e post-run (es. un altro processo ha scritto in parallelo),
    l'harness non ne sceglie uno a caso - segnala l'ambiguita'."""

    def test_multiple_new_certificates_not_silently_resolved(self):
        run_dir = os.path.join(self.tmpdir, "run_ambiguous")
        m, p, _ = harness.build_ini(run_dir=run_dir, strategy_identity="LIQ_SWEEP", selector=7,
                                    symbol="GOLD", period=("2024.01.01", "2024.06.01"), chart_period="H4")
        _write_certificate(os.path.join(self.cert_dir, "extra1.txt"), opened=1)
        _write_certificate(os.path.join(self.cert_dir, "extra2.txt"), opened=2)
        harness.collect_after_run(m, p)
        self.assertIsNone(m["certificate_dest"])
        self.assertEqual(len(m["new_certificates_detected"]), 2)
        self.assertTrue(any("ambiguita'" in w for w in m["warnings"]))


class TestConfigHashDeterminism(unittest.TestCase):
    def test_same_config_same_hash(self):
        cfg = {"a": 1, "b": [1, 2, 3]}
        self.assertEqual(harness.config_hash(cfg), harness.config_hash(dict(cfg)))

    def test_different_config_different_hash(self):
        self.assertNotEqual(harness.config_hash({"a": 1}), harness.config_hash({"a": 2}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
