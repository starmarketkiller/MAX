"""Tier-0 freeze / edge-book alignment."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "edge_freeze_check.py"


def test_edge_freeze_check_passes():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=str(ROOT), capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK:" in completed.stdout


def test_edge_book_header_exists():
    path = ROOT / "MQL5" / "Include" / "NEXUS_v1" / "NXS_EdgeBook.mqh"
    text = path.read_text(encoding="utf-8")
    assert "NXS_BOOK_EDGE_SHORTLIST" in (
        ROOT / "MQL5" / "Include" / "NEXUS_v1" / "NXS_Inputs.mqh"
    ).read_text(encoding="utf-8")
    assert "NXS_EdgeBook_Allows" in text
    assert "not a claim of validated economic edge" in text.lower() or "NOT a claim" in text
