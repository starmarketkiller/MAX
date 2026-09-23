"""Read-only freshness comparison for Product / Control Plane projections.

This module deliberately inspects artifact identity and phase metadata only. It
does not project, reinterpret, or expose scientific conclusions from artifacts
newer than the product read model.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
P7 = ROOT / "research_scripts" / "phase7"

# Ordering is governed explicitly; filenames are never sorted to infer recency.
PHASE_ORDER = {
    "7.7A": 10,
    "7.7B": 20,
    "7.9A": 30,
    "7.9B": 40,
    "7.9C": 50,
    "7.9D": 60,
    "7.9E": 70,
    "7.9F": 80,
}

STRATEGY_IDS = (
    "ADX_RSI", "BREAKOUT_ACC", "H006_LIQUIDITY_SWEEP_RECLAIM",
    "H015_SAR_EXTERNAL_VALIDATION", "SAR_LIVE",
    "VOLATILITY_BREAKOUT_CONFIRMED", "WICK_SWEEP_RECLAIM",
)

# The entity associations are catalog metadata, not scientific classifications.
CANONICAL_SOURCES = (
    {"phase": "7.7B", "path": P7 / "phase7_7b" / "missing_field_semantics_refinement_v1.json", "entities": STRATEGY_IDS},
    {"phase": "7.9A", "path": P7 / "phase7_9a" / "phase7_9a_postmortem_and_reprioritization_v1.json", "entities": STRATEGY_IDS},
    {"phase": "7.9B", "path": P7 / "phase7_9b" / "breakout_acc_formalization_decision_v1.json", "entities": ("BREAKOUT_ACC",)},
    {"phase": "7.9C", "path": P7 / "phase7_9c" / "breakout_acc_parity_decision_v1.json", "entities": ("BREAKOUT_ACC",)},
    {"phase": "7.9D", "path": P7 / "phase7_9d" / "breakout_acc_execution_parity_decision_v1.json", "entities": ("BREAKOUT_ACC",)},
    {"phase": "7.9E", "path": P7 / "phase7_9e" / "breakout_acc_reconstruction_decision_v1.json", "entities": ("BREAKOUT_ACC",)},
    {"phase": "7.9F", "path": P7 / "phase7_9f" / "breakout_acc_identity_adjudication_v1.json", "entities": ("BREAKOUT_ACC",)},
)

PROJECTED_SOURCE_PHASES = {
    "server/research_scripts/phase7/phase7_7b/missing_field_semantics_refinement_v1.json": "7.7B",
    "server/research_scripts/phase7/phase7_9a/phase7_9a_postmortem_and_reprioritization_v1.json": "7.9A",
    "server/research_scripts/phase7/phase7_9b/breakout_acc_formalization_decision_v1.json": "7.9B",
}


def _repo_path(path: Path) -> str:
    return path.relative_to(ROOT.parent).as_posix()


def _load_descriptor(descriptor: dict, warnings: list[dict]) -> dict | None:
    path = descriptor["path"]
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or not isinstance(doc.get("payload"), dict):
            raise ValueError("root and payload must be objects")
        raw_phase = doc["payload"].get("phase")
        if not isinstance(raw_phase, str) or not raw_phase.upper().startswith(descriptor["phase"]):
            raise ValueError("artifact phase does not match catalog metadata")
        return doc
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        warnings.append({"source": _repo_path(path), "error": type(exc).__name__, "scope": "FRESHNESS"})
        return None


def _latest_projected_source(strategy: dict) -> tuple[str | None, str | None]:
    metadata = strategy.get("projection_metadata") or {}
    if metadata.get("latest_phase") in PHASE_ORDER and metadata.get("latest_source"):
        return metadata["latest_phase"], metadata["latest_source"]
    candidates = []
    for source in (strategy.get("provenance") or {}).get("sources") or []:
        phase = PROJECTED_SOURCE_PHASES.get(source)
        if phase:
            candidates.append((PHASE_ORDER[phase], phase, source))
    if not candidates:
        return None, None
    _, phase, source = max(candidates, key=lambda item: item[0])
    return phase, source


class ProjectionFreshnessCatalog:
    def build(self, strategies: list[dict]) -> dict:
        warnings: list[dict] = []
        loaded = []
        failed_entities: set[str] = set()
        for descriptor in CANONICAL_SOURCES:
            doc = _load_descriptor(descriptor, warnings)
            if doc is None:
                failed_entities.update(descriptor["entities"])
                loaded.append({**descriptor, "doc": None})
            else:
                loaded.append({**descriptor, "doc": doc})

        records = []
        for strategy in strategies:
            strategy_id = strategy.get("strategy_id")
            relevant = [source for source in loaded if strategy_id in source["entities"]]
            valid = [source for source in relevant if source["doc"] is not None]
            canonical = max(valid, key=lambda item: PHASE_ORDER[item["phase"]]) if valid else None
            projected_phase, projected_source = _latest_projected_source(strategy)

            # A configured source failure makes freshness unknowable for the
            # affected entity; silently falling back could claim CURRENT.
            if strategy_id in failed_entities or canonical is None or projected_phase is None:
                status = "UNKNOWN"
            else:
                canonical_rank = PHASE_ORDER[canonical["phase"]]
                projected_rank = PHASE_ORDER[projected_phase]
                if projected_rank < canonical_rank:
                    status = "STALE"
                elif projected_rank == canonical_rank and projected_source == _repo_path(canonical["path"]):
                    status = "CURRENT"
                else:
                    status = "PARTIAL"

            canonical_path = _repo_path(canonical["path"]) if canonical else None
            canonical_doc = canonical["doc"] if canonical else None
            canonical_phase = canonical["phase"] if canonical else None
            lag = (f"Canonical research through {canonical_phase}; Product projection through {projected_phase}."
                   if canonical_phase and projected_phase and status == "STALE" else
                   "Freshness source coverage is incomplete." if status == "UNKNOWN" else
                   f"Product projection matches canonical research through {canonical_phase}." if status == "CURRENT" else
                   "Projection and canonical coverage only partially align.")
            records.append({
                "entity_type": "STRATEGY", "entity_id": strategy_id,
                "canonical_latest_source": canonical_path,
                "canonical_latest_phase": canonical_phase,
                "projected_latest_source": projected_source,
                "projected_latest_phase": projected_phase,
                "freshness_status": status,
                "lag_description": lag,
                "blocking_or_informational": "INFORMATIONAL",
                "provenance": {
                    "mode": "DERIVED", "direct": False,
                    "canonical_source": canonical_path,
                    "canonical_sha256": canonical_doc.get("canonical_sha256") if canonical_doc else None,
                    "projected_source": projected_source,
                    "phase_order": "EXPLICIT_CATALOG",
                },
            })

        counts = {status: sum(record["freshness_status"] == status for record in records)
                  for status in ("CURRENT", "STALE", "PARTIAL", "UNKNOWN")}
        known_canonical = [record for record in records if record["canonical_latest_phase"] in PHASE_ORDER]
        known_projected = [record for record in records if record["projected_latest_phase"] in PHASE_ORDER]
        return {
            "items": records, "count": len(records), "counts": counts,
            "latest_canonical_phase": max((record["canonical_latest_phase"] for record in known_canonical), key=lambda phase: PHASE_ORDER[phase], default=None),
            "latest_projection_phase": max((record["projected_latest_phase"] for record in known_projected), key=lambda phase: PHASE_ORDER[phase], default=None),
            "warnings": warnings,
        }


CATALOG = ProjectionFreshnessCatalog()
