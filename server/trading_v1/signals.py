"""Signal handoff. Direction comes from the existing backtest function, never from a model."""
from __future__ import annotations

from backtest import sig_macd
from trading_v1.engine import Intent


SIGNALS = {"MACD": sig_macd}


def macd_intent(*, client_id, candles, indicators, index, volume, stop, quote_age_seconds,
                spread_points, enabled):
    if "MACD" not in enabled:
        return None
    direction = sig_macd(candles, indicators, index)
    if direction == 0:
        return None
    price = candles[index]["close"]
    return Intent(
        client_id=client_id, strategy_id="MACD", side="BUY" if direction > 0 else "SELL",
        symbol="XAUUSD", volume=volume, price=price, stop=stop,
        quote_age_seconds=quote_age_seconds, spread_points=spread_points)
