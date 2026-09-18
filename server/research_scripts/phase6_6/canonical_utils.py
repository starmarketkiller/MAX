#!/usr/bin/env python3
"""Phase 6.6 - utility condivise: hashing canonico e determinismo.

Principio (sec.10 della richiesta): il metadata volatile (timestamp di
generazione) e' tenuto SEPARATO dal payload canonico, cosi' due run
sugli stessi input producono lo stesso `canonical_sha256` anche se
`generated_at` cambia. Ogni artifact JSON prodotto in questa fase ha
la forma:

{
  "generated_at": "<timestamp - volatile, non fa parte del payload canonico>",
  "canonical_sha256": "<hash SOLO del payload sottostante>",
  "payload": { ... contenuto vero e proprio ... }
}
"""
import hashlib
import json
import os
from datetime import datetime, timezone

ROOT = r"C:\Users\User\ClaudeWork\MAX"


def canonical_json_bytes(obj) -> bytes:
    """Serializzazione deterministica: chiavi ordinate, separatori fissi,
    nessuna dipendenza dall'ordine di inserimento del dict Python."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")


def canonical_sha256(obj) -> str:
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def wrap_with_provenance(payload: dict, script: str) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generation_script": script,
        "canonical_sha256": canonical_sha256(payload),
        "payload": payload,
    }


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel_path(abs_path: str) -> str:
    """Path relativo alla root del repo, forward-slash, MAI un path
    locale assoluto nell'output (sec.9)."""
    r = os.path.relpath(abs_path, ROOT)
    return r.replace("\\", "/")


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, obj: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=True, default=str)
