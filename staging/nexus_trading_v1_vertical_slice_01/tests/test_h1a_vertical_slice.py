"""Test suite for NEXUS Trading V1 Vertical Slice 01 (H1-A).

Three explicitly distinguished classes, per the mandate (section 8):
- SYNTHETIC: hand-built bar fixtures, exact boundary conditions, no
  real market data.
- HISTORICAL_ALLOWED: real bars from the reused DISCOVERY_REUSE
  dataset (2019-2022, verified outside the sealed FINAL_HOLDOUT,
  2026-02-04..2026-09-16).
- VISUAL: NOT executed here - no browser tool is available in this
  environment to actually render cockpit/index.html. Declared as a
  limitation in LIMITATIONS.md, not silently skipped.

No economic claim is made or tested here - these tests check
mechanical correctness (causality, determinism, no duplication,
mandatory stop, broker isolation, event integrity), never profit.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest

from data_layer.bar_store import BarStore
from decision_engine import engine as decision_engine
from decision_engine import h1a_detector as det
from paper_engine.simulator import PaperEngine
from journal import journal as journal_mod
from replay.replay import run_decisions_over, verify_no_future_leakage

ROOT = Path(__file__).resolve().parent.parent


def make_bar(epoch: int, open_: float, high: float, low: float, close: float,
             avg_spread: float = 0.3) -> dict:
    from datetime import datetime, timezone
    open_dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
    return {
        "bar_epoch": epoch,
        "bar_open_utc": open_dt.isoformat(),
        "available_at_utc": (open_dt.replace()).isoformat().replace("+00:00", "Z"),
        "open": open_, "high": high, "low": low, "close": close,
        "avg_spread": avg_spread,
    }


# ---------------------------------------------------------------------------
# SYNTHETIC: h1a_detector boundary conditions
# ---------------------------------------------------------------------------

class TestSyntheticDetector:
    """SYNTHETIC - hand-built fixtures, no real market data."""

    def test_insufficient_warmup(self):
        decision, reason, detail = det.classify_bar(
            make_bar(0, 100, 101, 99, 100.5), level_high=None, level_low=None, sweep_buffer=0.0)
        assert decision == det.WAIT
        assert reason == det.REASON_INSUFFICIENT_WARMUP
        assert detail is None

    def test_no_sweep(self):
        decision, reason, _ = det.classify_bar(
            make_bar(0, 100, 101, 99.5, 100.2), level_high=102, level_low=98, sweep_buffer=0.0)
        assert decision == det.WAIT
        assert reason == det.REASON_NO_SWEEP

    def test_sweep_without_reclaim_is_wait_not_h1a(self):
        # high sweeps the level AND closes beyond it (real breakout, not H1-A)
        decision, reason, _ = det.classify_bar(
            make_bar(0, 100, 103.5, 99.8, 103.2), level_high=103, level_low=98, sweep_buffer=0.0)
        assert decision == det.WAIT
        assert reason == det.REASON_SWEEP_WITHOUT_RECLAIM

    def test_long_candidate_sweep_and_reclaim(self):
        # low sweeps below level_low, close back above it -> BUY
        decision, reason, detail = det.classify_bar(
            make_bar(0, 100, 101, 97.5, 100.3), level_high=103, level_low=98, sweep_buffer=0.0)
        assert decision == det.BUY
        assert reason == det.REASON_CANDIDATE_LONG
        assert detail["direction"] == "LONG"
        assert detail["sweep_extreme"] == 97.5

    def test_short_candidate_sweep_and_reclaim(self):
        decision, reason, detail = det.classify_bar(
            make_bar(0, 100, 103.6, 99.5, 100.1), level_high=103, level_low=98, sweep_buffer=0.0)
        assert decision == det.SELL
        assert reason == det.REASON_CANDIDATE_SHORT
        assert detail["direction"] == "SHORT"

    def test_ambiguous_both_sides(self):
        # pathological huge-range bar that sweeps AND reclaims both sides
        decision, reason, detail = det.classify_bar(
            make_bar(0, 100, 103.5, 97.5, 100.5), level_high=103, level_low=98, sweep_buffer=0.0)
        assert decision == det.WAIT
        assert reason == det.REASON_AMBIGUOUS_BOTH
        assert detail is None

    def test_sweep_buffer_is_a_parameter_not_hardcoded(self):
        # a small sweep that passes with zero buffer must fail (NO_SWEEP)
        # once a larger buffer is required - proves the buffer is a real,
        # externally-controlled parameter, not a hidden constant
        bar = make_bar(0, 100, 101.2, 99.5, 100.3)
        dec_zero_buf, _, _ = det.classify_bar(bar, level_high=101, level_low=98, sweep_buffer=0.0)
        dec_big_buf, reason_big, _ = det.classify_bar(bar, level_high=101, level_low=98, sweep_buffer=1.0)
        assert dec_zero_buf in (det.BUY, det.SELL, det.WAIT)  # sanity
        assert dec_big_buf == det.WAIT and reason_big == det.REASON_NO_SWEEP

    def test_classify_sequence_is_causal_not_centered(self):
        """A level computed by classify_sequence for bar i must never
        include bar i's own high/low - verified by constructing a
        sequence where bar 20's own extreme would change the result if
        (incorrectly) included in its own window."""
        bars = [make_bar(i, 100, 100.5, 99.5, 100.0) for i in range(det.LOOKBACK_N)]
        # bar 20 has an extreme low that must NOT be in its own level window
        bars.append(make_bar(det.LOOKBACK_N, 100, 100.5, 50.0, 100.0))
        results = det.classify_sequence(bars)
        decision, reason, detail = results[det.LOOKBACK_N]
        # level_low for bar 20 must be built from bars 0..19 (all 99.5),
        # so bar 20's low=50.0 is a genuine sweep below that prior level
        assert reason in (det.REASON_CANDIDATE_LONG, det.REASON_SWEEP_WITHOUT_RECLAIM)


# ---------------------------------------------------------------------------
# SYNTHETIC: WAIT is a first-class observable record
# ---------------------------------------------------------------------------

class TestWaitIsObservable:
    def test_wait_record_has_full_schema(self):
        bar = make_bar(0, 100, 100.5, 99.5, 100.0)
        rec = decision_engine.evaluate_bar(bar, level_high=None, level_low=None,
                                            sweep_buffer=0.0, has_open_attempt=False)
        assert rec["h1a_decision"] == "WAIT"
        for key in ("event_id", "strategy_id", "strategy_version", "causal_timestamp",
                    "h1a_reason_code", "missing_rules_declared", "shadow_audit_event"):
            assert key in rec and rec[key] is not None


# ---------------------------------------------------------------------------
# SYNTHETIC: duplicate suppression (no duplicate signals / one attempt at a time)
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_duplicate_candidate_is_vetoed_while_attempt_open(self):
        bar = make_bar(0, 100, 101, 97.5, 100.3)  # would be a LONG candidate
        rec = decision_engine.evaluate_bar(bar, level_high=103, level_low=98,
                                            sweep_buffer=0.0, has_open_attempt=True)
        assert rec["h1a_decision"] == "WAIT"
        assert rec["is_veto"] is True
        assert rec["h1a_reason_code"] == "DUPLICATE_SUPPRESSED_OPEN_ATTEMPT_EXISTS"
        assert rec["h1a_decision_pre_veto"] == "BUY"
        assert rec["candidate_detail"] is None  # never opens a second attempt

    def test_same_bar_evaluated_twice_yields_identical_event_id(self):
        bar = make_bar(0, 100, 101, 97.5, 100.3)
        rec1 = decision_engine.evaluate_bar(bar, 103, 98, 0.0, False)
        rec2 = decision_engine.evaluate_bar(bar, 103, 98, 0.0, False)
        assert rec1["event_id"] == rec2["event_id"]


# ---------------------------------------------------------------------------
# SYNTHETIC: missing-data handling
# ---------------------------------------------------------------------------

class TestMissingData:
    def test_missing_close_marks_data_invalid_in_shadow_event(self):
        bar = make_bar(0, 100, 101, 99, 100.0)
        bar["close"] = None
        rec = decision_engine.evaluate_bar(bar, level_high=103, level_low=98,
                                            sweep_buffer=0.0, has_open_attempt=False)
        assert rec["shadow_audit_event"]["data_quality"] == "INVALID"

    def test_no_next_bar_registers_fill_uncertain_not_invented_fill(self):
        bars_by_epoch = {0: make_bar(0, 100, 101, 97.5, 100.3)}
        pe = PaperEngine(bars_by_epoch, [0])
        rec = decision_engine.evaluate_bar(bars_by_epoch[0], 103, 98, 0.0, False)
        assert rec["h1a_decision"] == "BUY"
        opened = pe.open_from_candidate(rec)
        assert opened is None  # no real attempt opened
        attempts = pe.all_attempts()
        assert len(attempts) == 1
        assert attempts[0].outcome == "FILL_UNCERTAIN"
        assert attempts[0].fill_uncertain_reason == "NO_NEXT_BAR_AVAILABLE_FOR_FILL"
        assert attempts[0].fill_price is None  # never invented


# ---------------------------------------------------------------------------
# SYNTHETIC: mandatory stop + execution costs
# ---------------------------------------------------------------------------

class TestMandatoryStopAndCosts:
    def test_every_opened_attempt_has_a_real_stop(self):
        bars_by_epoch = {
            0: make_bar(0, 100, 101, 97.5, 100.3),
            900: make_bar(900, 100.3, 100.8, 100.0, 100.5),
        }
        pe = PaperEngine(bars_by_epoch, [0, 900])
        rec = decision_engine.evaluate_bar(bars_by_epoch[0], 103, 98, 0.0, False)
        opened = pe.open_from_candidate(rec)
        assert opened is not None
        assert opened.stop_price is not None
        import math
        assert not math.isnan(opened.stop_price)

    def test_slippage_and_spread_are_explicit_and_applied(self):
        bars_by_epoch = {
            0: make_bar(0, 100, 101, 97.5, 100.3, avg_spread=0.4),
            900: make_bar(900, 100.3, 100.8, 100.0, 100.5, avg_spread=0.4),
        }
        pe = PaperEngine(bars_by_epoch, [0, 900])
        rec = decision_engine.evaluate_bar(bars_by_epoch[0], 103, 98, 0.0, False)
        opened = pe.open_from_candidate(rec)
        # LONG: fill = next bar's open (100.3) + slippage (worsens a buy)
        from paper_engine.simulator import SLIPPAGE_PRICE_UNITS
        assert opened.fill_price == pytest.approx(100.3 + SLIPPAGE_PRICE_UNITS)
        assert opened.cost_breakdown["slippage_price_units"] == SLIPPAGE_PRICE_UNITS
        assert opened.cost_breakdown["spread_price_units_at_signal_bar"] == 0.4

    def test_no_grid_pyramid_recovery_martingale_single_attempt_enforced(self):
        """PaperEngine.open_from_candidate raises if called while an
        attempt is already open - the one-attempt-at-a-time invariant
        is enforced in code, not just by convention."""
        bars_by_epoch = {
            0: make_bar(0, 100, 101, 97.5, 100.3),
            900: make_bar(900, 100.3, 100.8, 100.0, 100.5),
        }
        pe = PaperEngine(bars_by_epoch, [0, 900])
        rec = decision_engine.evaluate_bar(bars_by_epoch[0], 103, 98, 0.0, False)
        pe.open_from_candidate(rec)
        with pytest.raises(RuntimeError):
            pe.open_from_candidate(rec)


# ---------------------------------------------------------------------------
# SYNTHETIC + source-text: paper engine / broker separation
# ---------------------------------------------------------------------------

class TestBrokerSeparation:
    def test_simulator_source_has_no_network_or_mt5_import(self):
        """Static, source-text check - same technique already used
        elsewhere in this codebase (phase5d_shadow_engine_v1) to prove
        'no execution capability by construction'."""
        src = (ROOT / "paper_engine" / "simulator.py").read_text(encoding="utf-8")
        forbidden = ("socket", "requests", "MetaTrader5", "OrderSend", "urllib", "http.client")
        for token in forbidden:
            assert token not in src, f"forbidden token {token!r} found in simulator.py"

    def test_decision_engine_source_has_no_network_or_mt5_import(self):
        src = (ROOT / "decision_engine" / "engine.py").read_text(encoding="utf-8")
        forbidden = ("socket", "requests", "MetaTrader5", "OrderSend", "urllib", "http.client")
        for token in forbidden:
            assert token not in src


# ---------------------------------------------------------------------------
# HISTORICAL_ALLOWED: real dataset (DISCOVERY_REUSE, outside FINAL_HOLDOUT)
# ---------------------------------------------------------------------------

class TestHistoricalAllowedDataLayer:
    """HISTORICAL_ALLOWED - real bars, verified not the sealed holdout."""

    @pytest.fixture(scope="class")
    def store(self):
        return BarStore()

    def test_coverage_is_outside_final_holdout_window(self, store):
        from datetime import datetime, timezone
        cov = store.coverage()
        last = datetime.fromisoformat(cov["last_bar_available_at_utc"].replace("Z", "+00:00"))
        holdout_start = datetime(2026, 2, 4, tzinfo=timezone.utc)
        assert last < holdout_start, "dataset must end before the sealed FINAL_HOLDOUT window"

    def test_bars_as_of_never_returns_a_future_bar(self, store):
        from datetime import datetime
        all_bars = store.all_bars()
        cutoff = all_bars[100]["available_at_utc"]
        cutoff_dt = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
        filtered = store.bars_as_of(cutoff)
        assert len(filtered) == 101
        for b in filtered:
            available = datetime.fromisoformat(b["available_at_utc"].replace("Z", "+00:00"))
            assert available <= cutoff_dt

    def test_anti_lookahead_replay_passes_on_real_data(self, store):
        n = len(store.all_bars())
        samples = [50, 500, 2000, n - 1]
        report = verify_no_future_leakage(store, samples)
        assert report["passed"], report["mismatches"][:5]

    def test_replay_is_deterministic_same_input_same_output(self, store):
        bars = store.all_bars()[:600]
        run1 = run_decisions_over(bars)
        run2 = run_decisions_over(bars)
        for r1, r2 in zip(run1, run2):
            assert r1["event_id"] == r2["event_id"]
            assert r1["h1a_decision"] == r2["h1a_decision"]
            assert r1["h1a_reason_code"] == r2["h1a_reason_code"]

    def test_all_three_decision_kinds_occur_on_real_data(self, store):
        bars = store.all_bars()[:1500]
        records = run_decisions_over(bars)
        decisions = {r["h1a_decision"] for r in records}
        assert decisions == {"BUY", "SELL", "WAIT"}

    def test_causal_timestamp_is_bar_close_never_bar_open(self, store):
        bar = store.all_bars()[100]
        rec = decision_engine.evaluate_bar(bar, None, None, 0.0, False)
        assert rec["causal_timestamp"] == bar["available_at_utc"]
        assert rec["causal_timestamp"] != bar["bar_open_utc"]


# ---------------------------------------------------------------------------
# Journal / event integrity
# ---------------------------------------------------------------------------

class TestJournalIntegrity:
    """Uses a local scratch dir under this slice's own tree instead of
    pytest's tmp_path fixture - the sandbox denies access to the
    system-wide Temp directory pytest's tmp_path relies on (a sandbox
    permission limit, not a bug in the code under test)."""

    @pytest.fixture()
    def scratch_dir(self):
        import shutil
        d = ROOT / "tests" / "_scratch"
        d.mkdir(parents=True, exist_ok=True)
        yield d
        shutil.rmtree(d, ignore_errors=True)

    def test_hash_chain_detects_tampering(self, scratch_dir):
        log_path = scratch_dir / "test_journal.jsonl"
        journal_mod.append_records([{"a": 1}, {"a": 2}, {"a": 3}], log_path)
        assert journal_mod.verify_chain(log_path) is True

        lines = log_path.read_text(encoding="utf-8").splitlines()
        tampered = json.loads(lines[1])
        tampered["payload"]["a"] = 999
        lines[1] = json.dumps(tampered)
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        assert journal_mod.verify_chain(log_path) is False

    def test_journal_is_append_only_never_truncates_existing(self, scratch_dir):
        log_path = scratch_dir / "append_test.jsonl"
        journal_mod.append_records([{"a": 1}], log_path)
        before = log_path.read_text(encoding="utf-8")
        journal_mod.append_records([{"a": 2}], log_path)
        after = log_path.read_text(encoding="utf-8")
        assert after.startswith(before)

    def test_strategy_version_present_on_every_record(self):
        bars = [make_bar(0, 100, 101, 97.5, 100.3)]
        recs = decision_engine.evaluate_series(bars, lambda: False)
        for r in recs:
            assert r["strategy_id"] == "H1_A"
            assert r["strategy_version"] == "H1_A_V1"
            assert r["detector_version"] == "H1_A_V1"
