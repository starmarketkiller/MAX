"""Test di integrazione sulle rotte: CSRF, download protetti, ciclo comandi.

Copre AUD0-SEC-007/008/012, AUD0-CMD-001/002, AUD0-AI-001, AUD0-DB-005.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app as backend
import nexus_policy as policy
import nexus_security as sec


@pytest.fixture(scope="module")
def client():
    with TestClient(backend.app) as c:
        yield c


@pytest.fixture()
def logged_in(client):
    """Effettua il login e restituisce (client, header CSRF)."""
    client.cookies.clear()
    resp = client.post("/api/auth/login",
                       json={"email": backend.ADMIN_USER,
                             "password": backend.ADMIN_PASSWORD})
    assert resp.status_code == 200, resp.text
    csrf = resp.json()["csrf_token"]
    return client, {sec.CSRF_HEADER: csrf}


# --------------------------------------------------------------------------- #
# Liveness vs readiness — AUD0-DB-005 / AUD0-DEPLOY-RENDER-003
# --------------------------------------------------------------------------- #
def test_health_e_solo_liveness(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert body["check"] == "liveness"


def test_ready_verifica_database_e_migrazioni(client):
    body = client.get("/api/ready").json()
    assert body["check"] == "readiness"
    assert body["checks"]["database"]["ok"] is True
    assert body["checks"]["database"]["writable"] is True
    assert body["checks"]["migrations"]["ok"] is True
    assert "003_ea_command_lifecycle" in body["checks"]["migrations"]["applied"]
    assert "security" in body["checks"]


# --------------------------------------------------------------------------- #
# Sessione e CSRF — AUD0-SEC-008 / AUD0-AUTH-001
# --------------------------------------------------------------------------- #
def test_login_emette_cookie_di_sessione_e_token_csrf(client):
    client.cookies.clear()
    resp = client.post("/api/auth/login",
                       json={"email": backend.ADMIN_USER,
                             "password": backend.ADMIN_PASSWORD})
    assert resp.status_code == 200
    assert backend.SESSION_COOKIE in resp.cookies
    assert resp.json()["csrf_token"]


def test_login_con_credenziali_errate_rifiutato(client):
    client.cookies.clear()
    resp = client.post("/api/auth/login",
                       json={"email": backend.ADMIN_USER, "password": "sbagliata"})
    assert resp.status_code in (401, 429)
    backend.LOGIN_LIMITER.reset(f"testclient|{backend.ADMIN_USER.lower()}")


def test_mutazione_senza_header_csrf_rifiutata(logged_in):
    client, _headers = logged_in
    resp = client.post("/api/dashboard/command",
                       json={"action": "pause",
                             "target": {"account_id": "1", "symbol": "XAUUSD"}})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "CSRF_TOKEN_INVALID"


def test_mutazione_con_header_csrf_errato_rifiutata(logged_in):
    client, _headers = logged_in
    resp = client.post("/api/dashboard/command",
                       json={"action": "pause",
                             "target": {"account_id": "1", "symbol": "XAUUSD"}},
                       headers={sec.CSRF_HEADER: "token-inventato"})
    assert resp.status_code == 403


def test_logout_revoca_la_sessione_lato_server(client):
    client.cookies.clear()
    login = client.post("/api/auth/login",
                        json={"email": backend.ADMIN_USER,
                              "password": backend.ADMIN_PASSWORD})
    cookies = dict(login.cookies)
    csrf = login.json()["csrf_token"]
    assert client.get("/api/auth/me").status_code == 200

    out = client.post("/api/auth/logout", headers={sec.CSRF_HEADER: csrf})
    assert out.json()["server_session_revoked"] is True

    # Riusare il cookie catturato prima del logout non deve funzionare.
    client.cookies.clear()
    client.cookies.set(backend.SESSION_COOKIE, cookies[backend.SESSION_COOKIE])
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.clear()


# --------------------------------------------------------------------------- #
# Ciclo di vita comandi EA — AUD0-CMD-001 / AUD0-CMD-002
# --------------------------------------------------------------------------- #
def test_comando_senza_target_rifiutato(logged_in):
    client, headers = logged_in
    resp = client.post("/api/dashboard/command",
                       json={"action": "pause"}, headers=headers)
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "VALIDATION_FAILED"


def test_close_all_senza_conferma_rifiutato(logged_in):
    client, headers = logged_in
    resp = client.post("/api/dashboard/command",
                       json={"action": "close_all",
                             "target": {"account_id": "555", "symbol": "XAUUSD"}},
                       headers=headers)
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["requires_confirmation"] is True
    # Gli effetti dichiarati arrivano dal contratto canonico, non dalla UI.
    assert any("non è reversibile" in e for e in detail["effects"])


def test_polling_senza_identita_rifiutato(client):
    resp = client.get("/api/ea/command",
                      headers={"X-Nexus-Token": backend.BRIDGE_TOKEN})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "TARGET_SCOPE_MISMATCH"


def test_comando_consegnato_solo_all_istanza_giusta(logged_in):
    client, headers = logged_in
    created = client.post("/api/dashboard/command",
                          json={"action": "pause",
                                "target": {"account_id": "111", "symbol": "XAUUSD"}},
                          headers=headers)
    assert created.status_code == 200, created.text
    command_id = created.json()["command_id"]

    token = {"X-Nexus-Token": backend.BRIDGE_TOKEN}
    # Un'altra istanza non deve ricevere nulla.
    altro = client.get("/api/ea/command",
                       params={"account_id": "999", "symbol": "XAUUSD"}, headers=token)
    assert altro.json()["action"] is None
    altro_simbolo = client.get("/api/ea/command",
                               params={"account_id": "111", "symbol": "EURUSD"},
                               headers=token)
    assert altro_simbolo.json()["action"] is None

    # L'istanza corretta lo riceve, in LEASE (non "consegnato e concluso").
    mio = client.get("/api/ea/command",
                     params={"account_id": "111", "symbol": "XAUUSD"}, headers=token)
    body = mio.json()
    assert body["command_id"] == command_id
    assert body["status"] == policy.CMD_LEASED
    assert body["lease_id"]
    assert body["target"]["account_id"] == "111"

    # Lo stato non è terminale finché il broker non conferma.
    status = client.get(f"/api/command/{command_id}").json()
    assert status["terminal"] is False
    assert status["broker_confirmed"] is False


def test_ack_porta_il_comando_a_stato_terminale(logged_in):
    client, headers = logged_in
    created = client.post("/api/dashboard/command",
                          json={"action": "pause",
                                "target": {"account_id": "222", "symbol": "XAUUSD"}},
                          headers=headers)
    command_id = created.json()["command_id"]
    token = {"X-Nexus-Token": backend.BRIDGE_TOKEN}
    lease = client.get("/api/ea/command",
                       params={"account_id": "222", "symbol": "XAUUSD"},
                       headers=token).json()["lease_id"]

    ack = client.post("/api/ea/command/ack",
                      json={"command_id": command_id, "lease_id": lease,
                            "status": policy.CMD_SUCCEEDED, "retcode": 10009},
                      headers=token)
    assert ack.json()["status"] == policy.CMD_SUCCEEDED

    status = client.get(f"/api/command/{command_id}").json()
    assert status["terminal"] is True
    assert status["broker_confirmed"] is True
    assert status["result"]["retcode"] == 10009


def test_ack_con_lease_sbagliato_rifiutato(logged_in):
    client, headers = logged_in
    created = client.post("/api/dashboard/command",
                          json={"action": "pause",
                                "target": {"account_id": "333", "symbol": "XAUUSD"}},
                          headers=headers)
    command_id = created.json()["command_id"]
    token = {"X-Nexus-Token": backend.BRIDGE_TOKEN}
    client.get("/api/ea/command",
               params={"account_id": "333", "symbol": "XAUUSD"}, headers=token)

    resp = client.post("/api/ea/command/ack",
                       json={"command_id": command_id, "lease_id": "lease-falso",
                             "status": policy.CMD_SUCCEEDED},
                       headers=token)
    assert resp.status_code == 409


def test_idempotenza_evita_il_doppio_comando(logged_in):
    client, headers = logged_in
    body = {"action": "pause",
            "target": {"account_id": "444", "symbol": "XAUUSD"},
            "idempotency_key": "chiave-stabile-1"}
    first = client.post("/api/dashboard/command", json=body, headers=headers)
    second = client.post("/api/dashboard/command", json=body, headers=headers)
    assert first.json()["command_id"] == second.json()["command_id"]


def test_contratto_comandi_esposto_alla_ui(logged_in):
    client, _headers = logged_in
    body = client.get("/api/ea/command_contract").json()
    assert "close_all" in body["actions"]
    assert body["actions"]["close_all"]["requires_confirmation"] is True
    assert policy.CMD_LEASED not in body["terminal_statuses"]


# --------------------------------------------------------------------------- #
# Download protetti — AUD0-SEC-012
# --------------------------------------------------------------------------- #
def test_download_non_sono_nel_mount_statico_pubblico():
    # La cartella pubblica non deve più contenere artefatti scaricabili.
    assert not (backend.STATIC_DIR / "downloads").exists() or \
        not any((backend.STATIC_DIR / "downloads").iterdir())


def test_download_richiede_autenticazione(client):
    client.cookies.clear()
    assert client.get("/api/downloads/list").status_code == 401
    assert client.get("/api/downloads/file/NEXUS_Balanced.set").status_code == 401


def test_download_espone_il_digest(logged_in):
    client, _headers = logged_in
    body = client.get("/api/downloads/list").json()
    assert body["files"], "nessun artefatto nella cartella protetta"
    for item in body["files"]:
        assert len(item["sha256"]) == 64
        assert item["url"].startswith("/api/downloads/file/")


def test_download_blocca_il_path_traversal(logged_in):
    client, _headers = logged_in
    for evil in ("..%2f..%2fapp.py", "....//app.py"):
        resp = client.get(f"/api/downloads/file/{evil}")
        assert resp.status_code in (400, 404, 415)


# --------------------------------------------------------------------------- #
# Coach senza autorità di esecuzione — AUD0-AI-001 / NEXUS-AI-002
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(backend.COACH_ALLOW_ACTIONS,
                    reason="le azioni del Coach sono abilitate in questo ambiente")
def test_coach_non_puo_mutare_lo_stato_di_trading(logged_in):
    client, headers = logged_in
    resp = client.post("/api/coach/apply_action",
                       json={"type": "close_all"}, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"]["draft_route"] == "/api/coach/draft_action"


def test_coach_produce_una_bozza_non_eseguita(logged_in):
    client, _headers = logged_in
    resp = client.post("/api/coach/draft_action", json={"type": "close_all"})
    draft = resp.json()["draft"]
    assert draft["executed"] is False
    assert draft["authority"] == "AI_RECOMMENDATION"
    assert draft["submit_to"] == "/api/dashboard/command"


# --------------------------------------------------------------------------- #
# Tetti di rischio applicati dalle rotte — AUD0-RISK-001
# --------------------------------------------------------------------------- #
def test_policy_di_rischio_esposta(logged_in):
    client, _headers = logged_in
    body = client.get("/api/risk/policy").json()
    assert body["environment"] == backend.ENVIRONMENT
    assert "strategy_multiplier" in body["caps"]


def test_override_su_strategia_inesistente_rifiutato(logged_in):
    client, headers = logged_in
    resp = client.post("/api/strategies/risk_manual",
                       json={"overrides": {"STRATEGIA_INVENTATA": 1.2}},
                       headers=headers)
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# Limite dimensione body — AUD0-API-002
# --------------------------------------------------------------------------- #
def test_body_troppo_grande_rifiutato(logged_in):
    client, headers = logged_in
    huge = {"action": "pause", "target": {"account_id": "1", "symbol": "X"},
            "reason": "x" * (backend.MAX_JSON_BODY_BYTES + 1024)}
    resp = client.post("/api/dashboard/command", json=huge, headers=headers)
    assert resp.status_code == 413


def test_il_limite_copre_anche_le_rotte_ea_e_analytics(logged_in):
    """AUD0-API-002: il limite era applicato solo dove si usava read_json_body.

    Sedici rotte leggevano ancora `await request.json()`, cioe' un corpo di
    dimensione arbitraria in memoria — comprese quelle raggiungibili col solo
    token del bridge. Qui si verifica sia una rotta EA sia una autenticata.
    """
    client, headers = logged_in
    padding = "x" * (backend.MAX_JSON_BODY_BYTES + 1024)

    resp = client.post("/api/ea/push", json={"magic": 1, "symbol": padding},
                       headers={"X-Nexus-Token": backend.BRIDGE_TOKEN})
    assert resp.status_code == 413

    resp = client.post("/api/analytics/whatif",
                       json={"exclude_strategies": [padding]}, headers=headers)
    assert resp.status_code == 413


# --------------------------------------------------------------------------- #
# Audit operatore — AUD0-AUDIT-001
# --------------------------------------------------------------------------- #
def test_le_azioni_privilegiate_finiscono_nell_audit(logged_in):
    client, headers = logged_in
    client.post("/api/dashboard/command",
                json={"action": "pause",
                      "target": {"account_id": "777", "symbol": "XAUUSD"},
                      "reason": "test audit"},
                headers=headers)
    events = client.get("/api/audit/operator").json()["events"]
    assert any(e["action"] == "ea.command.pause" and e["decision"] == "ACCEPTED"
               for e in events)
    assert any(e["action"] == "auth.login" for e in events)
