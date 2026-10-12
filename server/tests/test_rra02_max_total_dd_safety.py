from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GLOBALS = (ROOT / "MQL5/Include/NEXUS_v1/NXS_Globals.mqh").read_text(encoding="utf-8")
STATE = (ROOT / "MQL5/Include/NEXUS_v1/NXS_State.mqh").read_text(encoding="utf-8")
PROT = (ROOT / "MQL5/Include/NEXUS_v1/NXS_Protections.mqh").read_text(encoding="utf-8")
WEB = (ROOT / "MQL5/Include/NEXUS_v1/NXS_WebBridge.mqh").read_text(encoding="utf-8")
EA = (ROOT / "MQL5/Experts/NEXUS_EA_v2.mq5").read_text(encoding="utf-8")


@dataclass
class ReferenceMaxDD:
    equity: float
    net_flow: float = 0.0
    peak: float = 0.0
    hit: bool = False

    def check(self, threshold: float = 10.0) -> float:
        adjusted = self.equity - self.net_flow
        assert adjusted > 0
        self.peak = max(self.peak, adjusted)
        dd = 100.0 * (self.peak - adjusted) / self.peak
        self.hit = self.hit or dd >= threshold
        return dd

    def flow(self, amount: float) -> None:
        self.equity += amount
        self.net_flow += amount


def test_adjusted_high_water_mark_neutralizes_verified_deposit_and_withdrawal():
    model = ReferenceMaxDD(10_000)
    assert model.check() == 0
    model.equity = 12_000
    assert model.check() == 0
    model.equity = 11_000
    before = model.check()
    model.flow(2_000)
    assert model.check() == before
    model.flow(-1_000)
    assert model.check() == before
    model.equity = 11_700
    assert model.check() > 10
    assert model.hit


def test_latch_is_permanent_across_rollover_and_restart_contract():
    assert "g_maxDDHit || g_maxDDRecoveryRequired" in PROT
    rollover = PROT.split("void NXS_Prot_OnNewDay()", 1)[1].split("// ===================================================================", 1)[0]
    assert "g_maxDDHit = false" not in rollover
    for field in (
        "g_maxDDPeakEquity",
        "g_maxDDHit",
        "g_maxDDNetCapitalFlow",
        "g_maxDDFlowCursorMsc",
        "g_maxDDFlowCursorTicket",
        "g_maxDDRecoveryRequired",
        "g_maxDDRecoveryReason",
    ):
        assert field in GLOBALS
        assert field in STATE
    assert "#define NXS_STATE_SCHEMA  6" in STATE


def test_missing_corrupt_or_legacy_snapshot_fails_closed_outside_tester():
    assert 'g_maxDDRecoveryReason="MAX_DD_SNAPSHOT_MISSING"' in STATE
    assert 'g_maxDDRecoveryReason="MAX_DD_SNAPSHOT_INVALID_OR_INCOMPATIBLE"' in STATE
    assert "magic != NXS_STATE_MAGIC || ver != NXS_STATE_SCHEMA" in STATE
    assert "g_stateRestoreHealthy=false" in STATE


def test_capital_flow_policy_and_event_driven_accounting_are_explicit():
    assert "dealType == DEAL_TYPE_BALANCE" in PROT
    for ambiguous in ("DEAL_TYPE_CREDIT", "DEAL_TYPE_BONUS", "DEAL_TYPE_CORRECTION"):
        assert ambiguous in PROT
    assert "NXS_Prot_ReconcileCapitalFlows()" in EA
    on_tx = EA.split("void OnTradeTransaction", 1)[1]
    assert "NXS_Prot_OnDeal(trans.deal);" in on_tx


def test_authorized_reset_creates_and_persists_a_new_epoch():
    reset = PROT.split("void NXS_Prot_AuthorizedMaxDDReset()", 1)[1].split(
        "void NXS_Prot_CheckMaxTotalDD", 1
    )[0]
    assert "g_maxDDPeakEquity = eq" in reset
    assert "g_maxDDNetCapitalFlow = 0.0" in reset
    assert "g_maxDDHit = false" in reset
    assert "g_maxDDRecoveryRequired = false" in reset
    assert "NXS_State_Save(true)" in reset
    web_reset = WEB.split('else if(action == "reset_protections")', 1)[1].split(
        'else if(action == "resync_trades")', 1
    )[0]
    assert "NXS_Prot_AuthorizedMaxDDReset()" in web_reset
    assert "_nxs_cmd_isSafetyReset(action)" in WEB
    assert "_nxs_cmd_auditLocal" in WEB


def test_protection_blocks_new_exposure_without_disabling_position_management_code():
    gate = PROT.split("bool NXS_Prot_EntryBlocked()", 1)[1].split(
        "void NXS_Prot_OnTick()", 1
    )[0]
    assert "g_maxDDHit" in gate
    assert "g_maxDDRecoveryRequired" in gate
    assert "NXS_Prot_CheckMaxHold()" in PROT
    assert "NXS_Prot_CheckMaxLossPerPos()" in PROT
    assert "NXS_Prot_FlattenAll" in PROT
    assert "NXS_Prot_ResumeMaxDDFlatten()" in EA
    resume = PROT.split("void NXS_Prot_ResumeMaxDDFlatten()", 1)[1].split(
        "void NXS_Prot_CheckMaxTotalDD", 1
    )[0]
    assert "g_maxDDHit" in resume
    assert "NXS_Prot_FlattenAll" in resume
    assert "NXS_State_Save(true)" in resume


def test_all_current_main_exposure_paths_retain_common_protection_gate():
    assert "NXS_Prot_EntryBlocked()" in EA
    execution = (ROOT / "MQL5/Include/NEXUS_v1/NXS_Execution.mqh").read_text(encoding="utf-8")
    assert "NXS_CommonExposurePreflight" in execution
    assert "bool protOK = !NXS_Prot_EntryBlocked();" in execution


def test_research_opt_out_remains_explicit_and_does_not_claim_old_22_83_case():
    assert "if(!NXS_IsResearchMode() || InpResearchUseTotalDD)" in PROT
