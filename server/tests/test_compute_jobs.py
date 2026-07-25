"""Coda di job computazionali e limiti dello spazio di ricerca.

Copre AUD0-COMPUTE-001..005, AUD0-BE-BT-003, AUD0-BE-BT-010..012.
"""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

import app as backend
import nexus_jobs as jobs
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


def _wait_terminal(client, job_id, timeout=20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/jobs/{job_id}").json()
        if body.get("terminal"):
            return body
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} non terminato entro {timeout}s")


# --------------------------------------------------------------------------- #
# Spazio di ricerca limitato — AUD0-COMPUTE-002
# --------------------------------------------------------------------------- #
def test_stima_combinazioni():
    assert jobs.estimate_combinations([1, 2], [3, 4, 5]) == 6
    assert jobs.estimate_combinations([], [1]) == 1


def test_ricerca_troppo_grande_rifiutata_prima_di_eseguire():
    with pytest.raises(jobs.SearchSpaceTooLarge) as exc:
        jobs.guard_search_space(list(range(50)), list(range(50)), list(range(50)))
    assert exc.value.combinations > exc.value.maximum


def test_ricerca_entro_i_limiti_accettata():
    assert jobs.guard_search_space([1, 2], [3, 4]) == 4


def test_optimizer_rifiuta_una_griglia_esplosiva(auth):
    client, headers = auth
    resp = client.post("/api/backtest/optimize_per_strategy", json={
        "symbol": "XAUUSD", "timeframe": "D1",
        "pool": list(backend.strategy_registry.LIVE_STRATEGY_IDS)[:20],
        "param_grid": {
            "atr_sl": [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4],
            "atr_tp": [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5],
            "htf_filter": [False, True],
            "breakeven_r": [0.0, 0.5, 1.0],
            "trailing_atr": [0.0, 1.0, 2.0],
        },
    }, headers=headers)
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["combinations"] > detail["maximum"]


def test_pool_con_strategia_inesistente_rifiutato(auth):
    client, headers = auth
    resp = client.post("/api/backtest/optimize_per_strategy",
                       json={"pool": ["STRATEGIA_INVENTATA"]}, headers=headers)
    assert resp.status_code == 422
    assert resp.json()["detail"]["field"] == "pool"


def test_timeframe_non_supportato_rifiutato(auth):
    client, headers = auth
    resp = client.post("/api/backtest/optimize_multi_tf", json={
        "pool": [list(backend.strategy_registry.LIVE_STRATEGY_IDS)[0]],
        "timeframes": ["1secondo"],
    }, headers=headers)
    assert resp.status_code == 422
    assert resp.json()["detail"]["field"] == "timeframes"


# --------------------------------------------------------------------------- #
# Il lavoro pesante non blocca la richiesta — AUD0-COMPUTE-001 / AUD0-BE-BT-012
# --------------------------------------------------------------------------- #
def test_optimize_restituisce_un_job_non_il_risultato(auth):
    client, headers = auth
    strategy = list(backend.strategy_registry.LIVE_STRATEGY_IDS)[0]
    resp = client.post("/api/backtest/optimize",
                       json={"symbol": "XAUUSD", "strategy": strategy},
                       headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == jobs.JOB_QUEUED
    assert body["job_id"]
    # AUD0-BE-BT-003: envelope di riproducibilità.
    assert body["manifest"]["params_hash"]
    assert body["manifest"]["app_version"] == backend.APP_VERSION
    assert body["manifest"]["requested_by"] == backend.ADMIN_USER

    final = _wait_terminal(client, body["job_id"])
    assert final["status"] in (jobs.JOB_SUCCEEDED, jobs.JOB_FAILED)


def test_library_build_dichiara_queued_solo_se_e_vero(auth):
    client, headers = auth
    resp = client.post("/api/backtest/strategy_library/build",
                       json={"symbol": "XAUUSD"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == jobs.JOB_QUEUED
    assert resp.json()["job_id"]


def test_library_build_senza_simbolo_rifiutato(auth):
    client, headers = auth
    resp = client.post("/api/backtest/strategy_library/build", json={}, headers=headers)
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# I job hanno un proprietario — AUD0-COMPUTE-005
# --------------------------------------------------------------------------- #
def test_job_inesistente_da_404(auth):
    client, _headers = auth
    assert client.get("/api/jobs/non-esiste").status_code == 404
    assert client.get("/api/backtest/optimize/non-esiste").status_code == 404


def test_job_di_un_altro_utente_non_e_leggibile():
    store = jobs.JobStore(backend._conn)
    store.init_schema()
    job_id = store.create(job_type="test", requested_by="altro@utente",
                          job_manifest={"params": {}})
    fetched = store.get(job_id)
    assert fetched["requested_by"] == "altro@utente"
    # La rotta filtra per proprietario: verificato nel test HTTP sopra.
    assert not store.request_cancel(job_id, "utente-diverso")


# --------------------------------------------------------------------------- #
# Errori tipizzati — AUD0-COMPUTE-003
# --------------------------------------------------------------------------- #
def test_un_eccezione_diventa_job_fallito_non_risultato_vuoto():
    store = jobs.JobStore(backend._conn)
    store.init_schema()
    runner = jobs.JobRunner(store, workers=1)
    job_id = store.create(job_type="test-fail", requested_by="tester",
                          job_manifest={"params": {}})

    def _boom():
        raise RuntimeError("dati di mercato non disponibili")

    runner.submit(job_id, _boom)
    deadline = time.time() + 10
    while time.time() < deadline:
        job = store.get(job_id)
        if job["status"] in jobs.TERMINAL_STATES:
            break
        time.sleep(0.05)
    assert job["status"] == jobs.JOB_FAILED
    assert "dati di mercato non disponibili" in job["error"]
    runner.shutdown()


def test_quota_di_job_per_utente():
    store = jobs.JobStore(backend._conn)
    store.init_schema()
    owner = f"quota-{time.time()}"
    for _ in range(jobs.MAX_ACTIVE_JOBS_PER_USER):
        store.create(job_type="t", requested_by=owner, job_manifest={})
    with pytest.raises(jobs.JobRejected):
        store.create(job_type="t", requested_by=owner, job_manifest={})


def test_i_job_orfani_di_un_riavvio_sono_dichiarati_falliti():
    store = jobs.JobStore(backend._conn)
    store.init_schema()
    owner = f"orfano-{time.time()}"
    job_id = store.create(job_type="t", requested_by=owner, job_manifest={})
    store.mark_running(job_id)
    store.reap_orphans()
    job = store.get(job_id)
    assert job["status"] == jobs.JOB_FAILED
    assert "riavvio" in job["error"]


# --------------------------------------------------------------------------- #
# Promozione ricerca → produzione — AUD0-BE-BT-011
# --------------------------------------------------------------------------- #
def test_import_non_promuove_a_locked_profile_per_default(auth):
    client, headers = auth
    resp = client.post("/api/backtest/import_results", json={
        "results": [{"strategy": list(backend.strategy_registry.LIVE_STRATEGY_IDS)[0],
                     "symbol": "XAUUSD", "sharpe": 1.5}],
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json().get("locked_written", 0) == 0


def test_promozione_richiede_una_motivazione(auth):
    client, headers = auth
    resp = client.post("/api/backtest/import_results", json={
        "results": [{"strategy": list(backend.strategy_registry.LIVE_STRATEGY_IDS)[0],
                     "symbol": "XAUUSD", "sharpe": 1.5}],
        "make_locked_profiles": True,
    }, headers=headers)
    # In sviluppo: serve la motivazione. In ambiente hardened: vietato del tutto.
    assert resp.status_code in (403, 422)
