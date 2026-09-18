import csv

import pytest
from fastapi.testclient import TestClient

import app as backend
import market_read_model


def _csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def _catalog(tmp_path):
    data = tmp_path / "server/research_scripts/phase5/data"
    _csv(data / "market_state_dataset_v1.csv", [{
        "bar_time_utc": "2022-01-01T00:00:00Z", "directional_efficiency": "0.7",
        "ema_slope_atr_norm": "0.2", "atr_percentile": "80",
        "position_in_rolling_range": "", "compression_percentile": "10", "roc": "-0.01",
    }, {
        "bar_time_utc": "not-a-date", "directional_efficiency": "", "ema_slope_atr_norm": "",
        "atr_percentile": "", "position_in_rolling_range": "", "compression_percentile": "", "roc": "",
    }])
    _csv(data / "events_v1.csv", [{
        "event_id": "EVT-1", "event_family": "SWEEP", "timestamp": "2022-01-01T00:00:00Z",
        "direction": "1", "magnitude": "", "observation_point": "bar_close", "detector_provenance": "sweep_v1",
    }, {
        "event_id": "BAD", "event_family": "", "timestamp": "broken", "direction": "", "magnitude": "",
        "observation_point": "", "detector_provenance": "",
    }])
    return market_read_model.MarketCatalog(tmp_path)


def test_state_source_nulls_and_deterministic_output(tmp_path):
    catalog = _catalog(tmp_path)
    first, warnings = catalog.states()
    second, _ = catalog.states()
    assert first == second
    assert len(first) == 1
    state = first[0]
    assert state["source_domain"] == "RESEARCH"
    assert state["semantic_parity"] == "NONE"
    assert state["range_position"] is None
    assert state["trend_state"] == "UP"
    assert any(item["code"] == "MALFORMED_RECORD" for item in warnings)


def test_events_are_real_filtered_records_and_bad_rows_are_isolated(tmp_path):
    events, warnings = _catalog(tmp_path).events()
    assert [event["event_id"] for event in events] == ["EVT-1"]
    assert events[0]["magnitude"] is None
    assert events[0]["family"] == "SWEEP"
    assert any(item["code"] == "MALFORMED_RECORD" for item in warnings)


def test_missing_artifacts_return_empty_catalog_with_warnings(tmp_path):
    states, warnings = market_read_model.MarketCatalog(tmp_path).states()
    assert states == []
    assert warnings and all(item["code"] == "MISSING_ARTIFACT" for item in warnings)


def test_operational_snapshot_is_partial_and_does_not_fill_research_fields():
    snapshot = market_read_model.operational_snapshot({"symbol": "XAUUSD", "_online": True, "_updated_ago": 2, "volRegime": "HIGH"})
    assert snapshot["source_domain"] == "OPERATIONAL"
    assert snapshot["semantic_parity"] == "PARTIAL"
    assert snapshot["directional_efficiency"] is None
    assert snapshot["provenance"]["type"] == "LIVE"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "market.db"))
    backend.init_db()
    catalog = _catalog(tmp_path)
    monkeypatch.setattr(market_read_model, "CATALOG", catalog)
    with TestClient(backend.app) as value:
        login = value.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        value.headers.update({"Authorization": f"Bearer {login.json()['token']}"})
        yield value


def test_market_routes_are_authenticated(client):
    with TestClient(backend.app) as anonymous:
        assert anonymous.get("/api/market/state").status_code == 401
    assert client.get("/api/market/state/latest").status_code == 200


def test_latest_and_event_filters(client):
    latest = client.get("/api/market/state/latest?symbol=XAUUSD&timeframe=H4").json()
    assert latest["research"]["source_domain"] == "RESEARCH"
    assert latest["operational"] is None
    response = client.get("/api/market/events?event_family=SWEEP&direction=1&from=2021-01-01T00:00:00Z")
    assert response.status_code == 200
    assert [item["event_id"] for item in response.json()["items"]] == ["EVT-1"]
    assert client.get("/api/market/events/EVT-1").status_code == 200
    assert client.get("/api/market/events/not-found").status_code == 404
