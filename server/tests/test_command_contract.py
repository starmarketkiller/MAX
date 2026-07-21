"""PR8 — test contratto comandi (stati, lease/retry/dead-letter, idempotenza)."""
import os
import sqlite3
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as backend
import command_contract as cc

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOKEN = {"X-Nexus-Token": "test-token"}


@pytest.fixture()
def client():
    with TestClient(backend.app) as c:
        yield c


def _auth(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    tok = r.json().get("token")
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def _db():
    conn = sqlite3.connect(backend.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------------------------------- contratto puro ---------
def test_states_and_transitions():
    assert cc.TERMINAL <= cc.STATES
    assert cc.can_transition(cc.PENDING, cc.LEASED)
    assert not cc.can_transition(cc.SUCCEEDED, cc.PENDING)   # terminale


def test_lease_increments_attempts_and_sets_expiry():
    c = cc.build_envelope("RESTART_EA", {"host_id": "h"}, {})
    c = cc.lease(c, now_ts=1000, lease_seconds=60)
    assert c["status"] == cc.LEASED and c["attempts"] == 1 and c["lease_until"] == 1060


def test_reclaim_returns_to_pending_then_dead_letters():
    c = cc.build_envelope("X", {"host_id": "h"}, {})
    c = cc.lease(c, 1000)
    assert cc.reclaim_if_expired_lease(c, 2000)["status"] == cc.PENDING
    c["attempts"] = c["max_attempts"]
    dl = cc.reclaim_if_expired_lease(c, 2000)
    assert dl["status"] == cc.FAILED_FINAL and cc.is_dead_letter(dl)


def test_complete_paths():
    c = cc.build_envelope("X", {"host_id": "h"}, {})
    c = cc.lease(c, 1000)
    assert cc.complete(c, ok=True)["status"] == cc.SUCCEEDED
    assert cc.complete(c, ok=False)["status"] == cc.FAILED_RETRYABLE
    c["attempts"] = c["max_attempts"]
    assert cc.complete(c, ok=False)["status"] == cc.FAILED_FINAL


def test_idempotency_key_deterministic():
    a = cc.idempotency_key("A", {"host_id": "h"}, {"p": 1})
    b = cc.idempotency_key("A", {"host_id": "h"}, {"p": 1})
    assert a == b
    assert a != cc.idempotency_key("A", {"host_id": "h"}, {"p": 2})


def test_expire_past_ttl():
    c = cc.build_envelope("X", {"host_id": "h"}, {}, ttl_seconds=0)
    out = cc.expire_if_past_ttl(c, cc.now_iso())
    assert out["status"] == cc.EXPIRED


# --------------------------------------------------- endpoint ---------------
def test_enqueue_is_idempotent(client):
    h = _auth(client)
    p = {"host_id": "hostA", "action": "RESTART_EA", "payload": {"k": 1}}
    r1 = client.post("/api/local_bridge/enqueue", json=p, headers=h).json()
    r2 = client.post("/api/local_bridge/enqueue", json=p, headers=h).json()
    assert r1["id"] == r2["id"] and r2.get("idempotent")


def test_poll_leases_and_ack_succeeds(client):
    h = _auth(client)
    client.post("/api/local_bridge/enqueue",
                json={"host_id": "hostB", "action": "PING", "payload": {}}, headers=h)
    polled = client.get("/api/local_bridge/poll?host_id=hostB", headers=TOKEN).json()
    assert polled["action"] == "PING"
    with _db() as c:
        row = c.execute("SELECT canonical_status, attempts, lease_until FROM bridge_commands WHERE id=?",
                        (polled["id"],)).fetchone()
    assert row["canonical_status"] == cc.LEASED and row["attempts"] == 1 and row["lease_until"]
    client.post("/api/local_bridge/ack", json={"id": polled["id"], "ok": True}, headers=TOKEN)
    with _db() as c:
        assert c.execute("SELECT canonical_status FROM bridge_commands WHERE id=?",
                         (polled["id"],)).fetchone()["canonical_status"] == cc.SUCCEEDED


def test_ack_error_retries_then_dead_letters(client):
    h = _auth(client)
    r = client.post("/api/local_bridge/enqueue",
                    json={"host_id": "hostC", "action": "FLAKY", "payload": {}}, headers=h).json()
    cid = r["id"]
    for _ in range(3):   # max_attempts=3: poll+ack(error) tre volte
        client.get("/api/local_bridge/poll?host_id=hostC", headers=TOKEN)
        client.post("/api/local_bridge/ack", json={"id": cid, "ok": False, "error": "boom"}, headers=TOKEN)
    with _db() as c:
        row = c.execute("SELECT canonical_status, dead_letter_reason FROM bridge_commands WHERE id=?",
                        (cid,)).fetchone()
    assert row["canonical_status"] == cc.FAILED_FINAL and row["dead_letter_reason"] == "max_attempts"


def test_commands_endpoint_lists_dead_letter(client):
    h = _auth(client)
    r = client.get("/api/local_bridge/commands", headers=h)
    assert r.status_code == 200 and "dead_letter" in r.json()


# --------------------------------------------------- dedup worker -----------
def test_worker_is_deduplicated():
    lb = os.path.join(ROOT, "LocalBridge", "nexus_local_worker.py")
    src = open(lb, encoding="utf-8").read()
    # lo shim delega alla fonte canonica, non contiene piu' la logica duplicata
    assert "runpy.run_path" in src and "server" in src
    assert len(src) < 1000   # shim piccolo, non la copia da 11KB


def test_deployment_manifest_valid():
    import json
    m = json.load(open(os.path.join(ROOT, "contracts", "deployment-manifest.json")))
    assert m["schema_version"] == 1
    assert set(m["command_states"]) <= cc.STATES | {cc.PENDING}
