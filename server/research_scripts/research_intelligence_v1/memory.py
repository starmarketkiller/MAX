"""Research Memory: append-only, hash-chained, schema-validated.

One JSONL file, one record per line (same pattern as orchestrator_v1/core/
ledger.py). There is no update and no delete: a correction is a new record
with a SUPERSEDES relation, and every record carries the hash of the previous
one, so a rewritten line breaks `verify()`.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.abspath(os.path.join(HERE, "..", ".."))
ROOT = os.path.dirname(SERVER)
SCHEMA_PATH = os.path.join(ROOT, "contracts", "research-memory-v1.schema.json")
DEFAULT_PATH = os.path.join(HERE, "memory", "research_memory_v1.jsonl")
GENESIS = "0" * 64

sys.path.insert(0, os.path.join(SERVER, "orchestrator_v1"))
from nxs_schema_validator import validate  # noqa: E402  (reused stdlib validator)

with open(SCHEMA_PATH, encoding="utf-8") as _handle:
    SCHEMA = json.load(_handle)


class MemoryViolation(Exception):
    pass


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_hash(record):
    body = {k: v for k, v in record.items() if k != "record_hash"}
    return sha256_text(canonical(body))


def schema_errors(record):
    errors = validate(record, SCHEMA)
    rtype = record.get("record_type")
    if rtype in SCHEMA["definitions"]:
        errors += validate(record.get("body"), SCHEMA["definitions"][rtype], SCHEMA, "$.body")
    return errors


class ResearchMemory:
    def __init__(self, path=DEFAULT_PATH):
        self.path = path
        self.records = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                self.records = [json.loads(line) for line in handle if line.strip()]
        self._by_id = {r["record_id"]: r for r in self.records}

    # ---- read ------------------------------------------------------------
    def get(self, record_id):
        return self._by_id.get(record_id)

    def of_type(self, record_type):
        return [r for r in self.records if r["record_type"] == record_type]

    def related(self, record_id):
        """Records pointing at `record_id` and records it points at."""
        out = []
        for r in self.records:
            if r["record_id"] == record_id:
                out += [(rel["type"], rel["target"]) for rel in r["relations"]]
            out += [(rel["type"], r["record_id"]) for rel in r["relations"] if rel["target"] == record_id]
        return out

    def current(self, record_id):
        """Follow SUPERSEDES forward. The superseded record stays readable."""
        current = record_id
        while True:
            newer = [r["record_id"] for r in self.records
                     if any(rel["type"] == "SUPERSEDES" and rel["target"] == current for rel in r["relations"])]
            if not newer:
                return self._by_id.get(current)
            current = newer[-1]

    def hypothesis_signatures(self):
        return {r["body"]["signature_sha256"]: r["record_id"] for r in self.of_type("HYPOTHESIS")}

    # ---- write -----------------------------------------------------------
    def append(self, record_type, record_id, body, *, author, origin, project, family,
               provenance=(), relations=(), created_at=None):
        if record_id in self._by_id:
            raise MemoryViolation(f"{record_id} already exists: records are immutable, append a "
                                  "new record with a SUPERSEDES relation instead")
        for rel in relations:
            if rel["target"] not in self._by_id:
                raise MemoryViolation(f"relation to unknown record {rel['target']}")
        record = {
            "schema_version": "research-memory-v1", "record_id": record_id, "record_type": record_type,
            "created_at": created_at or datetime.now(timezone.utc).isoformat(),
            "author": author, "origin": origin, "project": project, "family": family,
            "provenance": list(provenance), "relations": list(relations), "body": body,
            "prev_hash": self.records[-1]["record_hash"] if self.records else GENESIS,
        }
        record["record_hash"] = record_hash(record)
        errors = schema_errors(record)
        if errors:
            raise MemoryViolation("schema: " + "; ".join(errors[:5]))
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(canonical(record) + "\n")
        self.records.append(record)
        self._by_id[record_id] = record
        return record

    # ---- audit -----------------------------------------------------------
    def verify(self):
        """Every line valid, every hash correct, every link to the previous line intact."""
        problems = []
        prev = GENESIS
        for n, r in enumerate(self.records, start=1):
            if r["prev_hash"] != prev:
                problems.append(f"line {n} {r['record_id']}: chain broken")
            if record_hash(r) != r["record_hash"]:
                problems.append(f"line {n} {r['record_id']}: content changed after writing")
            problems += [f"line {n}: {e}" for e in schema_errors(r)]
            prev = r["record_hash"]
        return problems

    def head_hash(self):
        return self.records[-1]["record_hash"] if self.records else GENESIS
