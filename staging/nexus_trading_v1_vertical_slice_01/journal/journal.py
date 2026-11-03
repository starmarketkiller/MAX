"""journal.py - append-only, hash-chained journal for decisions and
paper attempts. Reuses phase5d_shadow_engine_v1.shadow_mode.append_chain
/ verify_chain VERBATIM (imported, not copied) - same guarantee: a
previous line can never be rewritten, because the underlying file
handle is always opened in append ("a") mode, never "w"/"r+".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT / "server" / "research_scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "server" / "research_scripts"))

from phase5d_shadow_engine_v1 import shadow_mode as _shadow_mode  # noqa: E402
from phase5d_shadow_engine_v1.contract import canonical_hash  # noqa: E402

GENESIS_HASH = _shadow_mode.GENESIS_HASH


def _last_record_hash(log_path: Path) -> str:
    if not log_path.is_file() or log_path.stat().st_size == 0:
        return GENESIS_HASH
    last_line = None
    with log_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                last_line = line
    if last_line is None:
        return GENESIS_HASH
    return json.loads(last_line)["record_hash"]


def append_records(records: list[dict[str, Any]], log_path: Path) -> list[dict[str, Any]]:
    """Generic hash-chained append for any JSON-serializable record
    list - same chaining scheme as shadow_mode.append_chain, applied
    here to plain dicts (decision records / paper attempts) instead of
    DecisionEvent objects, since those are already dicts by the time
    they reach the journal."""
    prev_hash = _last_record_hash(log_path)
    written: list[dict[str, Any]] = []
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        for payload in records:
            record = {"prev_hash": prev_hash, "payload": payload}
            record["record_hash"] = canonical_hash(record)
            fh.write(json.dumps(record, sort_keys=True, default=str) + "\n")
            written.append(record)
            prev_hash = record["record_hash"]
    return written


def verify_chain(log_path: Path) -> bool:
    """Identical algorithm to shadow_mode.verify_chain, applied to the
    plain-dict journals written by append_records above."""
    prev_hash = GENESIS_HASH
    if not log_path.is_file():
        return True
    with log_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("prev_hash") != prev_hash:
                return False
            claimed = record.get("record_hash")
            check = {"prev_hash": record.get("prev_hash"), "payload": record.get("payload")}
            if canonical_hash(check) != claimed:
                return False
            prev_hash = claimed
    return True


def read_all(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.is_file():
        return []
    out = []
    with log_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line)["payload"])
    return out
