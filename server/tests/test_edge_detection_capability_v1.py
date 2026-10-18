"""Edge Detection Capability Test V1: integrity of the preserved evidence.

Offline and fast: checks artifact hashes against the manifest and that the
recorded verdict follows from the committed results under the frozen
decision rule. It does not re-run the simulation (about 15 minutes).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1] / "research_scripts" / "edge_detection_capability_v1"
ROOT = Path(__file__).resolve().parents[2]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(name: str):
    return json.loads((STUDY / name).read_text(encoding="utf-8"))


def test_artifact_hashes_match_manifest():
    manifest = _load("manifest_v1.json")
    for name, digest in manifest["artifacts_sha256"].items():
        assert _sha(STUDY / name) == digest, name


def test_input_hashes_match_manifest():
    manifest = _load("manifest_v1.json")
    for rel, digest in manifest["inputs_sha256"].items():
        assert _sha(ROOT / rel) == digest, rel


def test_protocol_frozen_hash():
    recorded = (STUDY / "protocol_v1.sha256").read_text().split()[0]
    assert _sha(STUDY / "protocol_v1.json") == recorded
    assert _load("results_v1.json")["meta"]["protocol_sha256"] == recorded


def test_verdict_follows_from_results():
    res = _load("results_v1.json")
    sig = [c for c in res["signal"] if c["cost_atr"] == 0]
    # Scoped calibration defect: IID bootstrap liberal under clustered events.
    clustered_null = [c["rejection_rate"]["M1"] for c in sig if c["gen"] == "G_C" and c["delta_atr"] == 0]
    assert min(clustered_null) > 0.075
    # A calibrated dependence-aware alternative exists: M3 never above 0.075.
    # M2 exceeds it once (0.0825, clustered n=200), recorded in the manifest.
    null = [c for c in sig if c["delta_atr"] == 0 and c["gen"] in ("G_U", "G_C")]
    assert max(c["rejection_rate"]["M3"] for c in null) <= 0.075
    assert max(c["rejection_rate"]["M2"] for c in null) == 0.0825
    # Underpowered: no economically relevant edge reaches 80% power at n <= 50.
    for c in res["trade"]:
        if c["n"] <= 50 and c["deltaR"] in (0.1, 0.2, 0.3):
            assert c["power_lower_ci_gt_0"] < 0.80
    for c in sig:
        if c["n"] <= 50 and c["delta_atr"] in (0.25, 0.5):
            assert max(c["rejection_rate"][m] for m in ("M2", "M3")) < 0.80
    assert _load("manifest_v1.json")["verdict"] == "PIPELINE_UNDERPOWERED"
