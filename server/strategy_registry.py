"""Canonical strategy registry loader and validation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "contracts" / "strategy-registry.json"
VALID_STATUSES = {"ACTIVE", "EXPERIMENTAL", "SHADOW_ONLY", "RESEARCH_ONLY", "DEPRECATED", "DISABLED"}
VALID_PARITY = {"EXACT", "FUNCTIONALLY_EQUIVALENT", "APPROXIMATE", "PROXY", "NOT_IMPLEMENTED"}
REQUIRED = {"strategy_id","display_name","family","status","live_implementation","research_implementation","research_parity","proxy_for","supported_symbols","supported_timeframes","default_enabled","risk_class","auto_disable_eligible","selector_index","schema_version"}


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("strategies"), list):
        raise ValueError("invalid strategy registry envelope")
    ids: set[str] = set()
    selectors: set[int] = set()
    for index, record in enumerate(data["strategies"]):
        missing = REQUIRED - set(record)
        if missing:
            raise ValueError(f"strategy[{index}] missing fields: {sorted(missing)}")
        strategy_id = record["strategy_id"]
        if not isinstance(strategy_id, str) or not strategy_id or strategy_id != strategy_id.upper():
            raise ValueError(f"invalid strategy_id: {strategy_id!r}")
        if strategy_id in ids:
            raise ValueError(f"duplicate strategy_id: {strategy_id}")
        ids.add(strategy_id)
        if record["status"] not in VALID_STATUSES or record["research_parity"] not in VALID_PARITY:
            raise ValueError(f"invalid status/parity for {strategy_id}")
        selector = record["selector_index"]
        if selector is not None:
            if not isinstance(selector, int) or selector < 1 or selector in selectors:
                raise ValueError(f"invalid/duplicate selector_index for {strategy_id}")
            selectors.add(selector)
        if record["status"] == "RESEARCH_ONLY" and record["live_implementation"]:
            raise ValueError(f"research-only strategy cannot be live: {strategy_id}")
        if record["research_parity"] == "PROXY" and not record["proxy_for"]:
            raise ValueError(f"proxy target missing for {strategy_id}")
    for record in data["strategies"]:
        if record["proxy_for"] is not None and record["proxy_for"] not in ids:
            raise ValueError(f"unknown proxy target for {record['strategy_id']}: {record['proxy_for']}")
    return data


REGISTRY = load_registry()
STRATEGIES = tuple(REGISTRY["strategies"])
BY_ID = {record["strategy_id"]: record for record in STRATEGIES}
LIVE_STRATEGY_IDS = tuple(record["strategy_id"] for record in STRATEGIES if record["live_implementation"])
RESEARCH_STRATEGY_IDS = tuple(record["strategy_id"] for record in STRATEGIES if record["research_implementation"])
AUTO_DISABLE_IDS = frozenset(record["strategy_id"] for record in STRATEGIES if record["auto_disable_eligible"])


def require_strategy(strategy_id: str, *, research: bool = False) -> dict:
    record = BY_ID.get(strategy_id)
    if record is None:
        raise ValueError(f"unknown strategy_id: {strategy_id}")
    capability = "research_implementation" if research else "live_implementation"
    if not record[capability]:
        raise ValueError(f"strategy {strategy_id} has no {'research' if research else 'live'} implementation")
    return record


def require_strategies(strategy_ids: Iterable[str], *, research: bool = False) -> tuple[str, ...]:
    values = tuple(strategy_ids)
    for strategy_id in values:
        require_strategy(strategy_id, research=research)
    return values
