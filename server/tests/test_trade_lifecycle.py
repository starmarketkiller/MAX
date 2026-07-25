"""PR1 — Trade lifecycle ledger: acceptance test lato backend.

Copre i 6 scenari di accettazione al livello verificabile via API
(la controparte MQL5 gira in Strategy Tester sull'agente desktop):

 1. one entry + one full exit
 2. two partial exits + final exit (il PnL del trade e' l'aggregato,
    mai l'ultimo spezzone)
 3. duplicate deal replay (stesso evento ripetuto -> nessun doppione)
 4. restart & history resync (resync dopo close: riga unica, PnL invariato)
 5. two positions on the same symbol (due trade logici indipendenti)
 6. exactly one TRADE_CLOSED (event='close') per trade logico

Piu': migrazione additiva della tabella `trades` su DB legacy.
"""
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

import app as backend

TOKEN = {"X-Nexus-Token": "test-token"}


@pytest.fixture()
def client():
    with TestClient(backend.app) as c:   # il context manager esegue init_db()
        yield c


def _db():
    conn = sqlite3.connect(backend.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _clear():
    with _db() as c:
        c.execute("DELETE FROM trades")
        c.execute("DELETE FROM trade_events")
        c.execute("DELETE FROM trade_reasons")


def _close_payload(pos_id, pnl, *, event="close", partial_count=0,
                   lots=0.10, volume_out=None, symbol="GOLD", strategy="MACD"):
    return {
        "ticket": pos_id, "magic": 990001, "symbol": symbol,
        "strategy": strategy, "side": "BUY", "lots": lots,
        "openPrice": 2400.0, "closePrice": 2410.0, "pnl": pnl,
        "openTime": "2026-07-20 10:00:00", "closeTime": "2026-07-20 12:00:00",
        "reason": "tp", "event": event, "positionId": pos_id,
        "tradeUid": f"111:{pos_id}", "partialCount": partial_count,
        "volumeOut": volume_out if volume_out is not None else lots,
    }


def _trades():
    with _db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM trades ORDER BY ticket")]


def _events(event=None):
    q = "SELECT * FROM trade_events"
    args = ()
    if event:
        q += " WHERE event=?"
        args = (event,)
    with _db() as c:
        return [dict(r) for r in c.execute(q, args)]


# ---------------------------------------------------------------- 1 ---------
def test_single_entry_single_exit(client):
    _clear()
    r = client.post("/api/ea/trade_reason", json=_close_payload(1001, 25.0),
                    headers=TOKEN)
    assert r.status_code == 200
    rows = _trades()
    assert len(rows) == 1
    assert rows[0]["pnl"] == 25.0
    assert rows[0]["trade_uid"] == "111:1001"
    assert rows[0]["partial_count"] == 0
    assert len(_events("close")) == 1


# ---------------------------------------------------------------- 2 ---------
def test_two_partials_plus_final_exit(client):
    """Il flusso nuovo: eventuali eventi parziali/pre-close NON toccano il
    PnL del trade; solo il close finale (aggregato dal ledger EA) e'
    autoritativo. Prima di PR1 l'ultimo spezzone sovrascriveva tutto."""
    _clear()
    # pre-push protezione (PnL flottante) — mai autoritativo
    client.post("/api/ea/trade_reason",
                json=_close_payload(2001, 4.10, event="close_request"),
                headers=TOKEN)
    # due uscite parziali (spezzoni da 3.30 e 2.20)
    client.post("/api/ea/trade_reason",
                json=_close_payload(2001, 3.30, event="partial",
                                    volume_out=0.03), headers=TOKEN)
    client.post("/api/ea/trade_reason",
                json=_close_payload(2001, 5.50, event="partial",
                                    volume_out=0.06), headers=TOKEN)
    rows = _trades()
    assert rows == [] or rows[0].get("pnl") is None  # nessun upsert dai parziali

    # chiusura finale aggregata dal ledger EA: pnl TOTALE, partial_count=2
    client.post("/api/ea/trade_reason",
                json=_close_payload(2001, 9.90, partial_count=2,
                                    volume_out=0.10), headers=TOKEN)
    rows = _trades()
    assert len(rows) == 1
    assert rows[0]["pnl"] == 9.90          # aggregato, non 5.50 (ultimo spezzone)
    assert rows[0]["partial_count"] == 2
    assert rows[0]["last_event"] == "close"
    assert len(_events("close")) == 1
    # gli eventi restano tutti nel registro (audit)
    assert len(_events("partial")) == 2
    assert len(_events("close_request")) == 1


# ---------------------------------------------------------------- 3 ---------
def test_duplicate_replay_is_idempotent(client):
    _clear()
    p = _close_payload(3001, 12.5)
    for _ in range(3):
        client.post("/api/ea/trade_reason", json=p, headers=TOKEN)
    assert len(_trades()) == 1
    assert _trades()[0]["pnl"] == 12.5
    assert len(_events("close")) == 1      # replay -> nessun secondo evento


# ---------------------------------------------------------------- 4 ---------
def test_restart_history_resync_no_duplicates(client):
    """Trade chiuso live, poi ri-pushato dal resync post-restart: la riga
    resta una, il PnL non cambia, il close resta uno."""
    _clear()
    client.post("/api/ea/trade_reason", json=_close_payload(4001, -7.7),
                headers=TOKEN)
    sync = dict(_close_payload(4001, -7.7, event="resync", partial_count=0))
    r = client.post("/api/ea/trade_history_sync", json={"trades": [sync, sync]},
                    headers=TOKEN)
    assert r.status_code == 200
    rows = _trades()
    assert len(rows) == 1
    assert rows[0]["pnl"] == -7.7
    assert len(_events("close")) == 1
    assert len(_events("resync")) == 1     # anche il resync e' exactly-once


def test_resync_of_offline_close_creates_single_row(client):
    """Trade chiuso mentre l'EA era offline: arriva SOLO via resync."""
    _clear()
    sync = _close_payload(4002, 3.14, event="resync", partial_count=1)
    for _ in range(2):
        client.post("/api/ea/trade_history_sync", json={"trades": [sync]},
                    headers=TOKEN)
    rows = _trades()
    assert len(rows) == 1
    assert rows[0]["pnl"] == 3.14
    assert rows[0]["partial_count"] == 1
    assert len(_events("resync")) == 1
    assert len(_events("close")) == 0      # mai chiuso live: nessun close


# ---------------------------------------------------------------- 5 ---------
def test_two_positions_same_symbol(client):
    _clear()
    client.post("/api/ea/trade_reason",
                json=_close_payload(5001, 10.0, symbol="GOLD"), headers=TOKEN)
    client.post("/api/ea/trade_reason",
                json=_close_payload(5002, -4.0, symbol="GOLD"), headers=TOKEN)
    rows = _trades()
    assert len(rows) == 2                  # chiave = position, mai symbol
    assert {r["trade_uid"] for r in rows} == {"111:5001", "111:5002"}
    assert len(_events("close")) == 2


# ---------------------------------------------------------------- 6 ---------
def test_exactly_one_trade_closed_per_logical_trade(client):
    _clear()
    p = _close_payload(6001, 8.0, partial_count=3)
    for _ in range(5):
        client.post("/api/ea/trade_reason", json=p, headers=TOKEN)
    client.post("/api/ea/trade_history_sync",
                json={"trades": [dict(p, event="resync")]}, headers=TOKEN)
    with _db() as c:
        n = c.execute("SELECT COUNT(*) FROM trade_events "
                      "WHERE trade_uid='111:6001' AND event='close'").fetchone()[0]
    assert n == 1


# ------------------------------------------------------- retrocompatibilita' -
def test_legacy_payload_without_event_is_not_authoritative(client):
    """AUD0-PROT-006: un payload SENZA campo `event` non e' una chiusura
    confermata dal broker.

    Questo test asseriva il contrario — che il default fosse `close`
    autoritativo — cioe' proprio il difetto segnalato: i push di richiesta
    chiusura portano prezzo RICHIESTO e P/L FLOTTANTE, e senza etichetta
    finivano a sovrascrivere i campi realizzati del trade.

    Il payload resta registrato nel ledger degli eventi (nulla va perso), ma
    la tabella `trades` la scrivono solo close/resync.
    """
    _clear()
    legacy = _close_payload(7001, 2.0)
    for k in ("event", "positionId", "tradeUid", "partialCount", "volumeOut"):
        legacy.pop(k)
    r = client.post("/api/ea/trade_reason", json=legacy, headers=TOKEN)
    assert r.status_code == 200
    assert _trades() == []

    with _db() as c:
        n = c.execute("SELECT COUNT(*) FROM trade_events "
                      "WHERE event='close_request'").fetchone()[0]
    assert n == 1

    # Con l'etichetta esplicita il trade viene invece scritto.
    confirmed = _close_payload(7001, 2.0)
    confirmed["event"] = "close"
    client.post("/api/ea/trade_reason", json=confirmed, headers=TOKEN)
    rows = _trades()
    assert len(rows) == 1
    assert rows[0]["pnl"] == 2.0


def test_unknown_trade_event_is_rejected(client):
    """AUD0-PROT-006: un'etichetta non riconosciuta non deve essere accettata
    in silenzio — il consumatore non saprebbe come interpretarla."""
    _clear()
    payload = _close_payload(7002, 3.0)
    payload["event"] = "definitivissimo"
    r = client.post("/api/ea/trade_reason", json=payload, headers=TOKEN)
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "UNKNOWN_TRADE_EVENT"
    assert _trades() == []


def test_migration_is_additive_and_idempotent(tmp_path, monkeypatch):
    """DB legacy (schema pre-PR1) -> init_db aggiunge le colonne senza
    toccare le righe esistenti; doppia esecuzione = nessun errore."""
    dbfile = tmp_path / "legacy.db"
    conn = sqlite3.connect(dbfile)
    conn.execute(
        "CREATE TABLE trades (ticket INTEGER PRIMARY KEY, symbol TEXT, "
        "strategy TEXT, side TEXT, lots REAL, open_price REAL, close_price REAL, "
        "pnl REAL, open_time TEXT, close_time TEXT, reason TEXT, raw TEXT, "
        "synced_at REAL)")
    conn.execute("INSERT INTO trades(ticket,symbol,pnl) VALUES (1,'GOLD',5.5)")
    conn.commit()
    conn.close()

    monkeypatch.setattr(backend, "DB_PATH", str(dbfile))
    backend.init_db()
    backend.init_db()   # idempotente

    conn = sqlite3.connect(dbfile)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(trades)")}
    assert {"position_id", "trade_uid", "partial_count",
            "volume_out", "last_event"} <= cols
    row = conn.execute("SELECT symbol, pnl, trade_uid FROM trades "
                       "WHERE ticket=1").fetchone()
    assert row == ("GOLD", 5.5, None)      # riga storica intatta
    conn.close()
