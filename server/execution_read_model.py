"""Read-only canonical view over existing NEXUS execution telemetry."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "execution-read-model-v1"


def _freshness(primary: dict | None) -> dict[str, Any]:
    if not primary:
        return {"state": "UNAVAILABLE", "age_seconds": None, "timestamp": None}
    age = primary.get("_updated_ago")
    timestamp = None
    if isinstance(age, (int, float)):
        timestamp = datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() - age, timezone.utc
        ).isoformat().replace("+00:00", "Z")
    return {
        "state": "LIVE" if primary.get("_online") else "STALE",
        "age_seconds": age,
        "timestamp": timestamp,
    }


def build_snapshot(*, primary: dict | None, settings: dict | None,
                   health: dict | None, bridge: dict | None,
                   leaderboard: list[dict] | None,
                   allocation_config: dict | None,
                   recent_trades: list[dict] | None) -> dict[str, Any]:
    freshness = _freshness(primary)
    positions = primary.get("positions") if isinstance(primary, dict) else None
    strategies = settings.get("strategies") if isinstance(settings, dict) else None
    board = {item.get("name"): item for item in (leaderboard or []) if item.get("name")}
    engines = []
    if isinstance(strategies, dict):
        for engine_id in sorted(strategies):
            stats = board.get(engine_id)
            engines.append({
                "engine_id": engine_id,
                "enabled": bool(strategies[engine_id]),
                "configuration_status": "ENABLED" if strategies[engine_id] else "DISABLED",
                "runtime_status": "UNAVAILABLE",
                "risk_multiplier": stats.get("effective_mult") if stats else None,
                "latest_execution_stats": ({
                    "trades": stats.get("trades"), "win_rate": stats.get("win_rate"),
                    "profit_factor": stats.get("profit_factor"), "net": stats.get("net"),
                } if stats and stats.get("trades") else None),
                "provenance": "DERIVED" if stats else "CACHED",
                "canonical_strategy_status": "UNAVAILABLE",
            })

    worker = (bridge or {}).get("worker") or {}
    commands = (bridge or {}).get("commands") or []
    failed_commands = [command for command in commands if command.get("status") in {"FAILED_FINAL", "EXPIRED"}]
    protections = []
    if isinstance(primary, dict):
        protections = [name for name, key in (
            ("ESL", "eslHit"), ("DPT", "dptHit"),
            ("NEWS", "newsBlock"), ("PAUSED", "eaPaused"),
        ) if primary.get(key) is True]

    protection_fields = {"eslHit", "dptHit", "newsBlock", "eaPaused"}
    protections_known = bool(primary and protection_fields.intersection(primary))
    risk = {
        "state": "UNAVAILABLE" if not protections_known else ("BLOCKED" if protections else "CLEAR"),
        "drawdown_pct": primary.get("drawdownPct") if primary else None,
        "floating_pnl": primary.get("floatPnL") if primary else None,
        "exposure": primary.get("exposure") if primary else None,
        "margin_level": primary.get("marginLevel") if primary else None,
        "protections": protections,
        "max_daily_dd_pct": settings.get("MaxDailyDDPct") if settings else None,
        "max_concurrent": settings.get("MaxConcurrent") if settings else None,
        "provenance": freshness["state"],
    }
    trades = recent_trades or []
    available = []
    if any(trade.get("openTime") for trade in trades):
        available.append("position_open_time")
    if any(trade.get("closeTime") for trade in trades):
        available.append("position_close_time")
    missing = ["signal_timestamp", "order_sent_timestamp", "fill_timestamp",
               "requested_price", "fill_price", "slippage", "reject_reason"]
    if "position_open_time" not in available:
        missing.append("position_open_time")
    if "position_close_time" not in available:
        missing.append("position_close_time")
    quality = {
        "state": "UNAVAILABLE",
        "message": "Signal-to-fill telemetry incomplete",
        "available": available,
        "missing": missing,
        "provenance": "UNAVAILABLE",
    }
    if available:
        quality["state"] = "PARTIAL"
        quality["provenance"] = "DERIVED"

    return {
        "schema_version": SCHEMA_VERSION,
        "source_domain": "OPERATIONAL",
        "freshness": freshness,
        "ea": {
            "state": "UNAVAILABLE" if primary is None else ("LIVE" if primary.get("_online") else "STALE"),
            "paused": primary.get("eaPaused") if primary else None,
            "account": (primary.get("account") or primary.get("login") or primary.get("account_id")) if primary else None,
            "symbol": primary.get("symbol") if primary else None,
            "balance": primary.get("balance") if primary else None,
            "equity": primary.get("equity") if primary else None,
            "provenance": freshness["state"],
        },
        "positions": {"state": freshness["state"] if isinstance(positions, list) else "UNAVAILABLE",
                      "items": positions, "provenance": freshness["state"]},
        "risk": risk,
        "bridge": {
            "state": "LIVE" if worker.get("online") else ("STALE" if worker else "UNAVAILABLE"),
            "worker": worker or None, "commands": commands[:20],
            "failed_command_count": len(failed_commands),
            "provenance": "LIVE" if worker.get("online") else ("CACHED" if worker else "UNAVAILABLE"),
        },
        "engines": {"state": "CACHED" if isinstance(strategies, dict) else "UNAVAILABLE",
                    "items": engines, "provenance": "CACHED" if isinstance(strategies, dict) else "UNAVAILABLE"},
        "allocation": {"state": "DERIVED" if leaderboard is not None else "UNAVAILABLE",
                       "config": allocation_config, "items": leaderboard,
                       "provenance": "DERIVED" if leaderboard is not None else "UNAVAILABLE"},
        "recent_trades": {"state": "DERIVED" if recent_trades is not None else "UNAVAILABLE",
                          "items": recent_trades, "provenance": "DERIVED" if recent_trades is not None else "UNAVAILABLE"},
        "execution_quality": quality,
        "health": health,
    }
