"""PR6 — Loader del Canonical Strategy Registry per il backend.

Unica fonte di verita' per il backend: `contracts/strategy-registry.json`.
Rimpiazza i conteggi hardcoded (STRAT_NAMES_36 -> 36) con dati derivati dal
registry (37 live) e impone la Regola 1 del pack: un id sconosciuto e' un
errore, mai fallback silenzioso.
"""
from __future__ import annotations
import json
import os
from functools import lru_cache

_REGISTRY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "contracts", "strategy-registry.json")


class UnknownStrategyError(KeyError):
    """Sollevata quando un id/alias non risolve nel registry (no fallback)."""


@lru_cache(maxsize=1)
def _load() -> dict:
    with open(_REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _index() -> dict:
    idx = {}
    for r in _load()["strategies"]:
        idx[r["strategy_id"]] = r
        for a in r.get("aliases", []):
            idx[a] = r
    return idx


def all_records() -> list:
    return list(_load()["strategies"])


def live_ids() -> list:
    """Id canonici delle strategie LIVE (ordinati). Sostituisce STRAT_NAMES_36."""
    return sorted(r["strategy_id"] for r in _load()["strategies"]
                  if r.get("live_implementation"))


def research_only_ids() -> list:
    return sorted(r["strategy_id"] for r in _load()["strategies"]
                  if r.get("status") == "RESEARCH_ONLY")


def count_live() -> int:
    return len(live_ids())


def is_known(name: str) -> bool:
    return name in _index()


def resolve(name: str) -> dict:
    """Record canonico per id o alias. Solleva UnknownStrategyError se ignoto."""
    idx = _index()
    if name not in idx:
        raise UnknownStrategyError(
            f"strategia sconosciuta: {name!r} (nessun fallback silenzioso)")
    return idx[name]


def canonical_id(name: str) -> str:
    """Normalizza un id/alias (es. 'CISD' -> 'THREE_BAR_DELIVERY_BREAK')."""
    return resolve(name)["strategy_id"]


def registry_artifact() -> dict:
    """Il registry completo, per esposizione read-only via API."""
    return _load()
