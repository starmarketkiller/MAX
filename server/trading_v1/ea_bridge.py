"""Turn a real EA /api/ea/push payload into supervision records.

The EA already pushes its open positions (ticket, strategy, side, pnl - see
`_PositionsJSON` in NXS_WebBridge.mqh) on every status push. Nothing before
this module read that array into `TradingSupervisor`, so the supervisor was
correct in isolation but never reflected a real account. This only reads
positions that already exist on the broker side; it cannot create, confirm
ahead of time, or infer an order that was never reported.
"""
from __future__ import annotations


def ingest_positions(supervisor, payload):
    """Record each open EA position as CONFIRMED. Returns the records written.

    There is no pre-send client id in this telemetry (the EA reports
    positions, not pre-order intents), so `ticket:<n>` is used as the
    supervisor's client_id. This means the SIGNAL/AMBIGUOUS/retry states of
    TradingSupervisor are not exercised by this path - duplicate-order
    prevention already happens inside the EA (NXS_OpenTrade's bar/setup-matrix
    caps, the anti-duplicate ledger). This path only answers "what does the
    broker show right now", which is what the floor/dashboard need.
    """
    positions = payload.get("positions")
    if not isinstance(positions, list):
        return []
    recorded = []
    for pos in positions:
        if not isinstance(pos, dict):
            continue
        ticket = pos.get("ticket")
        if not ticket:
            continue
        record = supervisor.ingest({
            "kind": "POSITION",
            "client_id": f"ticket:{ticket}",
            "strategy_id": pos.get("strategy"),
            "ticket": ticket,
            "position_id": ticket,
        })
        recorded.append(record)
    return recorded
