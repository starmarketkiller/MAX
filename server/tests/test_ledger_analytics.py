import json
import sqlite3

import ledger_analytics as analytics


def _db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE trade_events (
          id INTEGER PRIMARY KEY, trade_uid TEXT, event TEXT, position_id INTEGER,
          magic INTEGER, symbol TEXT, pnl REAL, lots REAL, partial_count INTEGER,
          volume_out REAL, reason TEXT, payload TEXT, created_at REAL
        );
        CREATE TABLE trades (ticket INTEGER PRIMARY KEY, trade_uid TEXT, pnl REAL);
    """)
    return conn


def _event(conn, uid, event, pnl, created, strategy="MACD"):
    payload = {"ticket": int(uid.split(":")[-1]) if not uid.startswith("legacy:") else 9,
               "strategy": strategy, "side": "BUY", "closeTime": "2026-07-20T12:00:00"}
    conn.execute(
        "INSERT INTO trade_events(trade_uid,event,position_id,symbol,pnl,lots,reason,payload,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (uid, event, payload["ticket"], "GOLD", pnl, 0.1, "tp", json.dumps(payload), created),
    )


def test_close_is_preferred_and_mutable_trade_overwrite_is_ignored():
    conn = _db()
    _event(conn, "111:1", "close", 12.5, 1)
    _event(conn, "111:1", "resync", 999.0, 2)
    conn.execute("INSERT INTO trades VALUES(1,'111:1',-500.0)")

    rows = analytics.authoritative_trades(conn)

    assert len(rows) == 1
    assert rows[0]["pnl"] == 12.5
    assert rows[0]["source_event"] == "close"
    assert rows[0]["source_provenance"] == "OBSERVED_LIVE"
    assert rows[0]["provenance"] == "DERIVED_ANALYTICS"


def test_resync_only_trade_is_reconstructed_history():
    conn = _db()
    _event(conn, "111:2", "resync", -4.0, 3)

    row = analytics.authoritative_trades(conn)[0]

    assert row["pnl"] == -4.0
    assert row["source_provenance"] == "RECONSTRUCTED_HISTORY"


def test_legacy_history_is_quarantined_and_excluded():
    conn = _db()
    _event(conn, "legacy:9", "close", 100.0, 1)
    conn.execute("INSERT INTO trades VALUES(9,NULL,100.0)")

    assert analytics.authoritative_trades(conn) == []
    provenance = analytics.provenance(conn)
    assert provenance["metric"] == "DERIVED_ANALYTICS"
    assert provenance["legacy"]["provenance"] == "LEGACY_UNVERIFIED"
    assert provenance["legacy"]["trade_rows"] == 1
    assert provenance["legacy"]["legacy_event_uids"] == 1
    assert provenance["legacy"]["excluded"] is True
