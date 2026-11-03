"""simulator.py - deterministic PAPER-ONLY execution. No order is ever
sent to MetaTrader or to any broker API, no network call of any kind
is made - verified by this file's
own import list (stdlib + the reused research_execution_model_v1 pure
functions only) and by a static source-text test
(test_paper_engine_no_broker_dependency in the test suite).

Reuses, not reimplements: FillModel / resolve_bar_exit / apply_cost_cap
/ experiment_identity from server/research_execution_model_v1.py.

One open attempt at a time for (strategy_id, symbol) - no grid, no
pyramid, no recovery, no martingale, per the frozen contract §9.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT / "server") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "server"))

import research_execution_model_v1 as rem  # noqa: E402

OutcomeKind = Literal["SL_HIT", "TP_HIT", "DATASET_ENDED_STILL_OPEN", "FILL_UNCERTAIN"]

INTRABAR_POLICY = "STOP_FIRST"  # DESIGN_ASSUMPTION_V1: conservative, declared, not optimized
SLIPPAGE_PRICE_UNITS = 0.05     # DESIGN_ASSUMPTION_V1: explicit, applied against every fill
DEFAULT_RISK_PCT_OF_EQUITY = 0.01  # DESIGN_ASSUMPTION_V1: configurable, 1% default
DEFAULT_STARTING_EQUITY = 10_000.0


@dataclass
class PaperAttempt:
    attempt_id: str
    strategy_id: str
    strategy_version: str
    symbol: str
    direction: Literal["LONG", "SHORT"]
    signal_bar_epoch: int
    signal_event_id: str
    stop_price: float
    target_price: float
    risk_amount: float
    volume: float
    fill_bar_epoch: int | None = None
    fill_price: float | None = None
    fill_uncertain_reason: str | None = None
    exit_bar_epoch: int | None = None
    exit_price: float | None = None
    outcome: OutcomeKind | None = None
    mfe_price_units: float = 0.0
    mae_price_units: float = 0.0
    cost_breakdown: dict[str, Any] = field(default_factory=dict)
    bars_held: int = 0
    is_open: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "symbol": self.symbol,
            "direction": self.direction,
            "signal_bar_epoch": self.signal_bar_epoch,
            "signal_event_id": self.signal_event_id,
            "stop_price": self.stop_price,
            "target_price": self.target_price,
            "risk_amount": self.risk_amount,
            "volume": self.volume,
            "fill_bar_epoch": self.fill_bar_epoch,
            "fill_price": self.fill_price,
            "fill_uncertain_reason": self.fill_uncertain_reason,
            "exit_bar_epoch": self.exit_bar_epoch,
            "exit_price": self.exit_price,
            "outcome": self.outcome,
            "mfe_price_units": self.mfe_price_units,
            "mae_price_units": self.mae_price_units,
            "cost_breakdown": self.cost_breakdown,
            "bars_held": self.bars_held,
            "is_open": self.is_open,
        }


class PaperEngine:
    """Deterministic, single-attempt-at-a-time paper simulator over a
    STATIC, already-loaded bar list (no live feed, no broker)."""

    def __init__(self, bars_by_epoch: dict[int, dict[str, Any]], bar_epochs_sorted: list[int],
                 risk_pct: float = DEFAULT_RISK_PCT_OF_EQUITY,
                 starting_equity: float = DEFAULT_STARTING_EQUITY) -> None:
        self._bars_by_epoch = bars_by_epoch
        self._epochs = bar_epochs_sorted
        self._risk_pct = risk_pct
        self._equity = starting_equity
        self._open_attempt: PaperAttempt | None = None
        self._closed_attempts: list[PaperAttempt] = []
        self._attempt_seq = 0

    def has_open_attempt(self) -> bool:
        return self._open_attempt is not None

    def all_attempts(self) -> list[PaperAttempt]:
        return list(self._closed_attempts) + ([self._open_attempt] if self._open_attempt else [])

    def _next_bar_after(self, epoch: int) -> dict[str, Any] | None:
        try:
            idx = self._epochs.index(epoch)
        except ValueError:
            return None
        if idx + 1 >= len(self._epochs):
            return None
        return self._bars_by_epoch[self._epochs[idx + 1]]

    def open_from_candidate(self, decision_record: dict[str, Any]) -> PaperAttempt | None:
        """Open a new paper attempt from a non-vetoed BUY/SELL decision
        record (decision_engine.engine.evaluate_bar output). Returns
        None if a FILL_UNCERTAIN was registered instead of a real open
        - caller must still journal that attempt (see to_dict with
        outcome=FILL_UNCERTAIN), it is NOT silently dropped."""
        if self._open_attempt is not None:
            raise RuntimeError("open_from_candidate called while an attempt is already open - "
                                "caller must veto via decision_engine before reaching here")
        if decision_record["h1a_decision"] not in ("BUY", "SELL"):
            raise ValueError("open_from_candidate requires a non-WAIT decision record")

        detail = decision_record["candidate_detail"]
        direction = detail["direction"]
        signal_bar = self._bars_by_epoch[decision_record["bar_epoch"]]
        next_bar = self._next_bar_after(decision_record["bar_epoch"])

        self._attempt_seq += 1
        attempt_id = f"H1A-PAPER-{self._attempt_seq:06d}"

        if next_bar is None or next_bar.get("open") is None:
            attempt = PaperAttempt(
                attempt_id=attempt_id, strategy_id=decision_record["strategy_id"],
                strategy_version=decision_record["strategy_version"], symbol=decision_record["symbol"],
                direction=direction, signal_bar_epoch=decision_record["bar_epoch"],
                signal_event_id=decision_record["event_id"],
                stop_price=float("nan"), target_price=float("nan"), risk_amount=0.0, volume=0.0,
                fill_uncertain_reason="NO_NEXT_BAR_AVAILABLE_FOR_FILL", outcome="FILL_UNCERTAIN",
                is_open=False,
            )
            self._closed_attempts.append(attempt)
            return None

        raw_fill = rem.fill_price(
            rem.SyntheticBar(**{k: signal_bar[k] for k in ("open", "high", "low", "close")}),
            rem.SyntheticBar(**{k: next_bar[k] for k in ("open", "high", "low", "close")}),
            "NEXT_OPEN_V1",
        )
        slippage_sign = 1 if direction == "LONG" else -1
        fill_price_val = raw_fill + slippage_sign * SLIPPAGE_PRICE_UNITS

        # stop is anchored to the sweep extreme already computed by the detector, not re-derived here
        stop = detail["sweep_extreme"] - (signal_bar.get("avg_spread") or 0.0) if direction == "LONG" \
            else detail["sweep_extreme"] + (signal_bar.get("avg_spread") or 0.0)
        risk_distance = abs(fill_price_val - stop)
        if risk_distance <= 0:
            attempt = PaperAttempt(
                attempt_id=attempt_id, strategy_id=decision_record["strategy_id"],
                strategy_version=decision_record["strategy_version"], symbol=decision_record["symbol"],
                direction=direction, signal_bar_epoch=decision_record["bar_epoch"],
                signal_event_id=decision_record["event_id"],
                stop_price=stop, target_price=float("nan"), risk_amount=0.0, volume=0.0,
                fill_uncertain_reason="NON_POSITIVE_RISK_DISTANCE", outcome="FILL_UNCERTAIN", is_open=False,
            )
            self._closed_attempts.append(attempt)
            return None

        target = fill_price_val + 2 * risk_distance if direction == "LONG" else fill_price_val - 2 * risk_distance
        risk_amount = self._equity * self._risk_pct
        volume = risk_amount / risk_distance  # DESIGN_ASSUMPTION_V1: 1 unit = 1 oz, no contract/margin model

        attempt = PaperAttempt(
            attempt_id=attempt_id, strategy_id=decision_record["strategy_id"],
            strategy_version=decision_record["strategy_version"], symbol=decision_record["symbol"],
            direction=direction, signal_bar_epoch=decision_record["bar_epoch"],
            signal_event_id=decision_record["event_id"],
            stop_price=stop, target_price=target, risk_amount=risk_amount, volume=volume,
            fill_bar_epoch=next_bar["bar_epoch"], fill_price=fill_price_val,
            cost_breakdown={"slippage_price_units": SLIPPAGE_PRICE_UNITS,
                            "spread_price_units_at_signal_bar": signal_bar.get("avg_spread")},
        )
        self._open_attempt = attempt
        return attempt

    def advance_open_attempt(self, bar: dict[str, Any]) -> PaperAttempt | None:
        """Call once per bar strictly after the fill bar, in ascending
        order, until it returns a CLOSED attempt (or None if still
        open / nothing to advance)."""
        a = self._open_attempt
        if a is None or bar["bar_epoch"] <= a.fill_bar_epoch:
            return None

        direction = 1 if a.direction == "LONG" else -1
        favorable = (bar["high"] - a.fill_price) if direction == 1 else (a.fill_price - bar["low"])
        adverse = (a.fill_price - bar["low"]) if direction == 1 else (bar["high"] - a.fill_price)
        a.mfe_price_units = max(a.mfe_price_units, favorable)
        a.mae_price_units = max(a.mae_price_units, adverse)
        a.bars_held += 1

        synth = rem.SyntheticBar(**{k: bar[k] for k in ("open", "high", "low", "close")})
        hit = rem.resolve_bar_exit(synth, direction=direction, stop=a.stop_price,
                                    target=a.target_price, policy=INTRABAR_POLICY)
        if hit is None:
            return None

        kind, raw_exit_price = hit
        exit_price = raw_exit_price - direction * SLIPPAGE_PRICE_UNITS  # slippage worsens the exit too
        a.exit_bar_epoch = bar["bar_epoch"]
        a.exit_price = exit_price
        a.outcome = "SL_HIT" if kind == "SL" else "TP_HIT"
        a.is_open = False
        pnl = (exit_price - a.fill_price) * a.volume if direction == 1 else (a.fill_price - exit_price) * a.volume
        self._equity += pnl
        a.cost_breakdown["realized_pnl"] = pnl
        a.cost_breakdown["exit_slippage_price_units"] = SLIPPAGE_PRICE_UNITS
        self._closed_attempts.append(a)
        self._open_attempt = None
        return a

    def close_still_open_at_dataset_end(self, last_bar: dict[str, Any]) -> PaperAttempt | None:
        a = self._open_attempt
        if a is None:
            return None
        a.exit_bar_epoch = last_bar["bar_epoch"]
        a.exit_price = last_bar["close"]
        a.outcome = "DATASET_ENDED_STILL_OPEN"
        a.is_open = False
        self._closed_attempts.append(a)
        self._open_attempt = None
        return a

    @property
    def equity(self) -> float:
        return self._equity
