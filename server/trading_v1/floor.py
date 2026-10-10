"""Floor view of EA supervision. Unconfirmed money stays absent."""
from __future__ import annotations


def project(view):
    records = view.get("records") or []
    confirmed = [item for item in records if item.get("state") == "CONFIRMED" and item.get("ticket")]
    ambiguous = [item for item in records if item.get("state") == "AMBIGUOUS"]
    in_flight = [item for item in records if item.get("state") == "IN_FLIGHT"]
    if confirmed:
        execution = "confirmed"
    elif in_flight:
        execution = "in_flight"
    elif ambiguous:
        execution = "ambiguous"
    else:
        execution = "not_run"
    return {"source": "ea_telemetry", "order_owner": "MQL5_EA", "accepts_orders": False,
            "signals": [item["client_id"] for item in records if item.get("last_kind") == "SIGNAL"
                        or item.get("state") == "SIGNAL_ONLY"],
            "orders_confirmed": [{"client_id": item["client_id"], "ticket": item["ticket"]}
                                 for item in confirmed],
            "ambiguous": [item["client_id"] for item in ambiguous],
            "retry_allowed": False,
            "demo_account_verified": bool(view.get("demo_account_verified")),
            "live_enabled": False,
            "realized_pnl": None,
            "stations": {
                "trading.exec": execution,
                "trading.risk": "ea",
                "trading.book": "not_run",
            }}
