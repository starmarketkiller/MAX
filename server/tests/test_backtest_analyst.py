"""Smoke test Backtest Analyst (OpenAI) — verifica configurazione e
comportamento controllato SENZA chiave API e senza esporre segreti.

Esecuzione (da server/):  python -m pytest tests/ -q
Non richiede OPENAI_API_KEY: testa proprio il percorso "chiave assente".
"""
import os
import sys
from pathlib import Path

# Il backend viene avviato da server/ (uvicorn app:app) — replichiamo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# DB temporaneo e credenziali di test PRIMA di importare app.
os.environ.setdefault("NEXUS_DB_PATH", str(Path(__file__).parent / "_test_nexus.db"))
os.environ.setdefault("NEXUS_ADMIN_USER", "testuser")
os.environ.setdefault("NEXUS_ADMIN_PASSWORD", "testpass")
os.environ.setdefault("NEXUS_JWT_SECRET", "test-secret-not-used-in-prod")
os.environ.setdefault("NEXUS_COOKIE_SECURE", "false")
os.environ.pop("OPENAI_API_KEY", None)   # il test copre il caso chiave assente

from fastapi.testclient import TestClient  # noqa: E402

import app as nexus_app  # noqa: E402

client = TestClient(nexus_app.app)


def _login_headers():
    r = client.post("/api/auth/login", json={"username": "testuser", "password": "testpass"})
    assert r.status_code == 200, f"login fallito: {r.status_code} {r.text}"
    token = r.json().get("token") or r.cookies.get("nexus_session")
    assert token, "nessun token dalla login"
    return {"Authorization": f"Bearer {token}"}


def test_startup_app_importabile():
    """L'app FastAPI si importa e monta le route degli agenti."""
    paths = {r.path for r in nexus_app.app.routes}
    assert "/api/agents/backtest-analysis" in paths
    assert "/api/agents/diagnostics" in paths


def test_diagnostics_richiede_auth():
    # Client fresco: quello condiviso conserva il cookie di sessione della login.
    with TestClient(nexus_app.app) as fresh:
        r = fresh.get("/api/agents/diagnostics")
    assert r.status_code == 401


def test_diagnostics_non_espone_segreti():
    r = client.get("/api/agents/diagnostics", headers=_login_headers())
    assert r.status_code == 200
    data = r.json()["backtest_analyst"]
    assert set(data) == {"openai_configured", "openai_model", "sdk_available"}
    assert data["openai_configured"] is False          # nessuna chiave nel test
    assert isinstance(data["openai_model"], str)
    # nessun valore che assomigli a una chiave nella risposta
    assert "sk-" not in r.text


def test_analysis_senza_chiave_errore_controllato():
    r = client.post("/api/agents/backtest-analysis",
                    headers=_login_headers(),
                    json={"report": "PF 1.5, WR 40%, DD 8%, 120 trade"})
    assert r.status_code == 503
    assert "OPENAI_API_KEY" in r.json()["detail"]


def test_analysis_richiede_auth():
    with TestClient(nexus_app.app) as fresh:
        r = fresh.post("/api/agents/backtest-analysis", json={"report": "x"})
    assert r.status_code == 401
