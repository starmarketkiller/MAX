"""MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1 - Account Registry
(contracts/mt5-account-registry-v1.schema.json). Store JSON-file-backed,
stesso stile leggero gia' usato altrove nel repo per registri non ad alto
volume (es. server/funding_v1/*_v1.json) - niente DB per questo, coerente
con la sez.27 ('non costruire il control plane completo').
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import canonical
from .identity import is_valid_account_id


def new_registry() -> dict:
    return {"schema_version": 1, "generated_at": canonical.utc_now_iso(), "accounts": []}


def load_registry(path: str | Path) -> dict:
    if not Path(path).exists():
        return new_registry()
    return canonical.load_json(path)


def save_registry(path: str | Path, registry: dict) -> None:
    registry["generated_at"] = canonical.utc_now_iso()
    canonical.save_json(path, registry)


def upsert_account(registry: dict, account_id: str, *, environment: str,
                   identity_source: str, display_label: Optional[str] = None,
                   broker: Optional[str] = None, server: Optional[str] = None,
                   base_currency: Optional[str] = None, leverage: Optional[int] = None,
                   source_terminal_role: str = "UNKNOWN") -> dict:
    if not is_valid_account_id(account_id):
        raise ValueError(f"account_id non valido: {account_id!r}")

    now = canonical.utc_now_iso()
    existing = next((a for a in registry["accounts"] if a["account_id"] == account_id), None)
    if existing is None:
        entry = {
            "account_id": account_id, "display_label": display_label, "environment": environment,
            "broker": broker, "server": server, "base_currency": base_currency, "leverage": leverage,
            "source_terminal_role": source_terminal_role, "identity_source": identity_source,
            "first_seen_at": now, "last_seen_at": now, "notes": [],
        }
        registry["accounts"].append(entry)
        return registry

    existing["last_seen_at"] = now
    for field, value in (("display_label", display_label), ("broker", broker), ("server", server),
                         ("base_currency", base_currency), ("leverage", leverage)):
        if value is not None:
            existing[field] = value
    return registry


def get_account(registry: dict, account_id: str) -> Optional[dict]:
    return next((a for a in registry["accounts"] if a["account_id"] == account_id), None)
