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

def _resolve_registry_path() -> str:
    # Layout locale (repo/server/strategy_registry.py -> repo/contracts/...) e
    # layout immagine Docker (/app/strategy_registry.py -> /app/contracts/...,
    # perche' il Dockerfile appiattisce server/ dentro /app) risalgono di un
    # numero diverso di livelli. Si prova prima il sibling (Docker), poi il
    # doppio dirname (locale): si usa quello che esiste davvero sul disco.
    here = os.path.dirname(os.path.abspath(__file__))
    sibling = os.path.join(here, "contracts", "strategy-registry.json")
    if os.path.exists(sibling):
        return sibling
    return os.path.join(os.path.dirname(here), "contracts", "strategy-registry.json")


_REGISTRY_PATH = _resolve_registry_path()


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


def research_ids() -> list:
    """Nomi accettati dal motore research, inclusi gli alias di implementazione."""
    result = []
    for record in _load()["strategies"]:
        if not record.get("research_implementation"):
            continue
        result.append((record.get("aliases") or [record["strategy_id"]])[0])
    return sorted(result)


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


def require_strategy(name: str, *, live: bool = False, research: bool = False) -> str:
    """Valida un nome e restituisce l'id usato dal contesto richiesto."""
    record = resolve(name)
    if live and not record.get("live_implementation"):
        raise ValueError(f"strategia non disponibile live: {name!r}")
    if research and not record.get("research_implementation"):
        raise ValueError(f"strategia non disponibile nel motore research: {name!r}")
    if research:
        return (record.get("aliases") or [record["strategy_id"]])[0]
    return record["strategy_id"]


def require_strategies(names, *, live: bool = False, research: bool = False) -> tuple:
    return tuple(require_strategy(name, live=live, research=research) for name in names)


# Adapter compatibili per i consumer esistenti; tutti derivati dal contratto.
REGISTRY = registry_artifact()
STRATEGIES = all_records()
BY_ID = {record["strategy_id"]: record for record in STRATEGIES}
LIVE_STRATEGY_IDS = tuple(live_ids())
RESEARCH_STRATEGY_IDS = tuple(research_ids())
AUTO_DISABLE_IDS = frozenset(
    record["strategy_id"] for record in STRATEGIES
    if record.get("auto_disable_eligible")
)
