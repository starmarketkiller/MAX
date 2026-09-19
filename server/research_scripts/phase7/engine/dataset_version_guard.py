#!/usr/bin/env python3
"""Phase 7.0B sec.8-9 - Dataset Version Guard: collega davvero un
dataset_version_hash ai dati realmente usati, invece di essere un campo
previsto nello schema (candidate_result_v2.schema.json) ma mai calcolato
(gap DATASET_VERSION_DRIFT gia' dichiarato in red_team_analysis.json).

L'hash e' calcolato da COMPONENTI dichiarati esplicitamente (manifest
sorgente, date range, strumento, timeframe, versione di trasformazione/
build, versione feature) - MAI dal contenuto grezzo dei tick stessi
(troppo grande, e comunque gia' rappresentato dal manifest). Se un
componente cambia, l'hash cambia - e un dataset_id gia' registrato con
un hash diverso e' DATASET_VERSION_DRIFT, mai silenziosamente lo stesso
dataset.
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256  # noqa: E402


class DatasetVersionDriftError(Exception):
    pass


def compute_manifest_content_hash(manifest_path: str) -> str:
    """Hash SEMANTICO del contenuto del manifest (dict canonico), non dei
    byte grezzi del file - insensibile a differenze di formattazione
    JSON irrilevanti, sensibile a qualunque differenza di contenuto
    (giorni aggiunti/rimossi/cambiati)."""
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    return canonical_sha256(manifest)


def compute_dataset_version_hash(components: dict) -> str:
    """components deve contenere almeno: source_manifest_hash, date_range,
    instrument, timeframe, transform_version - feature_build_version e'
    opzionale (solo se il dataset_id include gia' feature derivate)."""
    required = ("source_manifest_hash", "date_range", "instrument", "timeframe", "transform_version")
    missing = [k for k in required if k not in components]
    if missing:
        raise ValueError(f"componenti mancanti per l'hash del dataset: {missing}")
    return canonical_sha256(components)


class DatasetVersionRegistry:
    def __init__(self, registry_path: str):
        self.registry_path = registry_path
        self.registry = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.registry_path):
            with open(self.registry_path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save(self):
        tmp = self.registry_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=True, default=str)
        os.replace(tmp, self.registry_path)

    def register_or_check(self, dataset_id: str, components: dict) -> dict:
        new_hash = compute_dataset_version_hash(components)
        existing = self.registry.get(dataset_id)
        if existing is None:
            entry = {
                "dataset_id": dataset_id, "hash": new_hash, "components": components,
                "first_registered_at": datetime.now(timezone.utc).isoformat(),
            }
            self.registry[dataset_id] = entry
            return {"status": "REGISTERED_NEW", "dataset_id": dataset_id, "hash": new_hash}
        if existing["hash"] == new_hash:
            return {"status": "MATCH", "dataset_id": dataset_id, "hash": new_hash}
        diff = {k: (existing["components"].get(k), components.get(k))
                for k in set(existing["components"]) | set(components)
                if existing["components"].get(k) != components.get(k)}
        return {
            "status": "DATASET_VERSION_DRIFT", "dataset_id": dataset_id,
            "old_hash": existing["hash"], "new_hash": new_hash, "diff_components": diff,
        }


def assert_no_drift(registry: DatasetVersionRegistry, dataset_id: str, components: dict) -> dict:
    result = registry.register_or_check(dataset_id, components)
    if result["status"] == "DATASET_VERSION_DRIFT":
        raise DatasetVersionDriftError(
            f"DATASET_VERSION_DRIFT per '{dataset_id}': hash precedente={result['old_hash'][:16]}... "
            f"hash nuovo={result['new_hash'][:16]}... componenti cambiati={result['diff_components']}"
        )
    return result


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        registry_path = os.path.join(tmp, "dataset_version_registry_demo.json")
        registry = DatasetVersionRegistry(registry_path)

        components_v1 = {
            "source_manifest_hash": "abc123demo", "date_range": ["2023-02-04", "2026-09-16"],
            "instrument": "XAUUSD", "timeframe": "TICK", "transform_version": "phase7_v1",
        }
        r1 = registry.register_or_check("DEMO_DATASET", components_v1)
        print("Prima registrazione:", r1["status"])
        assert r1["status"] == "REGISTERED_NEW"

        # Caso positivo: stesso identico rebuild -> stesso identico hash.
        r2 = registry.register_or_check("DEMO_DATASET", dict(components_v1))
        print("Rebuild identico:", r2["status"], "stesso hash:", r2["hash"] == r1["hash"])
        assert r2["status"] == "MATCH" and r2["hash"] == r1["hash"]

        # Caso negativo deliberato: stesso dataset_id, ma transform_version cambiata -> DRIFT.
        components_drifted = dict(components_v1, transform_version="phase7_v2_BROKEN_ON_PURPOSE")
        r3 = registry.register_or_check("DEMO_DATASET", components_drifted)
        print("Rebuild con transform_version diversa:", r3["status"], "diff=", r3.get("diff_components"))
        assert r3["status"] == "DATASET_VERSION_DRIFT"

        try:
            assert_no_drift(registry, "DEMO_DATASET", components_drifted)
            print("ERRORE: assert_no_drift avrebbe dovuto sollevare!")
        except DatasetVersionDriftError as e:
            print(f"assert_no_drift ha correttamente sollevato: {e}")

        print("\nTutti i test del dataset version guard superati.")
