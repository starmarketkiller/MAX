from fastapi.testclient import TestClient

import app as backend
import execution_read_model


def _snapshot(**overrides):
    values = {
        "primary": {"_online": True, "_updated_ago": 2, "symbol": "XAUUSD", "balance": 1000,
                    "equity": 1010, "positions": [{"ticket": 7, "pnl": 10}], "drawdownPct": 1},
        "settings": {"strategies": {"ADX_RSI": True, "SAR": False}, "MaxDailyDDPct": 5},
        "health": {"score": 80},
        "bridge": {"worker": {"online": True, "host_id": "host-1"}, "commands": []},
        "leaderboard": [{"name": "ADX_RSI", "trades": 4, "win_rate": 50, "profit_factor": 1.2,
                         "net": 10, "effective_mult": 1.1}],
        "allocation_config": {"enabled": True},
        "recent_trades": [{"ticket": 1, "openTime": "2026-01-01T00:00:00Z"}],
    }
    values.update(overrides)
    return execution_read_model.build_snapshot(**values)


def test_execution_snapshot_separates_runtime_engines_from_canonical_strategy():
    snapshot = _snapshot()
    engine = next(item for item in snapshot["engines"]["items"] if item["engine_id"] == "ADX_RSI")
    assert engine["enabled"] is True
    assert engine["configuration_status"] == "ENABLED"
    assert engine["runtime_status"] == "UNAVAILABLE"
    assert engine["risk_multiplier"] == 1.1
    assert engine["canonical_strategy_status"] == "UNAVAILABLE"
    assert engine["latest_execution_stats"]["trades"] == 4


def test_missing_entities_remain_unavailable_and_null():
    snapshot = _snapshot(primary=None, settings=None, bridge=None, leaderboard=None,
                         allocation_config=None, recent_trades=None)
    assert snapshot["ea"]["state"] == "UNAVAILABLE"
    assert snapshot["positions"]["items"] is None
    assert snapshot["risk"]["drawdown_pct"] is None
    assert snapshot["engines"]["state"] == "UNAVAILABLE"
    assert snapshot["execution_quality"]["state"] == "UNAVAILABLE"


def test_stale_state_and_failed_bridge_commands_are_explicit():
    snapshot = _snapshot(
        primary={"_online": False, "_updated_ago": 120, "positions": []},
        bridge={"worker": {"online": False}, "commands": [{"status": "FAILED_FINAL"}]},
    )
    assert snapshot["freshness"]["state"] == "STALE"
    assert snapshot["bridge"]["state"] == "STALE"
    assert snapshot["bridge"]["failed_command_count"] == 1


def test_signal_to_fill_is_partial_only_when_position_timing_exists():
    assert _snapshot()["execution_quality"]["state"] == "PARTIAL"
    unavailable = _snapshot(recent_trades=[])["execution_quality"]
    assert unavailable["state"] == "UNAVAILABLE"
    assert "signal_timestamp" in unavailable["missing"]
    assert unavailable.get("slippage") is None


def test_execution_route_requires_auth_and_returns_read_only_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "execution.db"))
    backend.init_db()
    with TestClient(backend.app) as client:
        assert client.get("/api/execution/snapshot").status_code == 401
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        response = client.get("/api/execution/snapshot", headers={"Authorization": f"Bearer {login.json()['token']}"})
        assert response.status_code == 200
        body = response.json()
        assert body["schema_version"] == "execution-read-model-v1"
        assert body["ea"]["state"] == "UNAVAILABLE"
        assert body["execution_quality"]["state"] == "UNAVAILABLE"
