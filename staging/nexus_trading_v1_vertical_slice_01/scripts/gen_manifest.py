"""gen_manifest.py - writes MANIFEST_SHA256.txt for this slice's own
deliverable tree. Same convention as the sibling missions in
staging/ (gen_manifest.py pattern): "<sha256>  <size_bytes>  <relative_path>",
one line per file, sorted by path, excludes caches/scratch/the
manifest file itself (none of these are deliverables).
"""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "MANIFEST_SHA256.txt"
EXCLUDE_DIR_NAMES = {"__pycache__", ".pytest_cache", "_scratch"}

lines = []
for p in sorted(ROOT.rglob("*")):
    if not p.is_file():
        continue
    if p == MANIFEST:
        continue
    if EXCLUDE_DIR_NAMES & set(p.parts):
        continue
    data = p.read_bytes()
    h = hashlib.sha256(data).hexdigest()
    rel = p.relative_to(ROOT).as_posix()
    lines.append(f"{h}  {len(data)}  {rel}")

MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {len(lines)} entries to {MANIFEST}")
