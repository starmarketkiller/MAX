#!/usr/bin/env python3
"""Generate the versioned PR8 deployment manifest from tracked sources."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "MQL5/Experts/NEXUS_EA_v2.mq5",
    "LocalBridge/nexus_local_worker.py",
]


def _tracked_bytes(relative: str) -> bytes:
    """Byte content of the committed git blob (HEAD), not the working tree.

    Hashing the working-tree file makes the manifest depend on the checkout's
    line-ending conversion (e.g. `core.autocrlf=true` on Windows rewrites LF
    to CRLF locally while Linux CI keeps the blob's LF), so the same commit
    produces two different "correct" checksums depending on who regenerates
    it. Reading the git object directly is the one representation that is
    identical on every platform for a given commit.
    """
    return subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=ROOT, check=True, capture_output=True,
    ).stdout


def main():
    entries = []
    for relative in FILES:
        data = _tracked_bytes(relative)
        entries.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {
        "schema_version": 1,
        "release_id": "nexus-3.60",
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
