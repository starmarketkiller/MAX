"""Canonical, read-only Library catalog sourced from Phase 6.6 artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

SCHEMA_VERSION = 1
RELATION_TYPES = frozenset({"TESTS", "SUPPORTS", "REFUTES", "LIMITS", "AUDITS", "DERIVED_FROM", "SUPERSEDES"})
FILES = {
    "evidence": "h006_evidence_v2.json",
    "decision": "h006_decision_card_v2.json",
    "posthoc": "post_hoc_observations_v1.json",
    "ledger": "research_evidence_ledger_v1.json",
    "relations": "research_relations_v1.json",
    "manifest": "artifact_manifest.json",
}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    return here.parent.parent if (here.parent.parent / "server" / "research_scripts").exists() else here.parent


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LibraryCatalog:
    def __init__(self, artifact_dir: Optional[Path] = None):
        root = _repo_root()
        packaged = root / "server" / "research_scripts" / "phase6_6"
        self.artifact_dir = artifact_dir or (packaged if packaged.exists() else root / "research_scripts" / "phase6_6")
        self._signature = None
        self._catalog = None

    def _load(self, key: str, warnings: list[dict]) -> Optional[dict]:
        path = self.artifact_dir / FILES[key]
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict) or not isinstance(value.get("payload"), dict):
                raise ValueError("root and payload must be objects")
            expected = value.get("canonical_sha256")
            valid = expected == _canonical_hash(value["payload"]) if expected else None
            if valid is False:
                warnings.append({"code": "CANONICAL_SHA_MISMATCH", "artifact": FILES[key]})
            value["_canonical_sha_valid"] = valid
            value["_file_sha256"] = _file_hash(path)
            return value
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            warnings.append({"code": "ARTIFACT_UNAVAILABLE", "artifact": FILES[key], "detail": str(exc)})
            return None

    def _sig(self):
        return tuple((name, (self.artifact_dir / name).stat().st_mtime_ns if (self.artifact_dir / name).exists() else None) for name in FILES.values())

    @staticmethod
    def _entity(entity_id, kind, title, status, grade, phase, artifact, wrapper, attributes=None, limitations=None, created=None):
        return {
            "id": entity_id, "type": kind, "title": title, "status": status,
            "evidence_grade": grade, "phase": phase, "created_at": created,
            "updated_at": wrapper.get("generated_at") if wrapper else None,
            "limitations": limitations or [], "attributes": attributes or {},
            "provenance": {
                "mode": "DIRECT" if kind not in ("Hypothesis", "Experiment", "Dataset", "DecisionCard") else "DERIVED_FROM_STRUCTURED_ARTIFACT",
                "source_artifact": f"server/research_scripts/phase6_6/{artifact}",
                "source_phase": phase, "schema_version": (attributes or {}).get("schema_version"),
                "canonical_sha256": wrapper.get("canonical_sha256") if wrapper else None,
                "canonical_sha_valid": wrapper.get("_canonical_sha_valid") if wrapper else None,
                "file_sha256": wrapper.get("_file_sha256") if wrapper else None,
                "commit": (attributes or {}).get("commit"),
            },
        }

    def build(self, force=False) -> dict:
        signature = self._sig()
        if not force and self._catalog is not None and signature == self._signature:
            return self._catalog
        warnings: list[dict] = []
        loaded = {key: self._load(key, warnings) for key in FILES}
        manifest_entries = loaded["manifest"]["payload"].get("entries", []) if loaded["manifest"] else []
        expected_hashes = {
            Path(entry.get("relative_path", "")).name: entry.get("sha256")
            for entry in manifest_entries if isinstance(entry, dict)
        } if isinstance(manifest_entries, list) else {}
        for key, wrapper in loaded.items():
            expected = expected_hashes.get(FILES[key])
            if wrapper and expected and wrapper.get("_file_sha256") != expected:
                warnings.append({"code": "MANIFEST_SHA_MISMATCH", "artifact": FILES[key]})
        entities: dict[str, dict] = {}

        def add(item):
            if not item or not item.get("id"):
                warnings.append({"code": "MALFORMED_ENTITY"})
            elif item["id"] in entities:
                warnings.append({"code": "DUPLICATE_ENTITY_ID", "entity_id": item["id"]})
            else:
                entities[item["id"]] = item

        evidence = loaded["evidence"]
        if evidence:
            payload = evidence["payload"]
            hid = payload.get("hypothesis_id")
            primary = payload.get("primary_evidence")
            audit = payload.get("retroactive_methodological_audit")
            if isinstance(primary, dict):
                identity = primary.get("identity") if isinstance(primary.get("identity"), dict) else {}
                classification = primary.get("evidence_classification") if isinstance(primary.get("evidence_classification"), dict) else {}
                provenance = primary.get("provenance") if isinstance(primary.get("provenance"), dict) else {}
                limitations = provenance.get("limitations") if isinstance(provenance.get("limitations"), list) else []
                attrs = {**primary, "schema_version": identity.get("schema_version"), "commit": provenance.get("code_commit"), "promoted_to_e3": False}
                add(self._entity(hid, "Hypothesis", "Liquidity sweep reclaim true holdout", classification.get("conclusion"), classification.get("evidence_grade"), "Phase6", FILES["evidence"], evidence, attrs, limitations, identity.get("created_at")))
                add(self._entity(identity.get("experiment_id"), "Experiment", "Phase 6 true holdout", "COMPLETED", classification.get("evidence_grade"), "Phase6", FILES["evidence"], evidence, {"hypothesis_id": hid, "dataset_id": identity.get("dataset_id"), "schema_version": identity.get("schema_version"), "commit": provenance.get("code_commit")}, limitations, identity.get("created_at")))
                add(self._entity(identity.get("dataset_id"), "Dataset", "Dukascopy holdout 2022H2–2023H1", "USED", None, "Phase6", FILES["evidence"], evidence, {"schema_version": identity.get("schema_version")}, [], identity.get("created_at")))
                add(self._entity(identity.get("evidence_id"), "Evidence", "H006 primary evidence", classification.get("conclusion"), classification.get("evidence_grade"), "Phase6", FILES["evidence"], evidence, attrs, limitations, identity.get("created_at")))
            if isinstance(audit, dict):
                identity = audit.get("identity") if isinstance(audit.get("identity"), dict) else {}
                classification = audit.get("evidence_classification") if isinstance(audit.get("evidence_classification"), dict) else {}
                provenance = audit.get("provenance") if isinstance(audit.get("provenance"), dict) else {}
                limitations = provenance.get("limitations") if isinstance(provenance.get("limitations"), list) else []
                attrs = {**audit, "schema_version": identity.get("schema_version"), "commit": provenance.get("code_commit")}
                add(self._entity(identity.get("experiment_id"), "Experiment", "Phase 6.5 dependence audit", "COMPLETED", None, "Phase6.5", FILES["evidence"], evidence, {"hypothesis_id": hid, "dataset_id": identity.get("dataset_id"), "schema_version": identity.get("schema_version"), "commit": provenance.get("code_commit")}, limitations, identity.get("created_at")))
                add(self._entity(identity.get("evidence_id"), "EvidenceAudit", "H006 retrospective methodological audit", classification.get("conclusion"), None, "Phase6.5", FILES["evidence"], evidence, attrs, limitations, identity.get("created_at")))

        ledger = loaded["ledger"]
        transitions = ledger["payload"].get("transitions", []) if ledger else []
        if not isinstance(transitions, list): transitions = []
        h004_rows = [row for row in transitions if isinstance(row, dict) and row.get("entity") == "H004_EVENT_RECLAIM"]
        if h004_rows:
            row = h004_rows[-1]
            add(self._entity("H004_EVENT_RECLAIM", "Hypothesis", "Event reclaim", row.get("to_status"), "E2", row.get("phase"), FILES["ledger"], ledger, {"schema_version": ledger["payload"].get("schema_version"), "commit": row.get("commit")}, ["Validation was retrospectively classified as contaminated."], h004_rows[0].get("timestamp")))

        decision = loaded["decision"]
        if decision:
            p = decision["payload"]
            hid = p.get("hypothesis_id")
            add(self._entity(f"DEC-{hid}-V2" if hid else None, "DecisionCard", "H006 evidence decision", p.get("decision"), p.get("current_grade"), "Phase6.6", FILES["decision"], decision, {**p, "schema_version": 2}, p.get("unresolved_questions") if isinstance(p.get("unresolved_questions"), list) else []))

        posthoc = loaded["posthoc"]
        observations = posthoc["payload"].get("observations", []) if posthoc else []
        if isinstance(observations, list):
            for obs in observations:
                if not isinstance(obs, dict):
                    warnings.append({"code": "MALFORMED_POST_HOC_OBSERVATION"}); continue
                add(self._entity(obs.get("observation_id"), "PostHocObservation", "SELL sweep/reclaim asymmetry", obs.get("status"), None, obs.get("source_phase"), FILES["posthoc"], posthoc, {**obs, "schema_version": posthoc["payload"].get("schema_version")}, obs.get("explicit_non_actions") if isinstance(obs.get("explicit_non_actions"), list) else []))

        relations: list[dict] = []
        relation_doc = loaded["relations"]
        raw_edges = relation_doc["payload"].get("edges", []) if relation_doc else []
        if isinstance(raw_edges, list):
            for index, edge in enumerate(raw_edges):
                if not isinstance(edge, dict) or edge.get("relation") not in RELATION_TYPES:
                    warnings.append({"code": "MALFORMED_RELATION", "index": index}); continue
                source, target = edge.get("from"), edge.get("to")
                if source not in entities or target not in entities:
                    warnings.append({"code": "BROKEN_RELATION", "source_id": source, "target_id": target}); continue
                relations.append({"id": f"REL-{index + 1:03d}", "source_id": source, "type": edge["relation"], "target_id": target, "note": edge.get("note"), "provenance": {"source_artifact": f"server/research_scripts/phase6_6/{FILES['relations']}", "canonical_sha256": relation_doc.get("canonical_sha256")}})

        for item in entities.values():
            item["relations_in"] = [r for r in relations if r["target_id"] == item["id"]]
            item["relations_out"] = [r for r in relations if r["source_id"] == item["id"]]
        self._signature, self._catalog = signature, {"schema_version": SCHEMA_VERSION, "entities": entities, "relations": relations, "transitions": transitions, "warnings": warnings}
        return self._catalog

    def list_entities(self, filters=None):
        catalog, filters = self.build(), (filters or {})
        items = list(catalog["entities"].values())
        relation_type = filters.get("relation_type")
        for field in ("type", "status", "evidence_grade", "phase"):
            if filters.get(field): items = [x for x in items if str(x.get(field, "")).lower() == str(filters[field]).lower()]
        if relation_type: items = [x for x in items if any(r["type"] == relation_type for r in x["relations_in"] + x["relations_out"])]
        q = str(filters.get("q") or "").lower().strip()
        if q: items = [x for x in items if q in " ".join(str(x.get(k) or "") for k in ("id", "title", "type", "status")).lower() or any(q in r["type"].lower() for r in x["relations_in"] + x["relations_out"])]
        items.sort(key=lambda x: (x["type"], x["id"]))
        metadata = [{key: value for key, value in item.items() if key not in ("attributes", "relations_in", "relations_out")} for item in items]
        return {"items": metadata, "count": len(metadata), "warnings": catalog["warnings"]}

    def detail(self, entity_id): return self.build()["entities"].get(entity_id)

    def list_relations(self, relation_type=None):
        catalog = self.build(); items = catalog["relations"]
        if relation_type: items = [r for r in items if r["type"] == relation_type]
        return {"items": items, "count": len(items), "warnings": catalog["warnings"]}

    def explain(self, entity_id):
        catalog = self.build(); root = catalog["entities"].get(entity_id)
        if not root: return None
        connected = {entity_id}; changed = True
        while changed:
            changed = False
            for edge in catalog["relations"]:
                if edge["source_id"] in connected or edge["target_id"] in connected:
                    before = len(connected); connected.update((edge["source_id"], edge["target_id"])); changed |= len(connected) != before
        order = {"H004_EVENT_RECLAIM": 0, "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT": 1, "EXP-P6-001-H006-TRUE-HOLDOUT": 2, "EVD-H006-PRIMARY-001": 3, "EXP-P6.5-001-H006-DEPENDENCE-AUDIT": 4, "EVD-H006-AUDIT-001": 5, "SELL_SWEEP_RECLAIM_ASYMMETRY": 6}
        nodes = sorted((catalog["entities"][i] for i in connected), key=lambda x: (order.get(x["id"], 99), x["id"]))
        edges = sorted((r for r in catalog["relations"] if r["source_id"] in connected and r["target_id"] in connected), key=lambda r: r["id"])
        relevant = [t for t in catalog["transitions"] if isinstance(t, dict) and t.get("entity") in connected]
        decisions = [x for x in catalog["entities"].values() if x["type"] == "DecisionCard" and x["attributes"].get("hypothesis_id") in connected]
        limitations = sorted({value for node in nodes for value in node.get("limitations", []) if value})
        return {"root_entity": root, "path_nodes": nodes, "typed_edges": edges, "chronological_transitions": sorted(relevant, key=lambda x: (x.get("seq", 0), x.get("timestamp") or "")), "current_decision": decisions[0] if decisions else None, "limitations": limitations, "provenance": {"mode": "EXPLICIT_RELATIONS_AND_LEDGER", "inferred_relations": False}, "warnings": catalog["warnings"]}


CATALOG = LibraryCatalog()
