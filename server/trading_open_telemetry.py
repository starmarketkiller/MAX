"""Opening telemetry from the EA: request, acceptance, deal, live position.

NEXUS-OTEL-001. The EA (NXS_OpenTelemetry.mqh) reports three kinds of event,
each with its own idempotency key. This module validates them, stores them
once (UNIQUE account_login + event_key, persisted in SQLite) and projects the
lifecycle of every opening attempt.

It never sends, retries or modifies an order. A position counts as open only
when MT5 reported a deal IN and the terminal still saw the position.
"""
from __future__ import annotations

import json
import re

KINDS = {"order_result", "deal_in", "position_snapshot"}
KEY_PREFIX = {"order_result": ("ord:", "req:"), "deal_in": ("deal:",),
              "position_snapshot": ("snap:",)}
KEY_RE = re.compile(r"^[a-z]+:[0-9:]{1,96}$")
ACCEPTED = {10008, 10009, 10010}          # PLACED, DONE, DONE_PARTIAL
RETCODE_NAMES = {10008: "PLACED", 10009: "DONE", 10010: "DONE_PARTIAL",
                 10004: "REQUOTE", 10006: "REJECT", 10012: "TIMEOUT",
                 10014: "INVALID_VOLUME", 10015: "INVALID_PRICE", 10016: "INVALID_STOPS",
                 10018: "MARKET_CLOSED", 10019: "NO_MONEY", 10020: "PRICE_CHANGED",
                 10021: "PRICE_OFF"}
DEFAULT_AMBIGUOUS_AFTER_SEC = 120
VOLUME_EPS = 1e-9

DDL = """
CREATE TABLE IF NOT EXISTS ea_execution_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    account_login INTEGER NOT NULL,
    event_key     TEXT NOT NULL,
    kind          TEXT NOT NULL,
    order_ticket  INTEGER,
    deal_ticket   INTEGER,
    position_id   INTEGER,
    symbol        TEXT,
    magic         INTEGER,
    payload       TEXT NOT NULL,
    received_at   REAL NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ea_execution_events_once
    ON ea_execution_events(account_login, event_key);
CREATE INDEX IF NOT EXISTS idx_ea_execution_events_position
    ON ea_execution_events(account_login, position_id);
"""


class InvalidEvent(ValueError):
    pass


def _int(value, field, required=False):
    if value in (None, ""):
        if required:
            raise InvalidEvent(f"{field} missing")
        return None
    if isinstance(value, bool):
        raise InvalidEvent(f"{field} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise InvalidEvent(f"{field} must be an integer") from None
    if number < 0:
        raise InvalidEvent(f"{field} must not be negative")
    return number


def _float(value, field):
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise InvalidEvent(f"{field} must be a number")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise InvalidEvent(f"{field} must be a number") from None


def validate(event):
    """Return the normalized event or raise InvalidEvent."""
    if not isinstance(event, dict):
        raise InvalidEvent("event must be an object")
    kind = event.get("kind")
    if kind not in KINDS:
        raise InvalidEvent("unknown kind")
    key = str(event.get("event_key") or "")
    if not KEY_RE.match(key) or not key.startswith(KEY_PREFIX[kind]):
        raise InvalidEvent("event_key does not match kind")
    login = _int(event.get("account_login"), "account_login", required=True)
    if login == 0:
        raise InvalidEvent("account_login must identify an account")
    clean = dict(event)
    clean["account_login"] = login
    for field in ("order", "deal", "position_id", "magic", "ea_magic", "retcode",
                  "request_id", "deal_time_msc", "position_time_msc"):
        if field in clean:
            clean[field] = _int(clean[field], field)
    for field in ("requested_volume", "filled_volume", "deal_volume", "position_volume",
                  "requested_price", "fill_price", "deal_price", "position_price", "sl", "tp"):
        if field in clean:
            clean[field] = _float(clean[field], field)
    if kind == "deal_in":
        for field in ("deal", "order", "position_id"):
            if not clean.get(field):
                raise InvalidEvent(f"{field} missing")
        if key != f"deal:{clean['deal']}":
            raise InvalidEvent("event_key must be deal:<deal>")
    if kind == "order_result" and key.startswith("ord:"):
        if not clean.get("order") or key != f"ord:{clean['order']}":
            raise InvalidEvent("event_key must be ord:<order>")
    if kind == "position_snapshot" and not clean.get("position_id"):
        raise InvalidEvent("position_id missing")
    for flag in ("sent", "position_alive"):
        if flag in clean and not isinstance(clean[flag], bool):
            raise InvalidEvent(f"{flag} must be a boolean")
    return clean


def store(conn, event, received_at):
    """Insert once. Returns True when new, False when the key was already stored."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO ea_execution_events(account_login,event_key,kind,order_ticket,"
        "deal_ticket,position_id,symbol,magic,payload,received_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (event["account_login"], event["event_key"], event["kind"], event.get("order"),
         event.get("deal"), event.get("position_id"), event.get("symbol"), event.get("magic"),
         json.dumps(event, sort_keys=True), received_at))
    return cur.rowcount == 1


def load(conn, account_login=None, limit=2000):
    sql = "SELECT payload, received_at FROM ea_execution_events"
    args = []
    if account_login is not None:
        sql += " WHERE account_login=?"
        args.append(account_login)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    rows = []
    for row in conn.execute(sql, args).fetchall():
        event = json.loads(row[0])
        event["_received_at"] = row[1]
        rows.append(event)
    rows.reverse()
    return rows


def _position_key(event):
    return (event["account_login"], event.get("position_id"))


def project(events, now, closed_positions=(), ambiguous_after=DEFAULT_AMBIGUOUS_AFTER_SEC):
    """Lifecycle of each opening attempt and of each position seen by MT5."""
    closed = {tuple(item) for item in closed_positions}
    requests, deals, snapshots = [], {}, {}
    for event in events:
        if event["kind"] == "order_result":
            requests.append(event)
        elif event["kind"] == "deal_in":
            deals.setdefault(_position_key(event), []).append(event)
        else:
            snapshots[_position_key(event)] = event

    positions = {}
    for key in set(deals) | set(snapshots):
        items = sorted(deals.get(key, []), key=lambda d: (d.get("deal_time_msc") or 0, d["deal"]))
        snap = snapshots.get(key)
        latest = items[-1] if items else snap
        filled = sum(d.get("deal_volume") or 0.0 for d in items)
        alive_seen = any(d.get("position_alive") for d in items) or bool(snap)
        if key in closed:
            state = "CLOSED"
        elif alive_seen:
            state = "POSITION_OPEN"
        else:
            state = "DEAL_EXECUTED"
        positions[key] = {
            "account_login": key[0], "position_id": key[1],
            "symbol": latest.get("symbol"), "side": latest.get("side"),
            "magic": latest.get("magic"), "strategy": latest.get("strategy") or None,
            "orders": sorted({d["order"] for d in items}),
            "deals": [d["deal"] for d in items],
            "filled_volume": round(filled, 8) if items else None,
            "position_volume": latest.get("position_volume"),
            "sl": latest.get("sl"), "tp": latest.get("tp"),
            "open_price": latest.get("position_price") or (items[0].get("deal_price") if items else None),
            "state": state,
            "confirmed_by": ("deal+terminal" if any(d.get("position_alive") for d in items)
                             else "boot_snapshot" if snap else "deal_only"),
        }

    deals_by_order = {}
    for items in deals.values():
        for deal in items:
            deals_by_order.setdefault((deal["account_login"], deal["order"]), []).append(deal)

    attempts = []
    matched_positions = set()
    for req in requests:
        order = req.get("order") or 0
        retcode = req.get("retcode")
        record = {
            "event_key": req["event_key"], "account_login": req["account_login"],
            "order": order or None, "symbol": req.get("symbol"), "side": req.get("side"),
            "strategy": req.get("strategy") or None, "magic": req.get("magic"),
            "requested_volume": req.get("requested_volume"),
            "sl": req.get("sl"), "tp": req.get("tp"),
            "request_sent": bool(req.get("sent")),
            "retcode": retcode, "retcode_name": RETCODE_NAMES.get(retcode),
            "sent_at": req.get("sent_at"), "retry_allowed": False,
            "deals": [], "filled_volume": 0.0, "position_id": None,
        }
        if not req.get("sent"):
            record["stage"] = "REQUEST_BLOCKED"
            record["reason"] = req.get("blocked_reason") or None
        elif retcode not in ACCEPTED or not order:
            record["stage"] = "REQUEST_REJECTED"
        else:
            fills = deals_by_order.get((req["account_login"], order), [])
            record["deals"] = [d["deal"] for d in fills]
            record["filled_volume"] = round(sum(d.get("deal_volume") or 0.0 for d in fills), 8)
            if not fills:
                age = now - (req.get("_received_at") or now)
                record["stage"] = "ACCEPTED_NO_FILL" if age > ambiguous_after else "ORDER_ACCEPTED"
            else:
                pos_key = (req["account_login"], fills[0]["position_id"])
                matched_positions.add(pos_key)
                record["position_id"] = pos_key[1]
                position = positions.get(pos_key, {})
                requested = req.get("requested_volume") or 0.0
                if record["filled_volume"] + VOLUME_EPS < requested:
                    record["stage"] = "PARTIALLY_FILLED"
                elif position.get("state") in {"POSITION_OPEN", "CLOSED"}:
                    record["stage"] = position["state"]
                else:
                    record["stage"] = "DEAL_EXECUTED"
                record["position_state"] = position.get("state")
        attempts.append(record)

    for key, position in positions.items():
        position["order_reported"] = key in matched_positions

    counts = {}
    for record in attempts:
        counts[record["stage"]] = counts.get(record["stage"], 0) + 1
    open_positions = [p for p in positions.values() if p["state"] == "POSITION_OPEN"]
    return {
        "source": "ea_execution_events", "order_owner": "MQL5_EA",
        "sends_orders": False, "retry_allowed": False,
        "connected": bool(events),
        "attempts": attempts,
        "positions": sorted(positions.values(), key=lambda p: (p["account_login"], p["position_id"] or 0)),
        "counts": counts,
        "open_positions": len(open_positions),
        "ambiguous": [r["event_key"] for r in attempts if r["stage"] == "ACCEPTED_NO_FILL"],
        "unreported_orders": [p["position_id"] for p in positions.values() if not p["order_reported"]],
        "note": "an opening counts only after an MT5 deal and a terminal position; NEXUS never retries",
    }


def closed_positions(conn):
    """(account_login, position_id) whose close is already in the trade ledger."""
    out = set()
    for (uid,) in conn.execute(
            "SELECT DISTINCT trade_uid FROM trade_events WHERE event IN ('close','resync')"):
        account, _, position = str(uid or "").partition(":")
        if account.isdigit() and position.isdigit():
            out.add((int(account), int(position)))
    return out
