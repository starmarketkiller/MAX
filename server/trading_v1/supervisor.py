"""Read EA telemetry, reconcile it with the broker snapshot, and refuse a retry.

The EA owns signals, OrderSend and position management. A timeout is not a
failed order: until a deal or a position confirms it, the outcome stays
ambiguous and no second attempt is authorized.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from nexus_policy import RiskPolicyDenied, enforce_cap


def _empty():
    return {"schema": "trading-supervision-v1", "records": {}, "demo_account_verified": False,
            "live_enabled": False, "live_eligible": False, "audit": []}


class TradingSupervisor:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save(_empty())

    def _load(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, state):
        temp = self.path.with_name(f"{self.path.name}.{os.getpid()}.tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, self.path)

    def ingest(self, event):
        """Store an EA report. Never turns a signal into an order."""
        kind = event.get("kind")
        client_id = str(event.get("client_id") or "")
        if kind not in {"SIGNAL", "ORDER_REPORT", "DEAL", "POSITION"} or not client_id:
            raise ValueError("EA event needs kind and client_id")
        state = self._load()
        record = state["records"].get(client_id, {"client_id": client_id, "retry_allowed": False})
        record["strategy_id"] = event.get("strategy_id")
        record["last_kind"] = kind
        if kind == "SIGNAL":
            record["state"] = record.get("state") or "SIGNAL_ONLY"
        elif kind == "ORDER_REPORT" and event.get("ticket") and event.get("retcode") == 10009:
            record["state"] = "CONFIRMED"
            record["ticket"] = event["ticket"]
        elif kind in {"DEAL", "POSITION"} and (event.get("ticket") or event.get("position_id")):
            record["state"] = "CONFIRMED"
            record["ticket"] = event.get("ticket")
            record["position_id"] = event.get("position_id")
        else:
            record["state"] = "REPORTED"
        record["retry_allowed"] = False
        state["records"][client_id] = record
        state["audit"].append({"kind": kind, "client_id": client_id})
        self._save(state)
        return record

    def resolve_timeout(self, client_id, snapshot):
        """Reconcile orders, deals and positions before any retry. Timeout never retries."""
        found = _match(client_id, snapshot)
        state = self._load()
        record = state["records"].get(client_id, {"client_id": client_id})
        if found is None:
            record["state"] = "AMBIGUOUS"
        elif found["where"] == "orders":
            record["state"] = "IN_FLIGHT"
            record["ticket"] = found.get("ticket")
        else:
            record["state"] = "CONFIRMED"
            record["ticket"] = found.get("ticket")
            record["position_id"] = found.get("position_id")
            record["confirmed_by"] = found["where"]
        record["retry_allowed"] = False
        record["timeout"] = True
        state["records"][client_id] = record
        state["audit"].append({"kind": "TIMEOUT_RECONCILED", "client_id": client_id,
                                "state": record["state"]})
        self._save(state)
        return record

    def review_demo(self, report, approval):
        reasons = []
        if not report.get("connected"):
            reasons.append("TERMINAL_NOT_CONNECTED")
        if report.get("trade_mode") != "DEMO":
            reasons.append("NOT_A_DEMO_ACCOUNT")
        if str(report.get("login") or "") != str(approval.get("account_login") or ""):
            reasons.append("ACCOUNT_MISMATCH")
        actor = str(approval.get("verified_by") or "")
        if not actor or actor.startswith("jarvis"):
            reasons.append("IDENTITY_NOT_VERIFIED")
        verified = not reasons
        state = self._load()
        state["demo_account_verified"] = verified
        state["live_enabled"] = False
        state["audit"].append({"kind": "DEMO_REVIEW", "verified": verified, "reasons": reasons})
        self._save(state)
        return {"demo_account_verified": verified, "live_enabled": False,
                "trading_started": False, "reasons": reasons, "orders_sent": 0}

    def review_live(self, report, approval, limits, identity):
        reasons = []
        phrase = approval.get("phrase")
        if phrase == "ENABLE_LIVE" and not approval.get("approval_id"):
            reasons.append("PHRASE_IS_NOT_AUTHORIZATION")
        if not approval.get("approval_id"):
            reasons.append("MISSING_APPROVAL")
        actor = str(approval.get("actor") or "")
        if not actor or actor.startswith("jarvis"):
            reasons.append("HUMAN_APPROVAL_REQUIRED")
        if not identity.get("fingerprint"):
            reasons.append("IDENTITY_NOT_VERIFIED")
        if str(approval.get("account_login") or "") != str(report.get("login") or ""):
            reasons.append("ACCOUNT_MISMATCH")
        if report.get("trade_mode") != "LIVE" or not report.get("connected"):
            reasons.append("NOT_THE_LIVE_ACCOUNT")
        if not isinstance(limits, dict) or not limits:
            reasons.append("MISSING_RISK_LIMITS")
        else:
            try:
                for field, value in limits.items():
                    enforce_cap(field, value, hardened=True)
            except (RiskPolicyDenied, KeyError):
                reasons.append("RISK_LIMITS_REJECTED")
        eligible = not reasons
        state = self._load()
        state["live_eligible"] = eligible
        state["live_enabled"] = False
        state["audit"].append({"kind": "LIVE_REVIEW", "eligible": eligible, "reasons": reasons})
        self._save(state)
        return {"live_eligible": eligible, "live_enabled": False, "trading_started": False,
                "reasons": reasons, "orders_sent": 0}

    def projection(self):
        state = self._load()
        records = list(state["records"].values())
        return {"order_owner": "MQL5_EA", "accepts_orders": False,
                "demo_account_verified": state["demo_account_verified"],
                "live_enabled": False, "live_eligible": state["live_eligible"],
                "records": records, "audit": state["audit"]}


def _match(client_id, snapshot):
    for where in ("deals", "positions", "orders"):
        for item in snapshot.get(where) or []:
            if str(item.get("client_id") or "") == str(client_id):
                return {**item, "where": where}
    return None


def read_state(path):
    file = Path(path)
    if not path or not file.exists():
        return {"order_owner": "MQL5_EA", "accepts_orders": False, "connected": False,
                "demo_account_verified": False, "live_enabled": False, "records": []}
    state = json.loads(file.read_text(encoding="utf-8"))
    return {"order_owner": "MQL5_EA", "accepts_orders": False, "connected": False,
            "demo_account_verified": bool(state.get("demo_account_verified")),
            "live_enabled": False, "live_eligible": bool(state.get("live_eligible")),
            "records": list((state.get("records") or {}).values())}
