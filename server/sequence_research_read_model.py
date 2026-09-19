"""Fault-isolated, read-only projection of Phase 7.2 sequence research."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Optional

FILES = {
    "mechanisms": "market_mechanism_registry_v1.json",
    "sequences": "market_sequence_registry_v1.json",
    "branches": "conditional_branch_registry_v1.json",
    "contradictions": "contradiction_registry_v1.json",
    "priorities": "research_priority_queue_v2.json",
    "clusters": "evidence_cluster_registry_v1.json",
    "sources": "source_registry_v1.json",
    "diversity": "source_diversity_matrix_v1.json",
    "failure_memory": "failure_memory_crosscheck_v1.json",
    "leakage": "sequence_semantic_leakage_guard_v1.json",
    "readiness": "phase7_3_readiness_gate_v1.json",
    "claims": "external_hypothesis_corpus_v1.json",
}


def _default_dir() -> Path:
    here = Path(__file__).resolve().parent
    local = here.parent / "server" / "research_scripts" / "phase7" / "phase7_2"
    return local if local.exists() else here / "research_scripts" / "phase7" / "phase7_2"


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class SequenceResearchCatalog:
    def __init__(self, artifact_dir: Optional[Path] = None):
        self.artifact_dir = Path(artifact_dir) if artifact_dir else _default_dir()
        self._signature = None
        self._value = None

    def _signature_now(self):
        return tuple((name, (self.artifact_dir / name).stat().st_mtime_ns if (self.artifact_dir / name).exists() else None) for name in FILES.values())

    def _read(self, key: str, warnings: list[dict]) -> Optional[dict]:
        path = self.artifact_dir / FILES[key]
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("artifact root must be an object")
            if value.get("canonical_sha256") and isinstance(value.get("payload"), dict):
                if value["canonical_sha256"] != _canonical_hash(value["payload"]):
                    warnings.append({"code": "CANONICAL_SHA_MISMATCH", "artifact": FILES[key]})
            return value
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            warnings.append({"code": "ARTIFACT_UNAVAILABLE", "artifact": FILES[key], "detail": str(exc)})
            return None

    @staticmethod
    def _array(document, key, wrapped=False):
        root = document.get("payload") if wrapped and isinstance(document, dict) else document
        value = root.get(key) if isinstance(root, dict) else None
        return value if isinstance(value, list) else []

    def build(self, force=False):
        signature = self._signature_now()
        if not force and self._value is not None and signature == self._signature:
            return self._value
        warnings: list[dict] = []
        docs = {key: self._read(key, warnings) for key in FILES}
        mechanisms = self._array(docs["mechanisms"], "mechanisms", True)
        sequences = self._array(docs["sequences"], "sequences")
        branches = self._array(docs["branches"], "branches")
        scores = self._array(docs["priorities"], "all_scores", True)
        clusters = self._array(docs["clusters"], "merged_clusters")
        sources = self._array(docs["sources"], "sources", True)
        diversity = self._array(docs["diversity"], "rows", True)
        failure_checks = self._array(docs["failure_memory"], "mechanism_checks", True)
        leakage = self._array(docs["leakage"], "results", True)
        claims = self._array(docs["claims"], "claims", True)

        def index(items, field, label):
            result = {}
            for row in items:
                if not isinstance(row, dict) or not row.get(field):
                    warnings.append({"code": "MALFORMED_RECORD", "artifact": label}); continue
                if row[field] in result:
                    warnings.append({"code": "DUPLICATE_ID", "artifact": label, "id": row[field]}); continue
                result[row[field]] = row
            return result

        mechanism_by_id = index(mechanisms, "mechanism_id", FILES["mechanisms"])
        branch_by_id = index(branches, "branch_group_id", FILES["branches"])
        score_by_sequence = index(scores, "sequence_id", FILES["priorities"])
        source_by_id = index(sources, "source_id", FILES["sources"])
        claim_by_id = index(claims, "claim_id", FILES["claims"])
        leakage_by_sequence = index(leakage, "sequence_id", FILES["leakage"])
        failure_by_mechanism = index(failure_checks, "mechanism_id", FILES["failure_memory"])
        diversity_by_mechanism = index(diversity, "mechanism_id", FILES["diversity"])

        cluster_by_sequence: dict[str, list[dict]] = {}
        for cluster in clusters:
            if not isinstance(cluster, dict): continue
            for sequence_id in cluster.get("affected_sequences", []) if isinstance(cluster.get("affected_sequences"), list) else []:
                cluster_by_sequence.setdefault(sequence_id, []).append(cluster)

        joined = {}
        for sequence in sequences:
            if not isinstance(sequence, dict) or not sequence.get("sequence_id"):
                warnings.append({"code": "MALFORMED_RECORD", "artifact": FILES["sequences"]}); continue
            sequence_id = sequence["sequence_id"]
            if sequence_id in joined:
                warnings.append({"code": "DUPLICATE_ID", "artifact": FILES["sequences"], "id": sequence_id}); continue
            mechanism = mechanism_by_id.get(sequence.get("mechanism_id"))
            if not mechanism:
                warnings.append({"code": "BROKEN_MECHANISM", "sequence_id": sequence_id, "mechanism_id": sequence.get("mechanism_id")})
            source_claims = [claim_by_id[cid] for cid in sequence.get("source_claim_ids", []) if cid in claim_by_id]
            missing_claims = [cid for cid in sequence.get("source_claim_ids", []) if cid not in claim_by_id]
            if missing_claims:
                warnings.append({"code": "BROKEN_SOURCE_CLAIM", "sequence_id": sequence_id, "claim_ids": missing_claims})
            source_ids = sorted({claim.get("source_id") for claim in source_claims if claim.get("source_id")})
            source_records = [source_by_id[sid] for sid in source_ids if sid in source_by_id]
            quality = Counter(str(claim.get("evidence_quality")) for claim in source_claims if claim.get("evidence_quality"))
            score = score_by_sequence.get(sequence_id)
            leak = leakage_by_sequence.get(sequence_id)
            branch = branch_by_id.get(sequence.get("branch_group_id"))
            sequence_clusters = cluster_by_sequence.get(sequence_id, [])
            joined[sequence_id] = {
                **sequence,
                "description": mechanism.get("definition") if mechanism else None,
                "mechanism": mechanism,
                "priority": score,
                "semantic_leakage": leak,
                "branch": branch,
                "source_claims": source_claims,
                "sources": source_records,
                "raw_claim_count": len(source_claims),
                "source_count": len(source_ids),
                "source_categories": sorted({record.get("source_type") for record in source_records if record.get("source_type")}),
                "evidence_quality_distribution": dict(sorted(quality.items())),
                "evidence_clusters": sequence_clusters,
                "evidence_cluster_count": len(sequence_clusters),
                "failure_memory": failure_by_mechanism.get(sequence.get("mechanism_id")),
                "source_diversity": diversity_by_mechanism.get(sequence.get("mechanism_id")),
                "provenance": {
                    "mode": "RESEARCH", "source_phase": "Phase7.2/7.2B",
                    "sequence_artifact": FILES["sequences"], "priority_artifact": FILES["priorities"],
                    "leakage_artifact": FILES["leakage"], "outcome_tested": False,
                },
            }

        contradiction_payload = docs["contradictions"] or {}
        readiness_payload = (docs["readiness"] or {}).get("payload")
        self._signature = signature
        self._value = {
            "sequences": joined, "mechanisms": mechanism_by_id, "branches": branch_by_id,
            "warnings": warnings, "readiness": readiness_payload if isinstance(readiness_payload, dict) else None,
            "contradictions": contradiction_payload,
            "artifacts_loaded": [FILES[key] for key, value in docs.items() if value is not None],
        }
        return self._value

    @staticmethod
    def _summary(item):
        return {key: item.get(key) for key in (
            "sequence_id", "mechanism_id", "description", "direction", "timeframe_context",
            "causal_observability_status", "implementation_status", "failure_memory_relation",
            "branch_group_id", "semantic_leakage_status_original", "semantic_leakage_status_after_correction",
            "raw_claim_count", "source_count", "source_categories", "evidence_quality_distribution",
            "evidence_cluster_count", "provenance",
        )} | {"mechanism_name": (item.get("mechanism") or {}).get("name"), "priority": item.get("priority")}

    def list_sequences(self, filters=None):
        catalog, filters = self.build(), (filters or {})
        items = list(catalog["sequences"].values())
        mapping = {"priority": lambda x: (x.get("priority") or {}).get("tier"), "leakage_status": lambda x: x.get("semantic_leakage_status_after_correction")}
        for field in ("implementation_status", "failure_memory_relation", "causal_observability_status", "branch_group_id", "mechanism_id"):
            if filters.get(field): items = [item for item in items if str(item.get(field) or "").lower() == str(filters[field]).lower()]
        for field, getter in mapping.items():
            if filters.get(field): items = [item for item in items if str(getter(item) or "").lower() == str(filters[field]).lower()]
        query = str(filters.get("q") or "").strip().lower()
        if query:
            items = [item for item in items if query in " ".join(str(value or "") for value in (item.get("sequence_id"), item.get("mechanism_id"), (item.get("mechanism") or {}).get("name"), item.get("description"))).lower()]
        items.sort(key=lambda x: (-int((x.get("priority") or {}).get("total_score") or -1), x["sequence_id"]))
        return {"items": [self._summary(item) for item in items], "count": len(items), "warnings": catalog["warnings"], "artifacts_loaded": catalog["artifacts_loaded"]}

    def detail(self, sequence_id): return self.build()["sequences"].get(sequence_id)

    def list_mechanisms(self):
        catalog = self.build()
        items = []
        for mechanism in catalog["mechanisms"].values():
            related = [item for item in catalog["sequences"].values() if item.get("mechanism_id") == mechanism.get("mechanism_id")]
            items.append({**mechanism, "sequence_ids": [item["sequence_id"] for item in related], "sequence_count": len(related)})
        return {"items": sorted(items, key=lambda x: x["mechanism_id"]), "count": len(items), "warnings": catalog["warnings"]}

    def list_branches(self):
        catalog = self.build()
        items = [{**branch, "sequence_ids": sorted([item["sequence_id"] for item in catalog["sequences"].values() if item.get("branch_group_id") == branch_id])} for branch_id, branch in catalog["branches"].items()]
        return {"items": sorted(items, key=lambda x: x["branch_group_id"]), "count": len(items), "label": "Conditional Branch", "warnings": catalog["warnings"]}

    def readiness_summary(self):
        catalog = self.build(); statuses = Counter(item.get("implementation_status") for item in catalog["sequences"].values())
        return {"ready_for_phase_7_3": catalog["readiness"].get("ready_for_phase_7_3") if catalog["readiness"] else None,
                "gate": catalog["readiness"], "counts": {key: statuses.get(key, 0) for key in ("READY_FOR_FORMALIZATION", "NEEDS_ADDITIONAL_SPECIFICATION", "NOT_IMPLEMENTABLE_AS_DESCRIBED")},
                "sequence_count": len(catalog["sequences"]), "warnings": catalog["warnings"],
                "provenance": {"mode": "RESEARCH", "source_artifact": FILES["readiness"], "source_phase": "Phase7.2B"}}


CATALOG = SequenceResearchCatalog()
