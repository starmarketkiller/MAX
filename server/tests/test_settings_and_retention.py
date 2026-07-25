"""Settings versionati, applied-state ACK, retention e backup.

Copre AUD0-BE-SET-001..004, AUD0-DB-013, AUD0-DB-014, AUD0-DATA-002.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app as backend
import nexus_retention as retention
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
    assert resp.status_code == 200
    return client, {sec.CSRF_HEADER: resp.json()["csrf_token"]}


# --------------------------------------------------------------------------- #
# Compare-and-swap — AUD0-BE-SET-001 / AUD0-FE-SET-003
# --------------------------------------------------------------------------- #
def test_ogni_scrittura_incrementa_la_revisione(auth):
    client, headers = auth
    before = client.get("/api/settings/state").json()["desired"]["revision"]
    resp = client.post("/api/settings", json={"MaxConcurrent": 5}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["revision"] == before + 1


def test_scrittura_con_revisione_obsoleta_rifiutata(auth):
    client, headers = auth
    state = client.get("/api/settings/state").json()["desired"]
    stale = state["revision"] - 1

    resp = client.post("/api/settings",
                       json={"MaxConcurrent": 6, "expected_revision": stale},
                       headers=headers)
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["code"] == "CONFLICT"
    assert detail["current_revision"] == state["revision"]


def test_scrittura_con_revisione_corretta_accettata(auth):
    client, headers = auth
    revision = client.get("/api/settings/state").json()["desired"]["revision"]
    resp = client.post("/api/settings",
                       json={"MaxConcurrent": 7, "expected_revision": revision},
                       headers=headers)
    assert resp.status_code == 200
    assert resp.json()["revision"] == revision + 1


def test_due_scritture_concorrenti_non_si_annullano(auth):
    client, headers = auth
    revision = client.get("/api/settings/state").json()["desired"]["revision"]

    primo = client.post("/api/settings",
                        json={"MaxConcurrent": 4, "expected_revision": revision},
                        headers=headers)
    assert primo.status_code == 200

    # Il secondo operatore aveva caricato la stessa revisione: viene fermato.
    secondo = client.post("/api/settings",
                          json={"MaxConcurrent": 3, "expected_revision": revision},
                          headers=headers)
    assert secondo.status_code == 409


# --------------------------------------------------------------------------- #
# Audit delle modifiche — AUD0-BE-SET-002
# --------------------------------------------------------------------------- #
def test_la_modifica_registra_attore_e_diff(auth):
    client, headers = auth
    resp = client.post("/api/settings",
                       json={"MaxConcurrent": 2, "reason": "test di audit"},
                       headers=headers)
    changed = resp.json()["changed"]
    assert "MaxConcurrent" in changed
    assert changed["MaxConcurrent"]["to"] == 2

    events = client.get("/api/audit/operator").json()["events"]
    assert any(e["action"] == "settings.write" and e["reason"] == "test di audit"
               for e in events)

    history = client.get("/api/settings/history").json()
    assert any(h.get("actor") == backend.ADMIN_USER for h in history)


# --------------------------------------------------------------------------- #
# Desiderato vs applicato — AUD0-BE-SET-004
# --------------------------------------------------------------------------- #
def test_desiderato_non_significa_applicato(auth):
    client, headers = auth
    client.post("/api/settings", json={"MaxConcurrent": 5}, headers=headers)
    state = client.get("/api/settings/state").json()
    # Nessun EA ha confermato: non si puo' affermare che sia applicato.
    assert state["all_in_sync"] is False


def test_l_ea_conferma_la_revisione_applicata(auth):
    client, headers = auth
    written = client.post("/api/settings", json={"MaxConcurrent": 6}, headers=headers).json()
    token = {"X-Nexus-Token": backend.BRIDGE_TOKEN}

    ack = client.post("/api/ea/settings/ack", headers=token, json={
        "account_id": "9001", "symbol": "XAUUSD",
        "revision": written["revision"], "checksum": written["checksum"],
        "status": "APPLIED"})
    assert ack.status_code == 200

    state = client.get("/api/settings/state").json()
    assert state["in_sync"]["9001:XAUUSD"] is True


def test_ack_senza_identita_rifiutato(auth):
    client, _headers = auth
    token = {"X-Nexus-Token": backend.BRIDGE_TOKEN}
    resp = client.post("/api/ea/settings/ack", headers=token, json={"revision": 1})
    assert resp.status_code == 400


def test_un_rifiuto_dell_ea_resta_visibile(auth):
    client, headers = auth
    written = client.post("/api/settings", json={"MaxConcurrent": 7}, headers=headers).json()
    token = {"X-Nexus-Token": backend.BRIDGE_TOKEN}
    client.post("/api/ea/settings/ack", headers=token, json={
        "account_id": "9002", "symbol": "EURUSD",
        "revision": written["revision"], "status": "REJECTED",
        "rejected_reason": "RiskPercent fuori dai limiti locali"})

    state = client.get("/api/settings/state").json()
    entry = state["applied_by_instance"]["9002:EURUSD"]
    assert entry["status"] == "REJECTED"
    assert "fuori dai limiti" in entry["rejected_reason"]
    assert state["in_sync"]["9002:EURUSD"] is False


# --------------------------------------------------------------------------- #
# Locked profile: patch, non replace implicito — AUD0-BE-SET-003
# --------------------------------------------------------------------------- #
def test_un_payload_parziale_non_cancella_gli_altri_simboli(auth):
    client, headers = auth
    client.put("/api/dashboard/locked_profiles",
               json={"profiles": {"XAUUSD": {"RiskPercent": 1.0},
                                  "EURUSD": {"RiskPercent": 0.5}}},
               headers=headers)

    # Invio solo XAUUSD: EURUSD deve sopravvivere.
    client.put("/api/dashboard/locked_profiles",
               json={"profiles": {"XAUUSD": {"RiskPercent": 1.2}}},
               headers=headers)

    profiles = client.get("/api/dashboard/locked_profiles").json()
    assert "EURUSD" in profiles, "un payload parziale ha cancellato un profilo"
    assert "XAUUSD" in profiles


def test_la_cancellazione_richiede_un_marcatore_esplicito(auth):
    client, headers = auth
    client.put("/api/dashboard/locked_profiles",
               json={"profiles": {"GBPUSD": {"RiskPercent": 0.7}}}, headers=headers)
    resp = client.put("/api/dashboard/locked_profiles",
                      json={"profiles": {}, "delete": ["GBPUSD"]}, headers=headers)
    assert "GBPUSD" in resp.json()["removed"]
    assert "GBPUSD" not in client.get("/api/dashboard/locked_profiles").json()


def test_la_sostituzione_totale_va_dichiarata(auth):
    client, headers = auth
    client.put("/api/dashboard/locked_profiles",
               json={"profiles": {"AUDUSD": {"RiskPercent": 0.4}}}, headers=headers)
    resp = client.put("/api/dashboard/locked_profiles",
                      json={"profiles": {"USDJPY": {"RiskPercent": 0.4}},
                            "replace": True}, headers=headers)
    assert resp.json()["replace_all"] is True
    assert "AUDUSD" not in resp.json()["locked_profiles"]


# --------------------------------------------------------------------------- #
# Retention — AUD0-DB-013
# --------------------------------------------------------------------------- #
def test_le_classi_di_evidenza_sono_protette():
    protected = {r.table for r in retention.RETENTION_RULES if r.protected}
    assert {"trade_events", "operator_audit", "license_events"} <= protected


def test_il_dry_run_non_cancella_nulla():
    result = retention.apply_retention(backend._conn, dry_run=True)
    assert result["dry_run"] is True
    assert "operator_audit" in result["protected_skipped"]


def test_il_report_di_retention_e_leggibile(auth):
    client, _headers = auth
    body = client.get("/api/admin/retention").json()
    assert body["rules"]
    for rule in body["rules"]:
        if rule["protected"]:
            assert rule["would_delete"] == 0


# --------------------------------------------------------------------------- #
# Backup e drill di ripristino — AUD0-DB-014
# --------------------------------------------------------------------------- #
def test_il_backup_produce_un_file_con_digest(tmp_path):
    created = retention.backup_database(backend.DB_PATH, str(tmp_path))
    assert created["size_bytes"] > 0
    assert len(created["sha256"]) == 64
    # Un backup appena creato non è ancora "verificato".
    assert created["verified"] is False


def test_la_verifica_controlla_davvero_l_integrita(tmp_path):
    created = retention.backup_database(backend.DB_PATH, str(tmp_path))
    verified = retention.verify_backup(created["path"])
    assert verified["ok"] is True
    assert verified["integrity_check"] == "ok"
    assert verified["migrations"]


def test_il_drill_di_ripristino_confronta_i_conteggi(tmp_path):
    result = retention.restore_drill(backend.DB_PATH, str(tmp_path))
    assert result["drill_passed"] is True, result["mismatches"]
    assert result["verification"]["ok"] is True


def test_i_backup_vecchi_vengono_potati(tmp_path):
    # Il nome include il timestamp al secondo: si creano file distinti a mano
    # per verificare la potatura senza dipendere dall'orologio.
    created = retention.backup_database(backend.DB_PATH, str(tmp_path))
    import shutil as _shutil
    for i in range(2):
        _shutil.copy2(created["path"], tmp_path / f"nexus-2020010{i}T000000Z.db")
    assert len(list(tmp_path.glob("nexus-*.db"))) == 3
    removed = retention.cleanup_old_backups(str(tmp_path), keep=1)
    assert len(removed) == 2
    assert len(list(tmp_path.glob("nexus-*.db"))) == 1


# --------------------------------------------------------------------------- #
# Provenienza dei dati sintetici — AUD0-DATA-002
# --------------------------------------------------------------------------- #
def test_ogni_evento_del_calendario_demo_e_etichettato(auth):
    client, _headers = auth
    body = client.get("/api/analytics/economic_calendar").json() \
        if client.get("/api/analytics/economic_calendar").status_code == 200 else None
    if body is None:
        pytest.skip("rotta calendario non disponibile in questa build")
    assert body["usable_for_trading_decisions"] is False
    for event in body["events"]:
        # Il flag a livello di risposta non basta: la UI potrebbe mostrare
        # solo la lista.
        assert event["synthetic"] is True
        assert event["provenance"] == "SYNTHETIC_DEMO"
        assert event["title"].startswith("[DEMO]")
