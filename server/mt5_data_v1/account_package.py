"""MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1 - struttura di directory per account
(sez.6). Separazione RAW/NORMALIZED/DERIVED rigorosa (sez.16): raw/ non viene
MAI scritto da un passo successivo alla copia iniziale.

accounts/<account_id>/
  raw/            copie byte-identiche dei file originali (mai modificate)
  normalized/     deal/order/trade_episode/account_snapshot canonici
  derived/        analytics + report
  runs/<run_id>/  run manifest + artifact per singolo run (Tester o sessione)
  account_manifest.json
"""
from __future__ import annotations

from pathlib import Path

from .identity import is_valid_account_id


def _check(account_id: str) -> None:
    if not is_valid_account_id(account_id):
        raise ValueError(f"account_id non valido: {account_id!r}")


def account_dir(root: str | Path, account_id: str) -> Path:
    _check(account_id)
    return Path(root) / "accounts" / account_id


def raw_dir(root: str | Path, account_id: str) -> Path:
    return account_dir(root, account_id) / "raw"


def normalized_dir(root: str | Path, account_id: str) -> Path:
    return account_dir(root, account_id) / "normalized"


def derived_dir(root: str | Path, account_id: str) -> Path:
    return account_dir(root, account_id) / "derived"


def run_dir(root: str | Path, account_id: str, run_id: str) -> Path:
    return account_dir(root, account_id) / "runs" / run_id


def manifest_path(root: str | Path, account_id: str) -> Path:
    return account_dir(root, account_id) / "account_manifest.json"


def ensure_layout(root: str | Path, account_id: str) -> None:
    for d in (raw_dir(root, account_id), normalized_dir(root, account_id),
             derived_dir(root, account_id), account_dir(root, account_id) / "runs"):
        d.mkdir(parents=True, exist_ok=True)
