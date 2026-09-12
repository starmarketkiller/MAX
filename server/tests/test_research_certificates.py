"""Quantitative Integrity Web Bridge v1 — Test Validity Certificate v2 ingest.

Copre l'acceptance esplicito del task:
 * importa almeno i due certificati ADX_RSI gia' prodotti (fixture = i
   file .json REALI scritti dall'EA in Common\\Files\\NEXUS\\certificates
   durante la regression del task precedente, non dati sintetici)
 * il backend restituisce entrambi i run separati
 * stesso config_fingerprint, run_id diversi
 * entrambi PASS
 * funnel 118/117/1 preservato esattamente
 * idempotenza: un secondo ingest dello stesso run_id non duplica la riga
   ne' la sovrascrive
 * git_commit=UNKNOWN resta UNKNOWN (nessun dato inventato)
 * nessuna regressione sugli altri endpoint /api/local_bridge/*
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as backend

BRIDGE = {"X-Nexus-Token": "test-token"}
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "research_certificates"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "certificates.db"))
    backend.init_db()
    with TestClient(backend.app) as value:
        login = value.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        value.user_headers = {"Authorization": f"Bearer {login.json()['token']}"}
        yield value


def _enroll(client, host):
    """Arruola un host LocalBridge, stesso flusso di test_command_contract.py."""
    client.post("/api/local_bridge/heartbeat", headers=BRIDGE,
               json={"host_id": host, "version": "1.0.0", "os": "windows"})
    approved = client.post(f"/api/local_bridge/hosts/{host}/enroll",
                           headers=client.user_headers, json={"approve": True})
    assert approved.status_code == 200, approved.text
    hb = client.post("/api/local_bridge/heartbeat", headers=BRIDGE,
                     json={"host_id": host, "version": "1.0.0", "os": "windows"})
    assert hb.status_code == 200


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _ingest(client, host, cert, source_file=None):
    return client.post("/api/local_bridge/certificates/ingest", headers=BRIDGE,
                       json={"host_id": host, "certificate": cert, "source_file": source_file})


def test_ingest_rifiuta_host_non_registrato(client):
    cert = _load_fixture("adx_rsi_run1.json")
    resp = _ingest(client, "host-mai-visto", cert)
    assert resp.status_code == 403


def test_ingest_rifiuta_token_mancante(client):
    _enroll(client, "host-cert-01")
    cert = _load_fixture("adx_rsi_run1.json")
    resp = client.post("/api/local_bridge/certificates/ingest",
                       json={"host_id": "host-cert-01", "certificate": cert})
    assert resp.status_code == 401


def test_ingest_rifiuta_certificato_senza_run_id(client):
    _enroll(client, "host-cert-01")
    resp = _ingest(client, "host-cert-01", {"strategy": "ADX_RSI"})
    assert resp.status_code == 422


def test_importa_i_due_certificati_adx_rsi_reali(client):
    """Acceptance principale: due run ADX_RSI reali, run_id diversi, stesso
    config_fingerprint, funnel 118/117/1 preservato, entrambi PASS."""
    _enroll(client, "host-cert-01")
    run1 = _load_fixture("adx_rsi_run1.json")
    run2 = _load_fixture("adx_rsi_run2.json")

    assert run1["run_id"] != run2["run_id"]
    assert run1["config_fingerprint"] == run2["config_fingerprint"]

    r1 = _ingest(client, "host-cert-01", run1, source_file="GOLD_2026.06.01_00-00-00_sel1.json")
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "ingested"
    r2 = _ingest(client, "host-cert-01", run2, source_file="GOLD_2026.06.01_00-00-00_sel1_r001.json")
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "ingested"

    listing = client.get("/api/research/certificates", headers=client.user_headers).json()
    assert listing["count"] == 2
    run_ids = {c["run_id"] for c in listing["certificates"]}
    assert run_ids == {run1["run_id"], run2["run_id"]}

    d1 = client.get(f"/api/research/certificates/{run1['run_id']}",
                    headers=client.user_headers).json()
    d2 = client.get(f"/api/research/certificates/{run2['run_id']}",
                    headers=client.user_headers).json()

    # run separati, stesso config_fingerprint
    assert d1["run_id"] != d2["run_id"]
    assert d1["config_fingerprint"] == d2["config_fingerprint"] == run1["config_fingerprint"]

    # entrambi PASS
    assert d1["verdict"] == "PASS"
    assert d2["verdict"] == "PASS"

    # funnel 118/117/1 preservato esattamente su entrambi (nessuna
    # ri-classificazione lato backend)
    for d in (d1, d2):
        assert d["funnel"] == {"generated": 118, "blocked": 117, "open_attempt": 1,
                               "opened": 1, "broker_reject": 0}
        assert d["gate_reason_counts"] == {"OPEN_POSITION": 117}

    # provenance: git_commit=UNKNOWN resta UNKNOWN, mai inventato/alterato
    assert d1["git_commit"] == "UNKNOWN"
    assert d1["git_commit_provenance"] == "unavailable_at_runtime_no_build_stamping"

    # raw provenance intatta (documento originale conservato verbatim)
    assert d1["raw"] == run1
    assert d2["raw"] == run2


def test_idempotenza_su_run_id_nessun_duplicato(client):
    _enroll(client, "host-cert-01")
    cert = _load_fixture("adx_rsi_run1.json")

    first = _ingest(client, "host-cert-01", cert)
    assert first.json()["status"] == "ingested"
    second = _ingest(client, "host-cert-01", cert)
    assert second.status_code == 200
    assert second.json()["status"] == "already_ingested"

    listing = client.get("/api/research/certificates", headers=client.user_headers).json()
    assert listing["count"] == 1


def test_idempotenza_non_sovrascrive_con_payload_diverso(client):
    """Un run_id gia' presente resta immutabile anche se arriva un payload
    diverso con lo stesso id (first-write-wins, mai un verdetto mutato)."""
    _enroll(client, "host-cert-01")
    cert = _load_fixture("adx_rsi_run1.json")
    _ingest(client, "host-cert-01", cert)

    tampered = dict(cert)
    tampered["verdict"] = "FAIL"
    resp = _ingest(client, "host-cert-01", tampered)
    assert resp.json()["status"] == "already_ingested"

    detail = client.get(f"/api/research/certificates/{cert['run_id']}",
                        headers=client.user_headers).json()
    assert detail["verdict"] == "PASS"


def test_latest_e_latest_valid_only(client):
    _enroll(client, "host-cert-01")
    run1 = _load_fixture("adx_rsi_run1.json")
    run2 = _load_fixture("adx_rsi_run2.json")
    fail_run = dict(run1)
    fail_run["run_id"] = run1["run_id"] + "_synthetic_fail"
    fail_run["verdict"] = "FAIL"
    fail_run["fail_reasons"] = "FUNNEL_NOT_RECONCILED(test)"

    _ingest(client, "host-cert-01", run1)
    _ingest(client, "host-cert-01", run2)
    _ingest(client, "host-cert-01", fail_run)

    latest = client.get("/api/research/certificates/latest", headers=client.user_headers).json()
    assert latest["run_id"] == fail_run["run_id"]

    latest_valid = client.get("/api/research/certificates/latest?valid_only=true",
                              headers=client.user_headers).json()
    assert latest_valid["run_id"] == run2["run_id"]
    assert latest_valid["verdict"] == "PASS"


def test_funnel_endpoint(client):
    _enroll(client, "host-cert-01")
    run1 = _load_fixture("adx_rsi_run1.json")
    _ingest(client, "host-cert-01", run1)

    funnel = client.get(f"/api/research/certificates/{run1['run_id']}/funnel",
                        headers=client.user_headers).json()
    assert funnel["funnel"] == {"generated": 118, "blocked": 117, "open_attempt": 1,
                                "opened": 1, "broker_reject": 0}
    assert funnel["gate_reason_counts"] == {"OPEN_POSITION": 117}
    assert funnel["verdict"] == "PASS"


def test_certificate_not_found(client):
    resp = client.get("/api/research/certificates/does-not-exist",
                      headers=client.user_headers)
    assert resp.status_code == 404
    resp2 = client.get("/api/research/certificates/does-not-exist/funnel",
                       headers=client.user_headers)
    assert resp2.status_code == 404


def test_list_richiede_autenticazione(client):
    # `client` ha gia' effettuato login nel fixture (cookie di sessione
    # persistente su TestClient) - la richiesta va isolata senza quel cookie
    # per verificare davvero il caso non autenticato.
    resp = client.get("/api/research/certificates", cookies={"nexus_session": ""})
    assert resp.status_code in (401, 403)
