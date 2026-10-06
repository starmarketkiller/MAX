"""MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1 - idempotenza dell'import (sez.15).

classify_import() decide IMPORT_NEW / APPEND / RESCAN / SKIPPED_DUPLICATE
confrontando i byte del nuovo file con la copia RAW gia' salvata (non solo
l'hash finale - un file piu' lungo che inizia esattamente come il
precedente e' un APPEND reale, non un file diverso per caso).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import account_package, canonical

IMPORT_NEW = "IMPORT_NEW"
APPEND = "APPEND"
RESCAN = "RESCAN"
SKIPPED_DUPLICATE = "SKIPPED_DUPLICATE"


def classify_import(new_bytes: bytes, previous_bytes: Optional[bytes]) -> str:
    if previous_bytes is None:
        return IMPORT_NEW
    if new_bytes == previous_bytes:
        return SKIPPED_DUPLICATE
    if len(new_bytes) > len(previous_bytes) and new_bytes[: len(previous_bytes)] == previous_bytes:
        return APPEND
    return RESCAN


def import_raw_file(root: str | Path, account_id: str, source_path: str | Path) -> dict:
    """Copia (o aggiorna) la copia RAW per questo account e ritorna una entry
    pronta per account_manifest.import_log (sez.15). Non normalizza - solo
    decide la modalita' di import e materializza la copia raw."""
    account_package.ensure_layout(root, account_id)
    dest = account_package.raw_dir(root, account_id) / Path(source_path).name
    new_bytes = Path(source_path).read_bytes()
    previous_bytes = dest.read_bytes() if dest.exists() else None

    mode = classify_import(new_bytes, previous_bytes)
    if mode != SKIPPED_DUPLICATE:
        dest.write_bytes(new_bytes)

    return {
        "source_path": str(source_path).replace("\\", "/"),
        "source_sha256": canonical.file_sha256(source_path),
        "import_mode": mode,
        "imported_at": canonical.utc_now_iso(),
        "rows_ingested": None,  # popolato dal chiamante dopo la normalizzazione, se mode != SKIPPED_DUPLICATE
    }
