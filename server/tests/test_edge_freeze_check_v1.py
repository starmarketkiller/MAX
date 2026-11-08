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


def test_collector_gates_classic_strategies_through_edge_book():
    ea = (ROOT / "MQL5" / "Experts" / "NEXUS_EA_v2.mq5").read_text(encoding="utf-8")
    assert 'NXS_EdgeBook_Allows("MACD")' in ea
    assert 'NXS_EdgeBook_Allows("FVG_CONT")' in ea
    assert 'NXS_EdgeBook_Allows("Z_SCORE_BREAKOUT")' in ea
    assert "out[n++] = NXS_Strat_MACD();" not in ea.replace(
        'if(NXS_EdgeBook_Allows("MACD"))         out[n++] = NXS_Strat_MACD();', ""
    )


def test_fvg_cont_forward_status_matches_phase_734():
    import json

    reg = json.loads(
        (ROOT / "contracts" / "edge-validation-registry.json").read_text(encoding="utf-8")
    )
    fvg = next(s for s in reg["strategies"] if s["strategy_id"] == "FVG_CONT")
    assert fvg["forward_validation_status"] == "INSUFFICIENT_EVIDENCE"
    assert fvg["standalone_edge_status"] == "CANDIDATE"
    assert any("7.34" in note or "Phase 7.34" in note for note in fvg["validation_notes"])
