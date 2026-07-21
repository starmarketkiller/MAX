"""PR7 — test del contratto Settings (schema, validazione, profili versionati)."""
import json
import math
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as backend
import settings_schema as ss


@pytest.fixture()
def client():
    with TestClient(backend.app) as c:
        yield c


def _auth(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert r.status_code == 200, r.text
    tok = r.json().get("token")
    return {"Authorization": f"Bearer {tok}"} if tok else {}


# ---------------------------------------------------- non-divergenza --------
def test_backend_defaults_match_contract():
    """Regola cardine PR7: i default backend NON divergono dal contratto."""
    assert backend.DEFAULT_SETTINGS == ss.default_settings()


def test_schema_covers_all_defaults():
    keys_schema = {s["key"] for s in ss.schema()["settings"]}
    assert set(ss.default_settings()) == keys_schema


# ---------------------------------------------------- validazione -----------
def test_reject_nan_and_infinity():
    for bad in (float("nan"), float("inf")):
        with pytest.raises(ss.SettingsValidationError):
            ss.validate({"RiskPercent": bad})


def test_reject_out_of_range():
    with pytest.raises(ss.SettingsValidationError):
        ss.validate({"RiskPercent": 999})
    with pytest.raises(ss.SettingsValidationError):
        ss.validate({"MaxDailyDDPct": -1})


def test_integer_vs_decimal():
    with pytest.raises(ss.SettingsValidationError):
        ss.validate({"MaxConcurrent": 3.5})
    assert ss.validate({"MaxConcurrent": 3})["MaxConcurrent"] == 3


def test_reject_non_numeric_string():
    with pytest.raises(ss.SettingsValidationError):
        ss.validate({"RiskPercent": "high"})


def test_zero_is_never_coerced_to_one():
    # regola 7: nessuna coercizione magica del moltiplicatore 0 -> 1
    assert ss.validate({"MaxSpreadPoints": 0})["MaxSpreadPoints"] == 0


def test_unknown_key_rejected_by_default_but_passthrough_when_allowed():
    with pytest.raises(ss.SettingsValidationError):
        ss.validate({"TotallyUnknown": 1})
    out = ss.validate({"TotallyUnknown": 1, "RiskPercent": 1.0}, allow_unknown=True)
    assert out["TotallyUnknown"] == 1 and out["RiskPercent"] == 1.0


def test_structured_errors_list():
    try:
        ss.validate({"RiskPercent": 999, "MaxConcurrent": 3.5})
    except ss.SettingsValidationError as e:
        keys = {err["key"] for err in e.errors}
        assert {"RiskPercent", "MaxConcurrent"} <= keys


# ---------------------------------------------------- profili versionati ----
def test_locked_profile_has_version_and_checksum():
    p = backend.build_locked_profile({"RiskPercent": 1.0, "MaxLot": 5.0})
    assert p["version"] == 1
    assert p["schema_version"] == ss.schema_version()
    assert len(p["checksum"]) == 16
    # checksum deterministico
    p2 = backend.build_locked_profile({"MaxLot": 5.0, "RiskPercent": 1.0},
                                      profile_id=p["profile_id"])
    assert p2["checksum"] == p["checksum"]


def test_locked_profile_rejects_invalid_settings():
    with pytest.raises(ss.SettingsValidationError):
        backend.build_locked_profile({"RiskPercent": 999})


# ---------------------------------------------------- endpoint --------------
def test_settings_schema_endpoint(client):
    h = _auth(client)
    r = client.get("/api/settings/schema", headers=h)
    assert r.status_code == 200
    assert r.json()["schema_version"] == ss.schema_version()
    assert len(r.json()["defaults"]) == len(ss.default_settings())


def test_settings_put_rejects_invalid(client):
    h = _auth(client)
    r = client.put("/api/settings", json={"RiskPercent": 999}, headers=h)
    assert r.status_code == 422
    assert "errors" in r.json()["detail"]


def test_settings_put_accepts_valid_and_ui_state(client):
    h = _auth(client)
    r = client.put("/api/settings",
                   json={"RiskPercent": 1.5, "strategies": {"MACD": True}}, headers=h)
    assert r.status_code == 200, r.text


def test_settings_validate_dryrun(client):
    h = _auth(client)
    r = client.post("/api/settings/validate", json={"MaxDailyDDPct": -5}, headers=h)
    assert r.status_code == 200 and r.json()["valid"] is False
