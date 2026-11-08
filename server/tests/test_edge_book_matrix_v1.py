"""Pure-Python mirror of NXS_EdgeBook allow / deny rules."""
from __future__ import annotations

SHORTLIST = {
    "FVG_CONT",
    "LIQ_SWEEP",
    "ORDER_BLOCK",
    "BREAKOUT_ACC",
    "Z_SCORE_BREAKOUT",
    "EMA_PULLBACK",
}

HARD_DENIED = {
    "MACD",
    "RSI_DIV",
    "CRT",
    "BB_SQUEEZE",
    "TSI",
    "SH_BMS_RTO",
    "SH_BMS_RTO_V2",
    "SILVER_BULLET",
}


def allows(name: str, *, book_mode: str, research: bool) -> bool:
    if research:
        return True
    if book_mode == "EDGE_SHORTLIST":
        return name in SHORTLIST
    return name not in HARD_DENIED


def test_shortlist_matrix():
    for name in SHORTLIST:
        assert allows(name, book_mode="EDGE_SHORTLIST", research=False)
    assert not allows("MACD", book_mode="EDGE_SHORTLIST", research=False)
    assert not allows("SAR", book_mode="EDGE_SHORTLIST", research=False)
    assert not allows("STRUCT_REACT", book_mode="EDGE_SHORTLIST", research=False)


def test_full_hard_deny_matrix():
    assert not allows("MACD", book_mode="FULL", research=False)
    assert not allows("SILVER_BULLET", book_mode="FULL", research=False)
    assert allows("SAR", book_mode="FULL", research=False)
    assert allows("FVG_CONT", book_mode="FULL", research=False)


def test_research_bypasses_book():
    assert allows("MACD", book_mode="EDGE_SHORTLIST", research=True)
    assert allows("TSI", book_mode="FULL", research=True)


def test_mql_header_lists_match_python_mirror():
    from pathlib import Path

    text = (
        Path(__file__).resolve().parents[2]
        / "MQL5"
        / "Include"
        / "NEXUS_v1"
        / "NXS_EdgeBook.mqh"
    ).read_text(encoding="utf-8")
    for name in SHORTLIST | HARD_DENIED:
        assert f'"{name}"' in text


def test_collect_raw_every_push_is_book_gated():
    import re
    from pathlib import Path

    ea = (
        Path(__file__).resolve().parents[2]
        / "MQL5"
        / "Experts"
        / "NEXUS_EA_v2.mq5"
    ).read_text(encoding="utf-8")
    start = ea.index("int NXS_CollectRaw(")
    end = ea.index("if(InpUseStrategyProfiles)", start)
    body = ea[start:end]
    pushes = re.findall(r"out\[n\+\+\]\s*=\s*NXS_Strat_\w+", body)
    assert len(pushes) >= 40
    for line in body.splitlines():
        if "out[n++] = NXS_Strat_" not in line and "out[n++]=NXS_Strat_" not in line:
            continue
        assert "NXS_EdgeBook_Allows(" in line, line


def test_data_collection_path_is_book_gated():
    from pathlib import Path

    ea = (
        Path(__file__).resolve().parents[2]
        / "MQL5"
        / "Experts"
        / "NEXUS_EA_v2.mq5"
    ).read_text(encoding="utf-8")
    start = ea.index("=== MODALITÀ RACCOLTA DATI")
    end = ea.index("NXS_SafeBuy(dlots", start)
    dc = ea[start:end]
    assert "NXS_EdgeBook_Allows(s.stratName)" in dc
    assert "GATE_EDGE_BOOK" in dc
