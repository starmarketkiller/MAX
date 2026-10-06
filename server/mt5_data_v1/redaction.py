"""MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1 - redazione dei segreti (sez.18/9).

Policy: RAW (il file originale mai modificato) puo' contenere tutto quello
che il broker/EA ci ha scritto - non lo tocchiamo mai. NORMALIZED/DERIVED
(quello che finisce in accounts/<account_id>/..., quindi potenzialmente
condiviso/commitato) deve avere il login grezzo rimosso da ogni campo
testuale libero (es. `comment` su deal/order), anche se e' comparso li' per
caso (alcuni broker lo scrivono nel comment di deposito/prelievo).

Il login grezzo viene letto SOLO dalla mappa privata locale
(identity.py/_private/account_identity_map.json, gitignored) - mai persistito
altrove, nemmeno nei log di questo modulo.
"""
from __future__ import annotations

from typing import Any

from . import identity

REDACTED_PLACEHOLDER = "[REDACTED_ACCOUNT_LOGIN]"


def _redact_value(value: Any, login: str) -> Any:
    if isinstance(value, str) and login and login in value:
        return value.replace(login, REDACTED_PLACEHOLDER)
    if isinstance(value, dict):
        return {k: _redact_value(v, login) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v, login) for v in value]
    return value


def redact_bundle(bundle: dict, account_id: str) -> dict:
    """Ritorna una COPIA del bundle con ogni occorrenza letterale del login
    grezzo (se noto per questo account_id nella mappa privata) sostituita.
    Se l'account_id non ha un login registrato (es. TESTER sintetico), il
    bundle torna invariato - non c'e' nulla da redarre."""
    mapping = identity._load_private_map()
    entry = mapping.get(account_id)
    login = str(entry.get("login")) if entry and entry.get("login") else ""
    if not login:
        return bundle
    return _redact_value(bundle, login)
