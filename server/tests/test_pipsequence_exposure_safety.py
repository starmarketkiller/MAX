"""Static safety contract for PipSequence and every current exposure path.

These tests deliberately distinguish source-level guarantees from an MQL5
runtime proof.  They prevent the P0 bypass from returning while keeping the
known DataCollection and disabled NXR paths visible as separate findings.
"""
from __future__ import annotations

import re
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


def test_pipsequence_composes_both_economic_gate_families_before_send():
    body = _body(_src(INC / "NXS_PipSequence.mqh"), "void NXS_ManagePipSequence()")
    protections = body.index("NXS_CheckProtections(protReason)")
    common = body.index("NXS_CommonExposurePreflight(\"PIPSEQ_REENTRY\"")
    buy = body.index("NXS_SafeBuy(InpPipSeqLot")
    sell = body.index("NXS_SafeSell(InpPipSeqLot")
    assert protections < common < buy
    assert protections < common < sell


def test_a_gate_denial_terminally_consumes_the_reentry_request():
    source = _src(INC / "NXS_PipSequence.mqh")
    helper = _body(source, "void _pipSeqFinishReentry(")
    assert "g_pipSeqAwaitingReentry = false;" in helper
    assert "g_pipSeqReentryDir = 0;" in helper
    assert "g_pipSeqReentrySLDist = 0;" in helper

    manage = _body(source, "void NXS_ManagePipSequence()")
    protection_denial = manage.split("if(!NXS_CheckProtections(protReason))", 1)[1].split(
        "if(!NXS_CommonExposurePreflight", 1
    )[0]
    common_denial = manage.split("if(!NXS_CommonExposurePreflight", 1)[1].split(
        "bool ok =", 1
    )[0]
    for branch, state in (
        (protection_denial, "PIPSEQ_REENTRY_CANCELLED_PROTECTION"),
        (common_denial, "PIPSEQ_REENTRY_CANCELLED_COMMON_GATE"),
    ):
        assert f"_pipSeqFinishReentry({state}" in branch
        assert "return;" in branch
        assert "resta armato" not in branch


def test_terminal_reason_is_structured_and_does_not_grant_a_retry():
    source = _src(INC / "NXS_PipSequence.mqh")
    for reason in ("PIPSEQ_PROTECTION_DENIED", "PIPSEQ_COMMON_GATE_DENIED"):
        assert reason in source
    assert "g_pipSeqReentryTerminalReason" in source
    assert "g_pipSeqReentryTerminalGate" in source
    # PipSequence state is intentionally volatile: a restart cannot resurrect
    # an armed request.  Persistence needs its own versioned design.
    state = _src(INC / "NXS_State.mqh")
    assert "g_pipSeqAwaitingReentry" not in state
    assert "g_pipSeqReentryDir" not in state


def test_protection_flatten_runs_before_the_now_gated_reentry():
    ea = _src(EA)
    assert ea.index("NXS_Prot_OnTick();") < ea.index("NXS_ManagePipSequence();")
    pip = _src(INC / "NXS_PipSequence.mqh")
    assert pip.index("NXS_CheckProtections(protReason)") < pip.index(
        "NXS_SafeBuy(InpPipSeqLot"
    )


def test_current_exposure_path_census_keeps_known_exceptions_explicit():
    """No opening route may silently appear outside the reviewed census."""
    safe_calls: dict[str, int] = {}
    for path in [*INC.glob("*.mqh"), EA]:
        if path.name == "NXS_SafeOrder.mqh":
            continue  # function definitions, not exposure call sites
        text = _src(path)
        count = len(re.findall(r"NXS_Safe(?:Buy|Sell)\s*\(", text))
        if count:
            safe_calls[path.name] = count

    assert safe_calls == {
        "NXS_GridRecovery.mqh": 2,
        "NXS_Execution.mqh": 2,
        "NXS_InstManage.mqh": 2,
        "NXS_PipSequence.mqh": 2,
        "NXS_ProfitReclaim.mqh": 2,
        "NXS_Pyramiding.mqh": 2,
        "NXS_ReusePerformancePack.mqh": 2,
        "NXS_SLReclaim.mqh": 2,
        "NEXUS_EA_v2.mq5": 2,
    }

    protected = {
        "NXS_Execution.mqh": (True, True),
        "NXS_GridRecovery.mqh": (False, True),
        "NXS_InstManage.mqh": (False, True),
        "NXS_PipSequence.mqh": (True, True),
        "NXS_ProfitReclaim.mqh": (True, True),
        "NXS_Pyramiding.mqh": (False, True),
        "NXS_SLReclaim.mqh": (True, True),
    }
    for name, (needs_account_protections, needs_common) in protected.items():
        source = _src(INC / name)
        if needs_account_protections:
            assert "NXS_CheckProtections(" in source, name
        if needs_common:
            assert "NXS_CommonExposurePreflight(" in source, name

    # DataCollection is now part of the reviewed economic-gate family. NXR is
    # still the separate, disabled pre-existing finding.
    data_collection = _body(_src(EA), "void OnTick()").split(
        "if(InpDataCollectionMode)", 1
    )[1].split("// === CORE ISTITUZIONALE", 1)[0]
    assert "NXS_AccountGuard_DataCollectionAllowed(" in data_collection
    assert "NXS_CheckProtections(" in data_collection
    assert "NXS_CommonExposurePreflight(" in data_collection
    nxr = _src(INC / "NXS_ReusePerformancePack.mqh")
    assert "NXS_CommonExposurePreflight(" not in nxr
    assert re.search(r"InpNXR_Enable\s*=\s*false", nxr)


def test_final_send_boundary_stays_account_guarded_without_recursive_preflight():
    globals_source = _src(INC / "NXS_Globals.mqh")
    for name in ("NXS_DoBuy", "NXS_DoSell"):
        body = _body(globals_source, f"bool {name}(")
        assert body.index("NXS_AccountGuard_EntryAllowed(") < body.index("OrderSend(")
        assert "NXS_CommonExposurePreflight(" not in body
        assert "NXS_CheckProtections(" not in body

    # The final boundary lacks route/intent context and is deliberately not
    # made recursive.  Its universal backstop remains the fail-closed account
    # authorization; economic gates remain mandatory at each exposure route.

