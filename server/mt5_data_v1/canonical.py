"""MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1 - utility di hashing/provenance.

Stesso pattern di server/research_scripts/phase6_6/canonical_utils.py
(serializzazione deterministica + hash separato dal metadata volatile) -
duplicato qui invece di importato perche' quel file vive in una cartella
di ricerca specifica di una fase (phase6_6), non pensata come libreria
condivisa fra moduli di server/.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def canonical_json_bytes(obj: Any) -> bytes:
    """Chiavi ordinate, separatori fissi - stesso output per lo stesso contenuto
    indipendentemente dall'ordine di inserimento del dict Python."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")


def canonical_sha256(obj: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def wrap_with_provenance(payload: dict, generation_script: str) -> dict:
    """generated_at e' volatile e tenuto fuori dal payload hashato, cosi' due
    run sugli stessi input producono lo stesso canonical_sha256."""
    return {
        "generated_at": utc_now_iso(),
        "generation_script": generation_script,
        "canonical_sha256": canonical_sha256(payload),
        "payload": payload,
    }


def load_json(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str | Path, obj: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=True, default=str)
