"""Broker port. Only an MT5 adapter may send. The model never calls this."""
from __future__ import annotations

RETRYABLE = {10004, 10020, 10021, 10022}  # REQUOTE, PRICE_CHANGED, OFF_QUOTES, TIMEOUT
INVALID_STOPS = 10016
REJECTED = 10006
DONE = 10009


class BrokerDisconnected(RuntimeError):
    pass


class Mt5NotConnected(BrokerDisconnected):
    pass


class UnconnectedMt5Port:
    """Default port. Refuses every send until a terminal is attached."""

    environment = "DEMO"
    connected = False

    def send(self, order):
        raise Mt5NotConnected("no MT5 terminal is attached")

    def snapshot(self):
        return {"connected": False, "orders": [], "positions": [], "deals": []}


class ScriptedBroker:
    """In-process stand-in with the same retcodes as MT5. Not a live account."""

    def __init__(self, script, *, environment="DEMO"):
        self.environment = environment
        self.connected = True
        self.script = list(script)
        self.quote = (100.0, 100.2)
        self.orders = {}
        self.positions = {}
        self.deals = []
        self.sends = 0

    def move_quote(self, bid, ask):
        self.quote = (bid, ask)

    def send(self, order):
        if not self.connected:
            raise BrokerDisconnected("terminal disconnected")
        known = self.orders.get(order["client_id"])
        if known and (known.get("done") or known["retcode"] not in RETRYABLE):
            return known
        self.sends += 1
        outcome = self.script.pop(0) if self.script else {"retcode": DONE}
        retcode = int(outcome.get("retcode", DONE))
        result = {"client_id": order["client_id"], "retcode": retcode, "ticket": None,
                  "position_id": None, "done": retcode == DONE}
        if retcode == DONE:
            if order.get("stop") is None:
                result["retcode"] = INVALID_STOPS
                result["done"] = False
            else:
                ticket = outcome.get("ticket", 1000 + len(self.orders) + 1)
                position_id = outcome.get("position_id", ticket)
                result.update(ticket=ticket, position_id=position_id, done=True)
                self.positions[position_id] = {
                    "position_id": position_id, "ticket": ticket,
                    "client_id": order["client_id"], "strategy_id": order["strategy_id"],
                    "side": order["side"], "volume": order["volume"],
                    "price": order["price"], "stop": order["stop"],
                    "unrealized_pnl": outcome.get("unrealized_pnl"),
                }
                self.deals.append({"position_id": position_id, "ticket": ticket,
                                   "realized_pnl": None})
        self.orders[order["client_id"]] = result
        return result

    def snapshot(self):
        return {"connected": self.connected, "environment": self.environment,
                "orders": list(self.orders.values()),
                "positions": list(self.positions.values()),
                "deals": list(self.deals)}
