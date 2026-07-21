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
    response = client.post("/api/local_bridge/heartbeat", headers=BRIDGE,
                           json={"host_id": host, "version": "2.0.0", "os": "test"})
    assert response.status_code == 200


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


def test_single_worker_source_and_manifest_checksums():
    root = Path(__file__).resolve().parents[2]
    assert (root / "LocalBridge" / "nexus_local_worker.py").exists()
    assert not (root / "server" / "nexus_local_worker.py").exists()
    manifest = json.loads((root / "deploy" / "deployment-manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1 and manifest["release_id"] == "nexus-3.40"
    for record in manifest["files"]:
        assert hashlib.sha256((root / record["path"]).read_bytes()).hexdigest() == record["sha256"]
