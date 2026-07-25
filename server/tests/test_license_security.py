"""Sicurezza del sottosistema licenze.

Copre AUD0-LIC-001..004, AUD0-BE-LIC-001..004, AUD0-DB-018.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app as backend
import nexus_security as sec


@pytest.fixture(scope="module")
def client():
    with TestClient(backend.app) as c:
        yield c


@pytest.fixture()
def auth(client):
    client.cookies.clear()
    resp = client.post("/api/auth/login",
                       json={"email": backend.ADMIN_USER,
                             "password": backend.ADMIN_PASSWORD})
    assert resp.status_code == 200, resp.text
    return client, {sec.CSRF_HEADER: resp.json()["csrf_token"]}


def _create(client, headers, **overrides):
    body = {"account": 12345, "plan": "standard", "days": 30,
            "client": "Cliente Test", "note": "creata dai test"}
    body.update(overrides)
    return client.post("/api/license/create", json=body, headers=headers)


# --------------------------------------------------------------------------- #
# La chiave è un segreto — AUD0-LIC-004 / AUD0-BE-LIC-001 / AUD0-FE-LIC-001
# --------------------------------------------------------------------------- #
def test_la_chiave_viene_mostrata_una_sola_volta(auth):
    client, headers = auth
    created = _create(client, headers)
    assert created.status_code == 200, created.text
    body = created.json()
    raw_key = body["key"]
    assert body["key_shown_once"] is True
    assert raw_key

    # Nessuna rotta di lettura deve restituire la chiave riutilizzabile.
    listing = client.get("/api/license/list").json()
    assert listing["licenses"]
    for lic in listing["licenses"]:
        assert "key" not in lic
        assert raw_key not in str(lic)
        assert lic["fingerprint"].endswith("…")


def test_la_chiave_non_e_salvata_in_chiaro(auth):
    client, headers = auth
    raw_key = _create(client, headers).json()["key"]
    with backend._conn() as c:
        rows = [dict(r) for r in c.execute("SELECT key, key_hash FROM licenses")]
    for row in rows:
        assert row["key"] != raw_key, "la chiave in chiaro è finita nel database"
        assert row["key_hash"] and len(row["key_hash"]) == 64


def test_la_verifica_funziona_con_l_hash(auth):
    client, headers = auth
    raw_key = _create(client, headers, account=777).json()["key"]
    token = {"X-Nexus-Token": backend.BRIDGE_TOKEN}
    resp = client.post("/api/license/verify",
                       json={"key": raw_key, "account": 777}, headers=token)
    body = resp.json()
    if backend.LICENSE_MODE == "strict":
        assert body["valid"] is True and body["reason"] == "ok"
    else:
        # AUD0-LIC-001: in modalità open la risposta deve dichiararlo.
        assert body["enforcement"] == "disabled"
        assert "warning" in body


# --------------------------------------------------------------------------- #
# Create è insert-only — AUD0-LIC-002 / AUD0-BE-LIC-002
# --------------------------------------------------------------------------- #
def test_create_non_sovrascrive_una_licenza_esistente(auth):
    client, headers = auth
    raw_key = _create(client, headers).json()["key"]
    duplicate = _create(client, headers, key=raw_key)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "CONFLICT"


# --------------------------------------------------------------------------- #
# Validazione — AUD0-LIC-003 / AUD0-FE-LIC-005
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("payload", [
    {"plan": "piano-inventato"},
    {"account": "non-numerico"},
    {"days": 0},
    {"days": 99999},
    {"key": "corta"},
])
def test_campi_non_validi_rifiutati(auth, payload):
    client, headers = auth
    resp = _create(client, headers, **payload)
    assert resp.status_code == 422, resp.text


def test_scadenza_nel_passato_rifiutata(auth):
    client, headers = auth
    resp = _create(client, headers, expires_at=1)
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# Esistenza e motivazione — AUD0-LIC-003 / AUD0-FE-LIC-004
# --------------------------------------------------------------------------- #
def test_update_su_licenza_inesistente_da_404(auth):
    client, headers = auth
    resp = client.patch("/api/license/hash-inesistente",
                        json={"note": "x"}, headers=headers)
    assert resp.status_code == 404


def test_revoca_richiede_una_motivazione(auth):
    client, headers = auth
    license_id = _create(client, headers).json()["id"]

    senza = client.request("DELETE", f"/api/license/{license_id}", headers=headers)
    assert senza.status_code == 422

    con = client.request("DELETE", f"/api/license/{license_id}",
                         params={"reason": "cliente cessato"}, headers=headers)
    assert con.status_code == 200


def test_disattivazione_richiede_motivazione(auth):
    client, headers = auth
    license_id = _create(client, headers).json()["id"]
    resp = client.patch(f"/api/license/{license_id}",
                        json={"active": False}, headers=headers)
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# active ha effetto reale — AUD0-BE-LIC-004
# --------------------------------------------------------------------------- #
def test_la_revoca_invalida_la_chiave(auth, monkeypatch):
    client, headers = auth
    created = _create(client, headers, account=4242).json()
    raw_key, license_id = created["key"], created["id"]

    # La verifica deve girare in modalità strict per essere significativa.
    monkeypatch.setattr(backend, "LICENSE_MODE", "strict")
    token = {"X-Nexus-Token": backend.BRIDGE_TOKEN}

    before = client.post("/api/license/verify",
                         json={"key": raw_key, "account": 4242}, headers=token).json()
    assert before["valid"] is True

    client.request("DELETE", f"/api/license/{license_id}",
                   params={"reason": "test di revoca"}, headers=headers)

    after = client.post("/api/license/verify",
                        json={"key": raw_key, "account": 4242}, headers=token).json()
    assert after["valid"] is False and after["reason"] == "revoked"


def test_la_revoca_conserva_la_storia(auth):
    client, headers = auth
    license_id = _create(client, headers).json()["id"]
    client.request("DELETE", f"/api/license/{license_id}",
                   params={"reason": "chiusura contratto"}, headers=headers)

    # La riga non viene cancellata: resta con stato REVOKED.
    listing = client.get("/api/license/list").json()["licenses"]
    revoked = [l for l in listing if l["id"] == license_id]
    assert revoked and revoked[0]["status"] == "REVOKED"
    assert revoked[0]["revoked_reason"] == "chiusura contratto"

    events = client.get(f"/api/license/{license_id}/events").json()["events"]
    assert [e["event"] for e in events] == ["REVOKED", "ISSUED"]


def test_estensione_calcolata_sulla_scadenza_corrente(auth):
    client, headers = auth
    created = _create(client, headers, days=10).json()
    before = [l for l in client.get("/api/license/list").json()["licenses"]
              if l["id"] == created["id"]][0]["expires_at"]
    client.patch(f"/api/license/{created['id']}",
                 json={"extend_days": 5, "reason": "rinnovo"}, headers=headers)
    after = [l for l in client.get("/api/license/list").json()["licenses"]
             if l["id"] == created["id"]][0]["expires_at"]
    assert after == before + 5 * 86400
