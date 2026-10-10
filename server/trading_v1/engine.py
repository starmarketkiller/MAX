"""Execution cycle. Persists the intent before the send so a retry cannot double-fire."""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from trading_v1.broker import RETRYABLE, BrokerDisconnected, UnconnectedMt5Port
from trading_v1.risk import AccountView, RiskLimits, evaluate


MODES = {"BACKTEST", "DEMO", "LIVE"}
HUMAN_LIVE_PHRASE = "ENABLE_LIVE"


def _now():
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Intent:
    client_id: str
    strategy_id: str
    side: str
    symbol: str
    volume: float
    price: float
    stop: float | None
    quote_age_seconds: float
    spread_points: float


class ExecutionEngine:
    def __init__(self, path, broker=None, *, mode="DEMO", limits=None, account=None):
        if mode not in MODES:
            raise ValueError("unknown mode")
        self.path = Path(path)
        self.broker = broker if broker is not None else UnconnectedMt5Port()
        self.mode = mode
        self.limits = limits or RiskLimits()
        self.account = account or AccountView(
            "DEMO", False, 1000.0, 1000.0, 0.0, 500.0, 0, 0.0)
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save(self._empty())

    def _empty(self):
        return {"schema": "trading-execution-v1", "mode": self.mode, "live_armed": False,
                "kill_switch": False, "enabled_strategies": [], "orders": {}, "audit": []}

    def _load(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, state):
        temp = self.path.with_name(f"{self.path.name}.{os.getpid()}.tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, self.path)

    def _audit(self, state, kind, **payload):
        state["audit"].append({"at": _now(), "kind": kind, **payload})

    def set_kill_switch(self, on: bool):
        with self._lock:
            state = self._load()
            state["kill_switch"] = bool(on)
            self._audit(state, "KILL_SWITCH", on=bool(on))
            self._save(state)

    def enable_strategy(self, strategy_id, *, approved_by):
        actor = str(approved_by or "")
        if not actor or actor.startswith("jarvis"):
            raise PermissionError("a human must enable a strategy")
        with self._lock:
            state = self._load()
            if strategy_id not in state["enabled_strategies"]:
                state["enabled_strategies"].append(strategy_id)
            self._audit(state, "STRATEGY_ENABLED", strategy_id=strategy_id, approved_by=actor)
            self._save(state)

    def arm_live(self, *, phrase, account_environment, account_verified):
        if phrase != HUMAN_LIVE_PHRASE or account_environment != "LIVE" or not account_verified:
            raise PermissionError("LIVE stays disabled")
        with self._lock:
            state = self._load()
            state["live_armed"] = True
            state["mode"] = "LIVE"
            self.mode = "LIVE"
            self._audit(state, "LIVE_ARMED")
            self._save(state)

    def submit(self, intent: Intent):
        with self._lock:
            state = self._load()
            if self.mode == "LIVE" and not state.get("live_armed"):
                return self._block(state, intent, ("LIVE_DISABLED",))
            if getattr(self.broker, "environment", None) != self.mode:
                return self._block(state, intent, ("ACCOUNT_MODE_MISMATCH",))
            if intent.strategy_id not in state["enabled_strategies"]:
                return self._block(state, intent, ("STRATEGY_NOT_ENABLED",))
            existing = state["orders"].get(intent.client_id)
            if existing and existing["state"] in {"FILLED", "REJECTED"}:
                return existing
            if existing and existing["state"] == "SENDING":
                recovered = self._recover(state, intent)
                if recovered:
                    return recovered
            decision = evaluate(
                intent, self.account, self.limits,
                kill_switch=state["kill_switch"],
                quote_age_seconds=intent.quote_age_seconds,
                spread_points=intent.spread_points)
            self._audit(state, "RISK", client_id=intent.client_id,
                        allowed=decision.allowed, reasons=list(decision.reasons))
            if not decision.allowed:
                return self._block(state, intent, decision.reasons)
            order = {"client_id": intent.client_id, "strategy_id": intent.strategy_id,
                     "side": intent.side, "symbol": intent.symbol, "volume": intent.volume,
                     "price": intent.price, "stop": intent.stop}
            state["orders"][intent.client_id] = {**order, "state": "SENDING", "ticket": None,
                                                  "position_id": None, "retcode": None}
            self._audit(state, "SENDING", client_id=intent.client_id)
            self._save(state)
            try:
                result = self._send_with_retry(order)
            except BrokerDisconnected:
                state = self._load()
                state["orders"][intent.client_id]["state"] = "BLOCKED"
                state["orders"][intent.client_id]["retcode"] = "DISCONNECTED"
                self._audit(state, "DISCONNECTED", client_id=intent.client_id)
                self._save(state)
                return state["orders"][intent.client_id]
            state = self._load()
            record = state["orders"][intent.client_id]
            record["retcode"] = result["retcode"]
            if result.get("done"):
                record.update(state="FILLED", ticket=result["ticket"],
                              position_id=result["position_id"])
                self._audit(state, "FILLED", client_id=intent.client_id,
                            ticket=result["ticket"], position_id=result["position_id"])
            else:
                record["state"] = "REJECTED"
                self._audit(state, "REJECTED", client_id=intent.client_id,
                            retcode=result["retcode"])
            self._save(state)
            return record

    def _send_with_retry(self, order):
        result = self.broker.send(order)
        if result["retcode"] not in RETRYABLE:
            return result
        bid, ask = getattr(self.broker, "quote", (None, None))
        if hasattr(self.broker, "move_quote"):
            self.broker.move_quote((bid or order["price"]) + 0.1, (ask or order["price"]) + 0.1)
        elif getattr(self.broker, "quote", None) == (bid, ask):
            return result
        return self.broker.send(order)

    def _recover(self, state, intent):
        snapshot = self.broker.snapshot()
        for order in snapshot.get("orders") or []:
            if order.get("client_id") == intent.client_id and order.get("done"):
                record = state["orders"][intent.client_id]
                record.update(state="FILLED", ticket=order.get("ticket"),
                              position_id=order.get("position_id"), retcode=order.get("retcode"))
                self._audit(state, "RECOVERED", client_id=intent.client_id,
                            ticket=order.get("ticket"))
                self._save(state)
                return record
        return None

    def _block(self, state, intent, reasons):
        record = {"client_id": intent.client_id, "strategy_id": intent.strategy_id,
                  "state": "BLOCKED", "reasons": list(reasons), "ticket": None}
        state["orders"][intent.client_id] = record
        self._audit(state, "BLOCKED", client_id=intent.client_id, reasons=list(reasons))
        self._save(state)
        return record

    def reconcile(self):
        with self._lock:
            state = self._load()
            snapshot = self.broker.snapshot()
            broker_ids = {item.get("client_id") for item in snapshot.get("positions") or []}
            filled = [item for item in state["orders"].values() if item.get("state") == "FILLED"]
            missing = [item["client_id"] for item in filled if item["client_id"] not in broker_ids]
            extra = [item["position_id"] for item in snapshot.get("positions") or []
                     if item.get("client_id") not in state["orders"]]
            report = {"authoritative": "broker", "positions": snapshot.get("positions") or [],
                      "ledger_missing_on_broker": missing, "broker_unknown_to_ledger": extra,
                      "diverged": bool(missing or extra),
                      "realized_pnl": _sum(snapshot.get("deals") or [], "realized_pnl"),
                      "unrealized_pnl": _sum(snapshot.get("positions") or [], "unrealized_pnl")}
            self._audit(state, "RECONCILE", diverged=report["diverged"])
            self._save(state)
            return report

    def projection(self):
        state = self._load()
        report = None
        try:
            snapshot = self.broker.snapshot()
        except BrokerDisconnected:
            snapshot = {"connected": False, "positions": [], "orders": [], "deals": []}
        return {"mode": state["mode"], "live_armed": state["live_armed"],
                "kill_switch": state["kill_switch"],
                "connected": bool(snapshot.get("connected")),
                "enabled_strategies": list(state["enabled_strategies"]),
                "orders": list(state["orders"].values()),
                "positions": snapshot.get("positions") or [],
                "audit": state["audit"]}


def _sum(rows, key):
    values = [row.get(key) for row in rows if isinstance(row.get(key), (int, float))]
    if not values:
        return None
    return float(sum(values))


def read_state(path):
    file = Path(path)
    if not file.exists():
        return {"connected": False, "mode": None, "live_armed": False, "kill_switch": False,
                "orders": [], "positions": [], "audit": []}
    state = json.loads(file.read_text(encoding="utf-8"))
    return {"connected": False, "mode": state.get("mode"), "live_armed": bool(state.get("live_armed")),
            "kill_switch": bool(state.get("kill_switch")),
            "enabled_strategies": list(state.get("enabled_strategies") or []),
            "orders": list((state.get("orders") or {}).values()),
            "positions": [], "audit": state.get("audit") or []}


def jarvis_proposal(action):
    forbidden = {"ENABLE_LIVE", "RAISE_RISK_LIMIT", "REPLACE_STRATEGY"}
    if action in forbidden:
        return {"action": action, "applied": False, "effect": "PROPOSAL_ONLY"}
    return {"action": action, "applied": False, "effect": "NOT_AN_EXECUTION_ACTION"}
