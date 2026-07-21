#!/usr/bin/env python3
"""Generate the versioned PR8 deployment manifest from tracked sources."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "MQL5/Experts/NEXUS_EA_v2.mq5",
    "LocalBridge/nexus_local_worker.py",
]


def main():
    entries = []
    for relative in FILES:
        data = (ROOT / relative).read_bytes()
        entries.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {
        "schema_version": 1,
        "release_id": "nexus-3.50",
        "files": entries,
        "minimum_worker_version": "2.0.0",
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest["sha256"] = hashlib.sha256(canonical).hexdigest()
    target = ROOT / "deploy" / "deployment-manifest.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
