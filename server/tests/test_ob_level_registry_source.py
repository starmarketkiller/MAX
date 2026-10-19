"""Static gate: Order Block Phase A telemetry hooks exist (Track B)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRAT = ROOT / "MQL5" / "Include" / "NEXUS_v1" / "NXS_Strategies.mqh"
REACT = ROOT / "MQL5" / "Include" / "NEXUS_v1" / "NXS_ReactionEngine.mqh"
REG = ROOT / "MQL5" / "Include" / "NEXUS_v1" / "NXS_LevelRegistry.mqh"
INPUTS = ROOT / "MQL5" / "Include" / "NEXUS_v1" / "NXS_Inputs.mqh"
EA = ROOT / "MQL5" / "Experts" / "NEXUS_EA_v2.mq5"


def test_ob_source_constant_and_create_accepts_source():
    reg = REG.read_text(encoding="utf-8", errors="replace")
    assert 'NXS_LVLSRC_ORDER_BLOCK' in reg
    assert "string source" in reg


def test_ob_hooks_in_update_side():
    src = STRAT.read_text(encoding="utf-8", errors="replace")
    assert "NXS_Reaction_OnObCreated" in src
    assert "NXS_Reaction_OnObInvalidated" in src
    assert "NXS_Reaction_OnObConsumed" in src
    assert "InpLevelRegistry_ObTelemetry" in src
    assert "g_obLevelIdCounter" in src


def test_ob_parity_printer_wired():
    react = REACT.read_text(encoding="utf-8", errors="replace")
    ea = EA.read_text(encoding="utf-8", errors="replace")
    inputs = INPUTS.read_text(encoding="utf-8", errors="replace")
    assert "NXS_LevelEngine_PrintObParity" in react
    assert "NXS_LevelEngine_PrintObParity" in ea
    assert "InpLevelRegistry_ObTelemetry" in inputs


def test_level_registry_included_before_strategies():
    ea = EA.read_text(encoding="utf-8", errors="replace")
    lines = [ln for ln in ea.splitlines() if ln.lstrip().startswith("#include")]
    i_reg = next(i for i, ln in enumerate(lines) if "NXS_LevelRegistry.mqh" in ln)
    i_strat = next(i for i, ln in enumerate(lines) if "NXS_Strategies.mqh" in ln
                   and "Experimental" not in ln and "SMC" not in ln
                   and "Institutional" not in ln and "Elliott" not in ln)
    # LevelRegistry must precede Strategies so OB hooks resolve at compile time.
    assert i_reg < i_strat
