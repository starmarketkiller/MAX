"""EDGE_SHORTLIST .set completeness."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "edge_book_set_check.py"


def test_edge_book_set_check_passes():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=str(ROOT), capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK:" in completed.stdout


def test_smoke_ini_carries_book_mode():
    text = (ROOT / "MQL5" / "Profiles" / "NEXUS_EDGE_SHORTLIST_GOLD_SMOKE.ini").read_text(
        encoding="utf-8"
    )
    assert "InpBookMode=1" in text
    assert "Symbol=GOLD" in text
    assert "InpLiveTradingAuthorized=false" in text
    assert "confirmatory edge claim" in (
        ROOT / "docs" / "EDGE_BOOK_TESTER_RUNBOOK_V1.md"
    ).read_text(encoding="utf-8")
