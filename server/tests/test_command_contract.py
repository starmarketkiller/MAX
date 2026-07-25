import sqlite3
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as backend
import command_contract as cc

BRIDGE = {"X-Nexus-Token": "test-token"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "commands.db"))
    backend.init_db()
    with TestClient(backend.app) as value:
        login = value.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        value.user_headers = {"Authorization": f"Bearer {login.json()['token']}"}
        yield value


def register(client, host):
    """Arruola un host: richiesta dall'host + approvazione dell'operatore.

    AUD0-SEC-010: prima il solo heartbeat creava l'host. Chiunque avesse il
    token condiviso poteva quindi registrare o impersonare host arbitrari.
    Il primo heartbeat ora apre una richiesta e riceve 403 finché un
    operatore non la approva.
    """
    first = client.post("/api/local_bridge/heartbeat", headers=BRIDGE,
                        json={"host_id": host, "version": "2.0.0", "os": "test"})
    assert first.status_code == 403
    assert first.json()["detail"]["enrollment_state"] == "PENDING"

    approved = client.post(f"/api/local_bridge/hosts/{host}/enroll",
                           headers=client.user_headers, json={"approve": True})
    assert approved.status_code == 200, approved.text

    response = client.post("/api/local_bridge/heartbeat", headers=BRIDGE,
                           json={"host_id": host, "version": "2.0.0", "os": "test"})
    assert response.status_code == 200


def test_host_non_arruolato_non_riceve_comandi(client):
    """Un host sconosciuto non deve poter fare polling (AUD0-SEC-010)."""
    heartbeat = client.post("/api/local_bridge/heartbeat", headers=BRIDGE,
                            json={"host_id": "host-intruso", "version": "x", "os": "y"})
    assert heartbeat.status_code == 403

    # La richiesta di arruolamento resta però registrata e visibile.
    hosts = client.get("/api/local_bridge/hosts", headers=client.user_headers).json()
    assert "host-intruso" in hosts["pending"]


def test_host_revocato_viene_respinto(client):
    register(client, "host-da-revocare")
    revoked = client.post("/api/local_bridge/hosts/host-da-revocare/enroll",
                          headers=client.user_headers,
                          json={"approve": False, "reason": "macchina dismessa"})
    assert revoked.json()["enrollment_state"] == "REVOKED"

    resp = client.post("/api/local_bridge/heartbeat", headers=BRIDGE,
                       json={"host_id": "host-da-revocare", "version": "2.0.0"})
    assert resp.status_code == 403
    assert resp.json()["detail"]["enrollment_state"] == "REVOKED"


def test_revoca_host_richiede_motivazione(client):
    register(client, "host-motivazione")
    resp = client.post("/api/local_bridge/hosts/host-motivazione/enroll",
                       headers=client.user_headers, json={"approve": False})
    assert resp.status_code == 422


def enqueue(client, host, key="key-1", max_attempts=3):
    return client.post("/api/local_bridge/enqueue", headers=client.user_headers, json={
        "command_type": "PING", "target": {"host_id": host},
        "payload": {}, "idempotency_key": key, "max_attempts": max_attempts,
    })


def test_contract_enums_and_timestamps():
    assert cc.command_type("ping") == "PING"
    assert "LEASED" in cc.STATUSES and "FAILED_FINAL" in cc.STATUSES
    assert "+00:00" in cc.iso_timestamp(0)


def test_duplicate_idempotency_and_wrong_host_isolation(client):
    register(client, "host-a")
    register(client, "host-b")
    first = enqueue(client, "host-a").json()
    duplicate = enqueue(client, "host-a").json()
    assert duplicate["duplicate"] is True and duplicate["command_id"] == first["command_id"]
    assert client.get("/api/local_bridge/poll", headers=BRIDGE, params={"host_id": "host-b"}).json()["command"] is None
    leased = client.get("/api/local_bridge/poll", headers=BRIDGE, params={"host_id": "host-a"}).json()
    assert leased["status"] == "LEASED" and leased["command_id"] == first["command_id"]


def test_ack_requires_matching_host_and_lease(client):
    register(client, "host-a")
    enqueue(client, "host-a")
    leased = client.get("/api/local_bridge/poll", headers=BRIDGE, params={"host_id": "host-a"}).json()
    bad = client.post("/api/local_bridge/ack", headers=BRIDGE, json={
        "command_id": leased["command_id"], "lease_id": leased["lease_id"],
        "host_id": "host-b", "status": "SUCCEEDED",
    })
    assert bad.status_code == 409
    good = client.post("/api/local_bridge/ack", headers=BRIDGE, json={
        "command_id": leased["command_id"], "lease_id": leased["lease_id"],
        "host_id": "host-a", "status": "SUCCEEDED", "result": {"pong": True},
    })
    assert good.status_code == 200 and good.json()["status"] == "SUCCEEDED"


def test_expired_lease_retries_then_dead_letters(client):
    register(client, "host-a")
    command_id = enqueue(client, "host-a", max_attempts=2).json()["command_id"]
    first = client.get("/api/local_bridge/poll", headers=BRIDGE, params={"host_id": "host-a"}).json()
    with sqlite3.connect(backend.DB_PATH) as connection:
        connection.execute("UPDATE bridge_commands SET lease_expires_at=0 WHERE id=?", (command_id,))
    second = client.get("/api/local_bridge/poll", headers=BRIDGE, params={"host_id": "host-a"}).json()
    assert second["command_id"] == command_id and second["lease_id"] != first["lease_id"]
    failed = client.post("/api/local_bridge/ack", headers=BRIDGE, json={
        "command_id": command_id, "lease_id": second["lease_id"], "host_id": "host-a",
        "status": "FAILED_RETRYABLE", "error": "boom",
    })
    assert failed.json()["status"] == "FAILED_FINAL"
    status = client.get("/api/local_bridge/status", headers=client.user_headers).json()
    assert status["commands"][0]["status"] == "FAILED_FINAL"


def test_ea_command_is_leased_not_consumed(client):
    """Il polling prende il comando in LEASE, non lo consuma.

    Sostituisce il test precedente, che verificava il comportamento
    poll-consume: l'audit lo ha classificato P0 (AUD0-CMD-001,
    AUD0-BE-CMD-006) perché `DELIVERED` prova solo che l'EA ha ricevuto il
    comando, mentre il record veniva già rimosso dalla coda. Un crash
    successivo lo perdeva senza che nessuno lo sapesse.
    """
    created = client.post("/api/command", headers=client.user_headers, json={
        "action": "close_position",
        "target": {"account_id": "900001", "symbol": "XAUUSD"},
        "payload": {"ticket": 42},
        "confirm": True, "reason": "chiusura richiesta dal test",
    })
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["status"] == "PENDING" and body["command_id"] == body["id"]

    pending = client.get(f"/api/command/{body['id']}", headers=client.user_headers)
    assert pending.json()["status"] == "PENDING"
    assert pending.json()["terminal"] is False

    leased = client.get("/api/ea/command", headers=BRIDGE,
                        params={"account_id": "900001", "symbol": "XAUUSD"})
    assert leased.status_code == 200
    leased_body = leased.json()
    assert leased_body["status"] == "LEASED"
    assert leased_body["lease_id"]
    assert leased_body["ticket"] == 42          # payload appiattito
    assert "payload" not in leased_body

    status = client.get(f"/api/command/{body['id']}", headers=client.user_headers).json()
    assert status["status"] == "LEASED"
    # Il punto centrale: consegnato != eseguito.
    assert status["terminal"] is False
    assert status["broker_confirmed"] is False
    assert status["delivered_at"] and "+00:00" in status["delivered_at"]

    # Solo l'ACK dell'EA porta il comando a uno stato terminale.
    ack = client.post("/api/ea/command/ack", headers=BRIDGE, json={
        "command_id": body["id"], "lease_id": leased_body["lease_id"],
        "status": "SUCCEEDED", "retcode": 10009,
    })
    assert ack.json()["status"] == "SUCCEEDED"
    final = client.get(f"/api/command/{body['id']}", headers=client.user_headers).json()
    assert final["terminal"] is True and final["broker_confirmed"] is True


def test_ea_command_status_migration_is_additive(tmp_path, monkeypatch):
    path = tmp_path / "legacy-ea-commands.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE ea_commands (id TEXT PRIMARY KEY, action TEXT, "
                           "payload TEXT, created_at REAL, consumed INTEGER DEFAULT 0)")
        connection.execute("INSERT INTO ea_commands VALUES('old','pause','{}',1,1)")
    monkeypatch.setattr(backend, "DB_PATH", str(path))
    backend.init_db()
    backend.init_db()
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT status,delivered_at FROM ea_commands WHERE id='old'").fetchone()
    # I record storici marcati "consumati" vengono riportati a LEASED: la sola
    # verità dimostrabile è che erano stati consegnati, non eseguiti
    # (AUD0-CMD-001). Promuoverli a un esito positivo sarebbe una falsa prova.
    assert row == ("LEASED", None)
    with sqlite3.connect(path) as connection:
        applied = {r[0] for r in connection.execute("SELECT migration_id FROM schema_migrations")}
    assert "003_ea_command_lifecycle" in applied


def test_single_worker_source_and_manifest_checksums():
    root = Path(__file__).resolve().parents[2]
    assert (root / "LocalBridge" / "nexus_local_worker.py").exists()
    assert not (root / "server" / "nexus_local_worker.py").exists()
    manifest = json.loads((root / "deploy" / "deployment-manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1 and manifest["release_id"] == "nexus-3.60"
    for record in manifest["files"]:
        assert hashlib.sha256((root / record["path"]).read_bytes()).hexdigest() == record["sha256"]
