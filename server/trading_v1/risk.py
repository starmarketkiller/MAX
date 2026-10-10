"""Risk checks independent of any model. Limits are data, not suggestions."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    max_risk_per_trade: float = 50.0
    max_exposure_lots: float = 1.0
    max_daily_loss: float = 100.0
    max_drawdown_pct: float = 10.0
    max_positions: int = 3
    min_margin_level_pct: float = 200.0
    max_spread_points: float = 50.0
    max_quote_age_seconds: float = 5.0

    def replace(self, **changes):
        return RiskLimits(**{**self.__dict__, **changes})


@dataclass(frozen=True)
class AccountView:
    environment: str
    verified: bool
    equity: float
    peak_equity: float
    daily_pnl: float
    margin_level_pct: float
    open_positions: int
    open_lots: float


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reasons: tuple


def evaluate(intent, account: AccountView, limits: RiskLimits, *,
             kill_switch: bool, quote_age_seconds: float, spread_points: float):
    reasons = []
    if kill_switch:
        reasons.append("KILL_SWITCH")
    if quote_age_seconds > limits.max_quote_age_seconds:
        reasons.append("STALE_QUOTE")
    if intent.stop is None:
        reasons.append("STOP_REQUIRED")
    else:
        entry = float(intent.price)
        stop = float(intent.stop)
        if intent.side == "BUY" and stop >= entry:
            reasons.append("STOP_ON_WRONG_SIDE")
        if intent.side == "SELL" and stop <= entry:
            reasons.append("STOP_ON_WRONG_SIDE")
        risk = abs(entry - stop) * float(intent.volume)
        if risk > limits.max_risk_per_trade:
            reasons.append("MAX_RISK_PER_TRADE")
    if float(intent.volume) <= 0:
        reasons.append("VOLUME")
    if account.open_lots + float(intent.volume) > limits.max_exposure_lots:
        reasons.append("MAX_EXPOSURE")
    if account.daily_pnl <= -limits.max_daily_loss:
        reasons.append("MAX_DAILY_LOSS")
    if account.peak_equity > 0:
        drawdown = (account.peak_equity - account.equity) / account.peak_equity * 100
        if drawdown >= limits.max_drawdown_pct:
            reasons.append("MAX_DRAWDOWN")
    if account.open_positions >= limits.max_positions:
        reasons.append("MAX_POSITIONS")
    if account.margin_level_pct < limits.min_margin_level_pct:
        reasons.append("MARGIN")
    if spread_points > limits.max_spread_points:
        reasons.append("SPREAD")
    return RiskDecision(allowed=not reasons, reasons=tuple(reasons))
