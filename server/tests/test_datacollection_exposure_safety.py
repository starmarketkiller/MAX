"""Static contract for the isolated DataCollection exposure path.

These checks prove source-level wiring. They do not replace a compiled MQL5
Strategy Tester run or a broker-account runtime test.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INC = ROOT / "MQL5" / "Include" / "NEXUS_v1"
EA = ROOT / "MQL5" / "Experts" / "NEXUS_EA_v2.mq5"


def _src(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _body(text: str, signature: str) -> str:
    start = text.index(signature)
    opening = text.index("{", start)
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening:index + 1]
    raise AssertionError(f"unbalanced function body: {signature}")


def _data_collection_branch() -> str:
    on_tick = _body(_src(EA), "void OnTick()")
    return on_tick.split("if(InpDataCollectionMode)", 1)[1].split(
        "// === CORE ISTITUZIONALE", 1
    )[0]


def test_data_collection_has_stricter_account_scope_than_normal_entries():
    guard = _body(
        _src(INC / "NXS_AccountGuard.mqh"),
        "bool NXS_AccountGuard_DataCollectionAllowed(",
    )
    assert 'mode == "TESTER" || mode == "DEMO"' in guard
    assert "InpLiveTradingAuthorized" not in guard
    assert "InpLiveAccountLogin" not in guard
    assert "data_collection_account_unknown" in guard
    assert "data_collection_non_demo_forbidden" in guard


def test_account_scope_is_checked_before_any_data_collection_send():
    branch = _data_collection_branch()
    account = branch.index("NXS_AccountGuard_DataCollectionAllowed(")
    buy = branch.index("NXS_SafeBuy(dlots")
    sell = branch.index("NXS_SafeSell(dlots")
    assert account < buy
    assert account < sell
    denial = branch.split("if(!NXS_AccountGuard_DataCollectionAllowed", 1)[1].split(
        "double dstep", 1
    )[0]
    assert "GATE_ACCOUNT_MODE" in denial
    assert "return;" in denial


def test_data_collection_composes_both_economic_gate_families_before_send():
    branch = _data_collection_branch()
    protections = branch.index("NXS_CheckProtections(dcProtReason)")
    common = branch.index('NXS_CommonExposurePreflight("DATA_COLLECTION:"')
    buy = branch.index("NXS_SafeBuy(dlots")
    sell = branch.index("NXS_SafeSell(dlots")
    assert protections < common < buy
    assert protections < common < sell
    # Broker preflight is owned by the common gate; no parallel direct subset.
    assert "NXS_PreFlight(dot" not in branch


def test_tester_parity_policy_remains_explicit_and_default_on():
    inputs = _src(INC / "NXS_Inputs.mqh")
    protections = _body(_src(INC / "NXS_Risk.mqh"), "bool NXS_CheckProtections(")
    assert "InpTesterProtectionParity = true" in inputs
    assert "MQLInfoInteger(MQL_TESTER) && !InpTesterProtectionParity" in protections


def test_rejection_does_not_disable_management_or_close_paths():
    # The restriction lives only inside the DataCollection entry branch. It
    # must not turn into an OnInit failure or gate close/modify helpers.
    ea = _src(EA)
    guard_call = "NXS_AccountGuard_DataCollectionAllowed(dcAccountReason)"
    assert ea.count(guard_call) == 1
    assert guard_call not in _body(ea, "int OnInit()")
    globals_source = _src(INC / "NXS_Globals.mqh")
    for helper in ("NXS_DoClose", "NXS_DoClosePartial", "NXS_DoModify"):
        assert "NXS_AccountGuard_DataCollectionAllowed(" not in _body(
            globals_source, f"bool {helper}("
        )
