"""Trading floor read from execution events and the broker snapshot. Missing stays missing."""
from __future__ import annotations


def project(engine_view, *, stages=None, reconcile=None):
    stages = stages or {}
    orders = engine_view.get("orders") or []
    positions = (reconcile or {}).get("positions")
    if positions is None:
        positions = engine_view.get("positions") or []
    confirmed = [item for item in orders if item.get("state") == "FILLED" and item.get("ticket")]
    blocked = [item for item in orders if item.get("state") == "BLOCKED"]
    rejected = [item for item in orders if item.get("state") == "REJECTED"]
    realized = None if reconcile is None else reconcile.get("realized_pnl")
    unrealized = None if reconcile is None else reconcile.get("unrealized_pnl")
    if unrealized is None:
        unrealized = _pnl(positions)
    strategies = [{"strategy_id": name, "stage": stage}
                  for name, stage in sorted(stages.items())]
    return {
        "source": "broker" if engine_view.get("connected") else "not_connected",
        "mode": engine_view.get("mode"),
        "live_armed": bool(engine_view.get("live_armed")),
        "strategies": strategies,
        "signals": [item["client_id"] for item in orders],
        "orders_sent": [item["client_id"] for item in orders if item.get("state") != "BLOCKED"],
        "orders_confirmed": [{"client_id": item["client_id"], "ticket": item["ticket"]}
                             for item in confirmed],
        "positions": positions,
        "realized_pnl": realized,
        "unrealized_pnl": unrealized,
        "risk": {"kill_switch": bool(engine_view.get("kill_switch")),
                 "blocked": [item.get("reasons") for item in blocked]},
        "errors": [{"client_id": item["client_id"], "retcode": item.get("retcode")}
                   for item in rejected],
        "stations": {
            "trading.research": "recorded" if any(stage == "RESEARCH" for stage in stages.values()) else "not_run",
            "trading.valid": "recorded" if any(stage == "VALIDATED" for stage in stages.values()) else "not_run",
            "trading.shadow": "recorded" if engine_view.get("mode") == "DEMO" and confirmed else "not_run",
            "trading.exec": "confirmed" if confirmed else ("blocked" if blocked or rejected else "not_run"),
            "trading.risk": "blocked" if engine_view.get("kill_switch") or blocked else "clear",
            "trading.book": "broker" if positions else "not_run",
            "trading.perf": "broker" if _pnl(positions) is not None else "not_run",
        },
    }


def _pnl(positions):
    values = [item.get("unrealized_pnl") for item in positions
              if isinstance(item.get("unrealized_pnl"), (int, float))]
    if not values:
        return None
    return float(sum(values))
