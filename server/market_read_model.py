"""Canonical, read-only Market State catalog backed by structured research artifacts."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "market-read-model-v1"
MAX_ROWS = 5000


def _value(value: Any) -> Any:
    if value is None or value == "":
        return None
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except (TypeError, ValueError):
        return value


def _iso(value: Any) -> str | None:
    if value in (None, ""):
        return None
    raw = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return None


def _stable_id(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]
    return f"{prefix}-{digest}"


class MarketCatalog:
    def __init__(self, root: Path | None = None):
        module = Path(__file__).resolve().parent
        supplied = root.resolve() if root else None
        if (supplied and (supplied / "research_scripts").is_dir()) or (not root and (module / "research_scripts").is_dir()):
            self.root = supplied or module
        else:
            self.root = (supplied or module.parent) / "server"
        self.sources = [
            ("PHASE_5", self.root / "research_scripts/phase5/data/market_state_dataset_v1.csv", self.root / "research_scripts/phase5/data/events_v1.csv"),
            ("PHASE_6", self.root / "research_scripts/phase6/data/market_state_dataset_holdout.csv", self.root / "research_scripts/phase6/data/events_holdout.csv"),
        ]
        self._cache: dict[tuple[str, int, int, int], list[dict]] = {}

    def _rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.name

    def _rows(self, path: Path, warnings: list[dict], limit: int = MAX_ROWS) -> list[dict]:
        if not path.is_file():
            warnings.append({"code": "MISSING_ARTIFACT", "source_file": self._rel(path)})
            return []
        try:
            stat = path.stat()
            key = (str(path), stat.st_mtime_ns, stat.st_size, min(max(limit, 1), MAX_ROWS))
            if key in self._cache:
                return [dict(row) for row in self._cache[key]]
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(deque(csv.DictReader(handle), maxlen=key[-1]))
            self._cache = {cached_key: value for cached_key, value in self._cache.items() if cached_key[0] != str(path)}
            self._cache[key] = rows
            return [dict(row) for row in rows]
        except (OSError, UnicodeError, csv.Error) as exc:
            warnings.append({"code": "MALFORMED_ARTIFACT", "source_file": self._rel(path), "detail": type(exc).__name__})
            return []

    def states(self, limit: int = 500) -> tuple[list[dict], list[dict]]:
        warnings: list[dict] = []
        result: list[dict] = []
        for phase, state_path, _ in self.sources:
            for row in self._rows(state_path, warnings, limit):
                timestamp = _iso(row.get("bar_time_utc") or row.get("timestamp"))
                if not timestamp:
                    warnings.append({"code": "MALFORMED_RECORD", "source_file": self._rel(state_path)})
                    continue
                efficiency = _value(row.get("directional_efficiency"))
                slope = _value(row.get("ema_slope_atr_norm"))
                atr_pct = _value(row.get("atr_percentile"))
                range_pos = _value(row.get("position_in_rolling_range"))
                compression = _value(row.get("compression_percentile"))
                roc = _value(row.get("roc"))
                # Named states are deterministic read-model interpretations of numeric artifact fields.
                trend = None if slope is None else ("UP" if slope > 0 else "DOWN" if slope < 0 else "FLAT")
                volatility = None if atr_pct is None else ("HIGH" if atr_pct >= 67 else "LOW" if atr_pct <= 33 else "NORMAL")
                momentum = None if roc is None else ("POSITIVE" if roc > 0 else "NEGATIVE" if roc < 0 else "NEUTRAL")
                compression_state = None if compression is None else ("COMPRESSED" if compression < 20 else "RELEASED")
                location = None if range_pos is None else ("UPPER_RANGE" if range_pos >= .67 else "LOWER_RANGE" if range_pos <= .33 else "MID_RANGE")
                regime = None
                if trend and volatility:
                    regime = f"{trend}_{volatility}"
                source = self._rel(state_path)
                result.append({
                    "id": _stable_id("MSS", source, timestamp), "timestamp": timestamp,
                    "symbol": "XAUUSD", "timeframe": "H4", "source": phase,
                    "source_mode": "HISTORICAL_RESEARCH_ARTIFACT", "source_domain": "RESEARCH",
                    "semantic_parity": "NONE", "schema_version": SCHEMA_VERSION,
                    "regime": regime, "volatility_state": volatility, "trend_state": trend,
                    "directional_efficiency": efficiency, "momentum_state": momentum,
                    "structure_state": None, "range_position": range_pos,
                    "compression_state": compression_state, "location_state": location,
                    "data_quality": "STRUCTURED_ARTIFACT",
                    "limitations": ["Categorical states are derived by read-model-v1 from numeric Phase 5/6 features.", "No semantic equivalence with EA runtime state has been established."],
                    "provenance": {"type": "DERIVED", "source_file": source, "row_timestamp": timestamp},
                })
        result.sort(key=lambda item: (item["timestamp"], item["id"]))
        return result[-limit:], warnings

    def events(self, limit: int = 500) -> tuple[list[dict], list[dict]]:
        warnings: list[dict] = []
        result: list[dict] = []
        for phase, state_path, event_path in self.sources:
            for row in self._rows(event_path, warnings, limit):
                timestamp = _iso(row.get("timestamp"))
                family = row.get("event_family") or row.get("family")
                if not timestamp or not family:
                    warnings.append({"code": "MALFORMED_RECORD", "source_file": self._rel(event_path)})
                    continue
                direction = _value(row.get("direction"))
                event_id = row.get("event_id") or _stable_id("EVT", phase, family, timestamp, direction)
                source = self._rel(event_path)
                state_id = _stable_id("MSS", self._rel(state_path), timestamp)
                result.append({
                    "event_id": event_id, "family": family, "timestamp": timestamp,
                    "symbol": "XAUUSD", "timeframe": "H4", "direction": direction,
                    "magnitude": _value(row.get("magnitude")),
                    "observation_point": row.get("observation_point") or None,
                    "detector_version": row.get("detector_provenance") or None,
                    "source_dataset": source, "state_snapshot_id": state_id,
                    "linked_research_entity_id": None,
                    "limitations": ["Historical research event; not a live EA event."],
                    "source_domain": "RESEARCH", "semantic_parity": "NONE",
                    "provenance": {"type": "RESEARCH", "source": phase, "source_file": source},
                })
        result.sort(key=lambda item: (item["timestamp"], item["event_id"]), reverse=True)
        return result[:limit], warnings


def operational_snapshot(status: dict | None) -> dict | None:
    if not status:
        return None
    timestamp = None
    age = status.get("_updated_ago")
    if isinstance(age, (int, float)):
        timestamp = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() - age, timezone.utc).isoformat().replace("+00:00", "Z")
    symbol = status.get("symbol")
    return {
        "id": _stable_id("MSS-OP", status.get("account_id"), symbol, timestamp),
        "timestamp": timestamp, "symbol": symbol, "timeframe": status.get("timeframe"),
        "source": "EA_STATUS", "source_mode": "RUNTIME_TELEMETRY", "source_domain": "OPERATIONAL",
        "semantic_parity": "PARTIAL", "schema_version": SCHEMA_VERSION,
        "regime": status.get("marketRegime") or status.get("regime"),
        "volatility_state": status.get("volRegime"), "trend_state": status.get("htfBias"),
        "directional_efficiency": None, "momentum_state": status.get("velocity"),
        "structure_state": status.get("structure"), "range_position": None,
        "compression_state": None, "location_state": None,
        "data_quality": "CURRENT" if status.get("_online") else "STALE",
        "limitations": ["EA telemetry does not implement the canonical research feature schema; parity is partial."],
        "provenance": {"type": "LIVE" if status.get("_online") else "CACHED", "source_endpoint": "/api/ea/status"},
    }


CATALOG = MarketCatalog()
