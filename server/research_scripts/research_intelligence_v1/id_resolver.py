"""Deterministic hypothesis_id -> HYPOTHESIS record_id resolution.

ResearchMemory stays the only canonical source of hypotheses. This module never
creates records and never normalizes IDs (no uppercasing). Order:
1. exact lookup of "HYP-" + hypothesis_id (the historical rule). The record is
   returned only if it is a HYPOTHESIS whose body.hypothesis_id equals the
   requested id. If a record with that exact id exists but fails this check the
   result is None: the alias path is NOT tried (fail closed, an existing exact
   id is never shadowed by a manifest). The alias path applies only when no
   record with the exact id exists;
2. an alias declared in a versioned manifest under manifests/, accepted only if
   it is unambiguous across all manifests, its target exists and is a
   HYPOTHESIS, and (by default) the record hash and provenance declared in the
   manifest match the record in memory;
3. otherwise None (fail closed).
"""
from __future__ import annotations

import glob
import json
import os

MANIFEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifests")
MANIFEST_SCHEMA = "research-id-alias-manifest-v1"


def load_manifests(manifest_dir=MANIFEST_DIR):
    out = []
    for path in sorted(glob.glob(os.path.join(manifest_dir, "*.json"))):
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if data.get("manifest_schema") != MANIFEST_SCHEMA:
            continue
        out.append((os.path.basename(path), data))
    return out


BINDING_FIELDS = ("record_id", "record_hash", "signature_sha256", "draft_sha256")
MANIFEST_BINDING_FIELDS = ("manifest_id", "experiment_id")


def _binding(entry, manifest):
    """Every field that constrains what an alias means. Two declarations of the same
    alias are equivalent only if all of them match."""
    return (tuple(entry.get(k) for k in BINDING_FIELDS)
            + tuple(manifest.get(k) for k in MANIFEST_BINDING_FIELDS)
            + ((manifest.get("package") or {}).get("sha256"),))


def alias_table(manifests):
    """alias -> (entry, manifest), plus the sorted list of conflicting aliases.

    Declarations of one alias that differ in any binding field are a conflict and the
    alias is dropped (fail closed). The result does not depend on the order in which
    manifests are given: they are sorted by file name and canonical content first."""
    ordered = sorted(manifests, key=lambda nm: (nm[0], json.dumps(nm[1], sort_keys=True)))
    groups = {}
    for _, data in ordered:
        for entry in data.get("aliases", []):
            alias = entry.get("alias")
            if not alias or not entry.get("record_id"):
                continue
            groups.setdefault(alias, []).append((entry, data))
    table, conflicts = {}, []
    for alias in sorted(groups):
        decls = groups[alias]
        if len({_binding(e, m) for e, m in decls}) > 1:
            conflicts.append(alias)
        else:
            table[alias] = decls[0]
    return table, conflicts


def _provenance_ok(record, entry, manifest):
    if entry.get("record_hash") and entry["record_hash"] != record["record_hash"]:
        return False
    body = record.get("body", {})
    if entry.get("signature_sha256") and entry["signature_sha256"] != body.get("signature_sha256"):
        return False
    if body.get("hypothesis_id") != entry["alias"]:
        return False
    shas = {p.get("sha256") for p in record.get("provenance", []) if p.get("sha256")}
    package = (manifest.get("package") or {}).get("sha256")
    if package and package not in shas:
        return False
    if entry.get("draft_sha256") and entry["draft_sha256"] not in shas:
        return False
    return True


def resolve(memory, hypothesis_id, *, manifests=None, validate_provenance=True):
    """Record id of the hypothesis, or None. Never guesses."""
    if not isinstance(hypothesis_id, str) or not hypothesis_id:
        return None
    exact = f"HYP-{hypothesis_id}"
    record = memory.get(exact)
    if record is not None:
        ok = (record.get("record_type") == "HYPOTHESIS"
              and record.get("body", {}).get("hypothesis_id") == hypothesis_id)
        return exact if ok else None
    table, _ = alias_table(load_manifests(MANIFEST_DIR) if manifests is None else manifests)
    hit = table.get(hypothesis_id)
    if not hit:
        return None
    entry, manifest = hit
    record = memory.get(entry["record_id"])
    if record is None or record.get("record_type") != "HYPOTHESIS":
        return None
    if validate_provenance and not _provenance_ok(record, entry, manifest):
        return None
    return entry["record_id"]
