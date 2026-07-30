"""PR7 — Validatore Settings per il backend (contro contracts/settings.schema.json).

Impone i requisiti del pack:
1. rifiuta chiavi ignote (salvo allow_unknown_keys);
2. rifiuta NaN, infinito e stringhe non numeriche;
3. int vs decimale;
4. range + invarianti cross-field;
5. errori strutturati;
6. espone la schema_version applicata;
7. non converte MAI il moltiplicatore manuale 0 in 1 (nessuna coercizione magica).
"""
from __future__ import annotations
import json
import math
import os
from functools import lru_cache

def _resolve_contracts_dir() -> str:
    # Stesso disallineamento di layout descritto in strategy_registry.py:
    # locale risale due livelli, l'immagine Docker (server/ appiattita in
    # /app) uno solo. Si usa quello che esiste davvero sul disco.
    here = os.path.dirname(os.path.abspath(__file__))
    sibling = os.path.join(here, "contracts")
    if os.path.isdir(sibling):
        return sibling
    return os.path.join(os.path.dirname(here), "contracts")


_CONTRACTS = _resolve_contracts_dir()


class SettingsValidationError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__(f"{len(errors)} errori di validazione settings")


@lru_cache(maxsize=1)
def schema() -> dict:
    with open(os.path.join(_CONTRACTS, "settings.schema.json"), encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _by_key() -> dict:
    return {s["key"]: s for s in schema()["settings"]}


@lru_cache(maxsize=1)
def default_settings() -> dict:
    with open(os.path.join(_CONTRACTS, "default-settings.json"), encoding="utf-8") as f:
        return json.load(f)["settings"]


def schema_version() -> int:
    return schema()["schema_version"]


def _is_bad_number(v) -> bool:
    return isinstance(v, float) and (math.isnan(v) or math.isinf(v))


def validate(blob: dict, allow_unknown: bool = None) -> dict:
    """Valida un blob di settings. Ritorna il blob normalizzato (tipi corretti,
    nessuna coercizione di valore) o solleva SettingsValidationError con la lista
    strutturata degli errori.

    `allow_unknown`: se None usa lo schema. Gli endpoint operativi passano True
    perche' il blob 'settings' porta anche stato UI (es. 'strategies'): le chiavi
    canoniche restano validate in modo stretto, le extra passano invariate."""
    if not isinstance(blob, dict):
        raise SettingsValidationError([{"key": None, "error": "payload non è un oggetto"}])

    meta = _by_key()
    if allow_unknown is None:
        allow_unknown = schema().get("allow_unknown_keys", False)
    errors = []
    out = {}

    for key, val in blob.items():
        spec = meta.get(key)
        if spec is None:
            if not allow_unknown:
                errors.append({"key": key, "error": "chiave sconosciuta"})
            else:
                out[key] = val
            continue
        t = spec["type"]
        # NaN / infinito / bool spacciato per numero
        if _is_bad_number(val):
            errors.append({"key": key, "error": "NaN/infinito non ammesso"})
            continue
        if t == "boolean":
            if not isinstance(val, bool):
                errors.append({"key": key, "error": "atteso boolean", "got": repr(val)})
                continue
            out[key] = val
            continue
        # numerico: rifiuta stringhe non numeriche e bool
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            errors.append({"key": key, "error": f"atteso {t} numerico", "got": repr(val)})
            continue
        if t == "integer" and not float(val).is_integer():
            errors.append({"key": key, "error": "atteso intero", "got": val})
            continue
        lo, hi = spec.get("minimum"), spec.get("maximum")
        if lo is not None and val < lo:
            errors.append({"key": key, "error": f"< minimo {lo}", "got": val})
            continue
        if hi is not None and val > hi:
            errors.append({"key": key, "error": f"> massimo {hi}", "got": val})
            continue
        out[key] = int(val) if t == "integer" else float(val)

    # invarianti cross-field (regola 4)
    _cross_field(out, errors)

    if errors:
        raise SettingsValidationError(errors)
    return out


def _cross_field(s: dict, errors: list):
    # daily DD non negativo e bounded — gia' coperto dai range, ricontrollo esplicito
    for k in ("MaxDailyDDPct", "RiskPercent", "MaxLossPosPct"):
        if k in s and s[k] < 0:
            errors.append({"key": k, "error": "deve essere >= 0"})
    # esempio pack: MarketCloseGMT valido come ora
    if "MarketCloseGMT" in s and not (0 <= s["MarketCloseGMT"] <= 23):
        errors.append({"key": "MarketCloseGMT", "error": "ora GMT 0..23"})


def merged_with_defaults(blob: dict) -> dict:
    """Default canonici + override validati (per /api/ea/settings)."""
    return {**default_settings(), **blob}
