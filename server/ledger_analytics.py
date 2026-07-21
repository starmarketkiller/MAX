"""Read models analitici derivati esclusivamente dal trade event ledger."""
from __future__ import annotations

import json
import sqlite3
from typing import Any


DERIVED_PROVENANCE = "DERIVED_ANALYTICS"
LEGACY_PROVENANCE = "LEGACY_UNVERIFIED"


def _payload(row: sqlite3.Row) -> dict[str, Any]:
    try:
        value = json.loads(row["payload"] or "{}")
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def authoritative_trades(conn: sqlite3.Connection, limit: int | None = None) -> list[dict[str, Any]]:
    """Materializza un trade per UID dal ledger immutabile.

    ``close`` e' l'osservazione live preferita. ``resync`` e' usato solo se il
    close non esiste. Gli UID sintetici creati per payload pre-ledger restano
    quarantinati e non possono diventare verita' analitica.
    """
    rows = conn.execute(
        "SELECT * FROM trade_events WHERE event IN ('close','resync') "
        "ORDER BY created_at DESC, id DESC"
    ).fetchall()
    chosen: dict[str, sqlite3.Row] = {}
    for row in rows:
        uid = str(row["trade_uid"] or "")
        if not uid or uid.startswith("legacy:"):
            continue
        current = chosen.get(uid)
        if current is None or (row["event"] == "close" and current["event"] != "close"):
            chosen[uid] = row

    out = []
    for uid, row in chosen.items():
        data = _payload(row)
        ticket = data.get("ticket") or data.get("deal") or data.get("id") or row["position_id"]
        out.append({
            "trade_uid": uid,
            "ticket": ticket,
            "symbol": row["symbol"] or data.get("symbol"),
            "strategy": data.get("strategy"),
            "side": data.get("side") or data.get("type"),
            "lots": row["lots"] if row["lots"] is not None else data.get("volume"),
            "openPrice": data.get("openPrice") or data.get("open_price"),
            "closePrice": data.get("closePrice") or data.get("close_price"),
            "pnl": row["pnl"],
            "openTime": data.get("openTime") or data.get("open_time"),
            "closeTime": data.get("closeTime") or data.get("close_time"),
            "reason": row["reason"] or data.get("reason"),
            "partial_count": row["partial_count"],
            "volume_out": row["volume_out"],
            "source_event": row["event"],
            "source_provenance": (
                "OBSERVED_LIVE" if row["event"] == "close" else "RECONSTRUCTED_HISTORY"
            ),
            "provenance": DERIVED_PROVENANCE,
            "recorded_at": row["created_at"],
        })
    out.sort(key=lambda item: (item["recorded_at"] or 0), reverse=True)
    return out[:limit] if limit is not None else out


def quarantine_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    """Conta lo storico che non possiede evidenza terminale verificabile."""
    verified = {
        row["trade_uid"] for row in conn.execute(
            "SELECT DISTINCT trade_uid FROM trade_events "
            "WHERE event IN ('close','resync') AND trade_uid IS NOT NULL "
            "AND trade_uid NOT LIKE 'legacy:%'"
        )
    }
    legacy_events = conn.execute(
        "SELECT COUNT(DISTINCT trade_uid) n FROM trade_events "
        "WHERE event IN ('close','resync') AND trade_uid LIKE 'legacy:%'"
    ).fetchone()["n"]
    unverified_rows = 0
    for row in conn.execute("SELECT trade_uid FROM trades"):
        if not row["trade_uid"] or row["trade_uid"] not in verified:
            unverified_rows += 1
    return {
        "provenance": LEGACY_PROVENANCE,
        "excluded": True,
        "trade_rows": unverified_rows,
        "legacy_event_uids": legacy_events or 0,
        "reason": "Nessun evento terminale verificabile nel ledger",
    }


def provenance(conn: sqlite3.Connection) -> dict[str, Any]:
    return {
        "metric": DERIVED_PROVENANCE,
        "source": "trade_events",
        "terminal_event_policy": "close_preferred_resync_fallback",
        "legacy": quarantine_summary(conn),
    }
