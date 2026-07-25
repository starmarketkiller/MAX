"""Validazione tipata dei documenti che finivano nel KV senza controlli.

L'audit ha rilevato più rotte che accettavano JSON arbitrario e lo
persistevano così com'era, per poi darlo in pasto all'EA o alla ricerca:

* AUD0-VAL-001 / AUD0-BE-ROUTE-008 — `strategy_chain/config`
* AUD0-VAL-004 — tag, rating e note del journal
* AUD0-VAL-006 / AUD0-BE-BT-004 — setup del Creator

Modulo puro: nessun I/O, nessuna dipendenza da FastAPI.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

SCHEMA_VERSION = 1

_TAG_RE = re.compile(r"^[\w\- ]{1,32}$", re.UNICODE)
_STRATEGY_RE = re.compile(r"^[A-Z0-9_]{2,48}$")


class ValidationError(ValueError):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def _number(field: str, value: Any, *, minimum: float, maximum: float,
            default: float | None = None) -> float:
    if value is None and default is not None:
        return default
    try:
        n = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(field, "valore non numerico") from exc
    if n != n or n in (float("inf"), float("-inf")):
        raise ValidationError(field, "valore non finito")
    if not (minimum <= n <= maximum):
        raise ValidationError(field, f"fuori range [{minimum}, {maximum}]")
    return n


def _integer(field: str, value: Any, *, minimum: int, maximum: int,
             default: int | None = None) -> int:
    if value is None and default is not None:
        return default
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(field, "valore non intero") from exc
    if not (minimum <= n <= maximum):
        raise ValidationError(field, f"fuori range [{minimum}, {maximum}]")
    return n


def _boolean(field: str, value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    raise ValidationError(field, "valore booleano atteso")


# --------------------------------------------------------------------------- #
# Strategy chain — AUD0-VAL-001
# --------------------------------------------------------------------------- #
CHAIN_MAX_BRIDGES = 64
CHAIN_MAX_TARGETS_PER_BRIDGE = 16


def validate_chain_config(raw: Any, known_strategies: Iterable[str]) -> dict:
    """Valida la configurazione della strategy chain.

    Prima il PUT scriveva l'intero JSON della richiesta dentro `kv` senza
    schema, senza limiti numerici e senza verificare che gli identificativi di
    strategia esistessero. Una configurazione malformata veniva poi letta
    dall'EA e usata per decidere trade reali.
    """
    if not isinstance(raw, dict):
        raise ValidationError("config", "oggetto atteso")

    known = set(known_strategies)
    out = {
        "schema_version": SCHEMA_VERSION,
        "enable_continuation": _boolean("enable_continuation",
                                        raw.get("enable_continuation"), True),
        "enable_smart_reverse": _boolean("enable_smart_reverse",
                                         raw.get("enable_smart_reverse"), True),
        "continuation_window_sec": _integer("continuation_window_sec",
                                            raw.get("continuation_window_sec"),
                                            minimum=0, maximum=86400, default=1800),
        "continuation_lot_mult": _number("continuation_lot_mult",
                                         raw.get("continuation_lot_mult"),
                                         minimum=0.0, maximum=3.0, default=0.6),
        "max_continuations": _integer("max_continuations", raw.get("max_continuations"),
                                      minimum=0, maximum=20, default=3),
        "reverse_min_reaction": _number("reverse_min_reaction",
                                        raw.get("reverse_min_reaction"),
                                        minimum=0.0, maximum=100.0, default=75.0),
        "reverse_close_threshold_strong": _number(
            "reverse_close_threshold_strong", raw.get("reverse_close_threshold_strong"),
            minimum=0.0, maximum=100.0, default=55.0),
    }

    bridges_raw = raw.get("bridges")
    if bridges_raw is None:
        bridges_raw = {}
    if not isinstance(bridges_raw, dict):
        raise ValidationError("bridges", "oggetto atteso")
    if len(bridges_raw) > CHAIN_MAX_BRIDGES:
        raise ValidationError("bridges", f"massimo {CHAIN_MAX_BRIDGES} voci")

    bridges: dict[str, list[str]] = {}
    for source, targets in bridges_raw.items():
        source = str(source)
        if not _STRATEGY_RE.match(source):
            raise ValidationError(f"bridges.{source}", "identificativo non valido")
        if known and source not in known:
            raise ValidationError(f"bridges.{source}", "strategia sconosciuta")
        if not isinstance(targets, list):
            raise ValidationError(f"bridges.{source}", "lista attesa")
        if len(targets) > CHAIN_MAX_TARGETS_PER_BRIDGE:
            raise ValidationError(f"bridges.{source}",
                                  f"massimo {CHAIN_MAX_TARGETS_PER_BRIDGE} destinazioni")
        clean_targets = []
        for target in targets:
            target = str(target)
            if not _STRATEGY_RE.match(target):
                raise ValidationError(f"bridges.{source}", f"destinazione non valida: {target}")
            if known and target not in known:
                raise ValidationError(f"bridges.{source}", f"strategia sconosciuta: {target}")
            clean_targets.append(target)
        bridges[source] = clean_targets

    out["bridges"] = bridges
    return out


# --------------------------------------------------------------------------- #
# Journal — AUD0-VAL-004
# --------------------------------------------------------------------------- #
JOURNAL_MAX_TAGS = 20
JOURNAL_MAX_NOTE = 4000
JOURNAL_RATING_MIN = 1
JOURNAL_RATING_MAX = 5


def validate_journal_meta(raw: Any) -> dict:
    """Valida tag, rating e nota di un trade.

    Prima la rotta accettava array di tag arbitrari, note di lunghezza
    illimitata e rating senza range: righe enormi in database e valori che la
    UI non sa rappresentare.
    """
    if not isinstance(raw, dict):
        raise ValidationError("body", "oggetto atteso")
    out: dict[str, Any] = {}

    if "tags" in raw and raw["tags"] is not None:
        tags = raw["tags"]
        if isinstance(tags, str):
            tags = [tags]
        if not isinstance(tags, list):
            raise ValidationError("tags", "lista attesa")
        if len(tags) > JOURNAL_MAX_TAGS:
            raise ValidationError("tags", f"massimo {JOURNAL_MAX_TAGS} tag")
        clean = []
        for tag in tags:
            tag = str(tag).strip()
            if not tag:
                continue
            if not _TAG_RE.match(tag):
                raise ValidationError("tags", f"tag non valido: {tag!r}")
            if tag not in clean:
                clean.append(tag)
        out["tags"] = clean

    if "rating" in raw and raw["rating"] is not None:
        out["rating"] = _integer("rating", raw["rating"],
                                 minimum=JOURNAL_RATING_MIN, maximum=JOURNAL_RATING_MAX)

    if "note" in raw and raw["note"] is not None:
        note = str(raw["note"])
        if len(note) > JOURNAL_MAX_NOTE:
            raise ValidationError("note", f"massimo {JOURNAL_MAX_NOTE} caratteri")
        out["note"] = note

    return out


# --------------------------------------------------------------------------- #
# Creator setup — AUD0-VAL-006
# --------------------------------------------------------------------------- #
CREATOR_MAX_COMBO = 12
CREATOR_MAX_PARAM_KEYS = 40
CREATOR_MAX_SERIALIZED = 32 * 1024


def validate_creator_setup(raw: Any, known_strategies: Iterable[str]) -> dict:
    """Valida un setup del Creator prima di persistere.

    Prima la rotta verificava solo la presenza di `combo`, poi mutava
    l'oggetto in ingresso e lo salvava: struttura illimitata e identificativi
    di strategia mai verificati.
    """
    import json as _json

    if not isinstance(raw, dict):
        raise ValidationError("setup", "oggetto atteso")

    combo = raw.get("combo")
    if isinstance(combo, str):
        combo = [combo]
    if not isinstance(combo, list) or not combo:
        raise ValidationError("setup.combo", "lista non vuota attesa")
    if len(combo) > CREATOR_MAX_COMBO:
        raise ValidationError("setup.combo", f"massimo {CREATOR_MAX_COMBO} strategie")

    known = set(known_strategies)
    clean_combo = []
    for name in combo:
        name = str(name)
        if not _STRATEGY_RE.match(name):
            raise ValidationError("setup.combo", f"identificativo non valido: {name}")
        if known and name not in known:
            raise ValidationError("setup.combo", f"strategia sconosciuta: {name}")
        clean_combo.append(name)

    params = raw.get("params") or {}
    if not isinstance(params, dict):
        raise ValidationError("setup.params", "oggetto atteso")
    if len(params) > CREATOR_MAX_PARAM_KEYS:
        raise ValidationError("setup.params", f"massimo {CREATOR_MAX_PARAM_KEYS} chiavi")
    clean_params = {}
    for key, value in params.items():
        key = str(key)[:48]
        if isinstance(value, (int, float, bool)) or value is None:
            clean_params[key] = value
        elif isinstance(value, str):
            clean_params[key] = value[:200]
        else:
            raise ValidationError(f"setup.params.{key}", "tipo non supportato")

    # Copia normalizzata: l'input del chiamante non viene mutato.
    out = {
        "schema_version": SCHEMA_VERSION,
        "name": str(raw.get("name") or "")[:80],
        "symbol": str(raw.get("symbol") or "")[:24],
        "timeframe": str(raw.get("timeframe") or "")[:8],
        "combo": clean_combo,
        "params": clean_params,
    }
    if len(_json.dumps(out)) > CREATOR_MAX_SERIALIZED:
        raise ValidationError("setup", "documento troppo grande")
    return out
