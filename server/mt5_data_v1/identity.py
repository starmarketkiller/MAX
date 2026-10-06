"""MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1 - identita' account senza login in chiaro.

Principio (sez.2/9 della richiesta utente): l'Account Registry non contiene MAI
il numero di login/account del broker in chiaro, solo un alias stabile e
deterministico (`account_id`). La mappa alias -> login grezzo, quando serve
per risolvere un nuovo import, vive in un file locale separato e gitignored
(stesso pattern di LocalBridge/*.config.json) - non viene mai letta da
canonical.py/manifests.py/reports.py, solo da questo modulo.

Nota di reconciliation con server/app.py: la tabella `trades` ha un
`account_id INTEGER` grezzo (migrazione 010_trade_account_identity,
AUD0-DB-003/NXS-DB-004) - un contesto diverso (ledger live via LocalBridge,
dove il numero serve a disambiguare ticket collidenti fra conti sullo stesso
backend). Questo modulo non tocca quella tabella e non ne riusa il valore:
il nuovo `account_id` alias qui e' indipendente, e la coesistenza dei due
significati di "account_id" (uno grezzo in DB, uno alias qui) va letta nel
report finale, non nascosta.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

MODULE_DIR = Path(__file__).resolve().parent
PRIVATE_MAP_PATH = MODULE_DIR / "_private" / "account_identity_map.json"

ACCOUNT_ID_PREFIX = "acct_"


def derive_account_id(login: str, broker: Optional[str], server: Optional[str]) -> str:
    """Alias deterministico: stesso (login, broker, server) -> stesso alias,
    sempre. Non reversibile dal solo output (sha256 troncato)."""
    key = f"{login or ''}|{broker or ''}|{server or ''}".lower()
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"{ACCOUNT_ID_PREFIX}{digest}"


def is_valid_account_id(value: str) -> bool:
    if not value.startswith(ACCOUNT_ID_PREFIX):
        return False
    digest = value[len(ACCOUNT_ID_PREFIX):]
    return len(digest) == 16 and all(c in "0123456789abcdef" for c in digest)


def _load_private_map() -> dict:
    if not PRIVATE_MAP_PATH.exists():
        return {}
    with open(PRIVATE_MAP_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_private_map(data: dict) -> None:
    PRIVATE_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PRIVATE_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def register_account_identity(login: str, broker: Optional[str], server: Optional[str]) -> str:
    """Calcola l'account_id e registra il mapping privato login->alias (solo
    locale, mai nei dati canonici/derivati). Idempotente: richiamarlo con lo
    stesso login produce lo stesso account_id e aggiorna solo il mapping."""
    account_id = derive_account_id(login, broker, server)
    mapping = _load_private_map()
    mapping[account_id] = {"login": login, "broker": broker, "server": server}
    _save_private_map(mapping)
    return account_id
