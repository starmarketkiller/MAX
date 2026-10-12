from dataclasses import dataclass
import json
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

    def entry_allowed(self) -> bool:
        return not self.hit

    def save(self, path: Path) -> None:
        payload = {
            "schema": 6,
            "equity": self.equity,
            "net_flow": self.net_flow,
            "peak": self.peak,
            "hit": self.hit,
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        tmp.replace(path)

    @classmethod
    def restore(cls, path: Path) -> "ReferenceMaxDD":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != 6:
            raise ValueError("incompatible snapshot")
        return cls(
            equity=float(payload["equity"]),
            net_flow=float(payload["net_flow"]),
            peak=float(payload["peak"]),
            hit=bool(payload["hit"]),
        )


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


def test_reference_save_shutdown_restore_keeps_peak_latch_and_entry_gate(tmp_path):
    snapshot = tmp_path / "maxdd.json"
    before = ReferenceMaxDD(equity=8_900, peak=10_000, hit=True)
    before.save(snapshot)

    after = ReferenceMaxDD.restore(snapshot)
    assert after.peak == 10_000
    assert after.hit is True
    assert after.entry_allowed() is False


def test_reference_missing_corrupt_and_legacy_snapshots_fail_closed(tmp_path):
    for name, contents in (
        ("missing.json", None),
        ("corrupt.json", "{not-json"),
        ("legacy.json", json.dumps({"schema": 5})),
    ):
        snapshot = tmp_path / name
        if contents is not None:
            snapshot.write_text(contents, encoding="utf-8")
        blocked = False
        try:
            ReferenceMaxDD.restore(snapshot)
        except (FileNotFoundError, ValueError, json.JSONDecodeError):
            blocked = True
        assert blocked


def test_missing_corrupt_or_legacy_snapshot_fails_closed_outside_tester():
    assert 'g_maxDDRecoveryReason="MAX_DD_SNAPSHOT_MISSING"' in STATE
    assert 'g_maxDDRecoveryReason="MAX_DD_SNAPSHOT_INVALID_OR_INCOMPATIBLE"' in STATE
    assert "magic != NXS_STATE_MAGIC || ver != NXS_STATE_SCHEMA" in STATE
    assert "g_stateRestoreHealthy=false" in STATE
    assert EA.index("NXS_State_Load();") < EA.index("NXS_Prot_ResumeMaxDDFlatten();")


def test_capital_flow_policy_and_event_driven_accounting_are_explicit():
    assert "dealType == DEAL_TYPE_BALANCE" in PROT
    balance_branch = PROT.split("if(dealType == DEAL_TYPE_BALANCE){", 1)[1].split(
        "} else if", 1
    )[0]
    assert "g_maxDDNetCapitalFlow +=" not in balance_branch
    assert "UNVERIFIED_BALANCE_FLOW_TICKET" in balance_branch
    assert "g_maxDDRecoveryRequired = true" in balance_branch
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
    assert "NXS_Prot_CloseAlreadyInFlight" in PROT
    in_flight = PROT.split("bool NXS_Prot_CloseAlreadyInFlight", 1)[1].split(
        "int NXS_Prot_CloseAllWithReason", 1
    )[0]
    assert "ORDER_POSITION_ID" in in_flight
    assert "POSITION_IDENTIFIER" in in_flight


def test_reset_replay_is_rejected_before_the_mutating_handler():
    replay_guard = WEB.index("string prior = _nxs_cmd_seenStatus(commandId)")
    reset_handler = WEB.index('else if(action == "reset_protections")')
    assert replay_guard < reset_handler
    assert "_nxs_cmd_seenRecord(commandId, status)" in WEB


def test_atomic_save_keeps_last_snapshot_until_validated_replacement():
    save = STATE.split("void NXS_State_Save(bool force=false)", 1)[1].split(
        "void NXS_State_Load()", 1
    )[0]
    validate_tmp = save.index("_NXS_StateRead(tmp, false)")
    preserve_previous = save.index("FileCopy(main, FILE_COMMON, prev")
    replace_main = save.index("FileMove(tmp, FILE_COMMON, main")
    assert validate_tmp < preserve_previous < replace_main
    assert "g_stateRestoreHealthy=false" in save


def test_all_current_main_exposure_paths_retain_common_protection_gate():
    assert "NXS_Prot_EntryBlocked()" in EA
    execution = (ROOT / "MQL5/Include/NEXUS_v1/NXS_Execution.mqh").read_text(encoding="utf-8")
    assert "NXS_CommonExposurePreflight" in execution
    assert "bool protOK = !NXS_Prot_EntryBlocked();" in execution


def test_research_opt_out_remains_explicit_and_does_not_claim_old_22_83_case():
    assert "if(!NXS_IsResearchMode() || InpResearchUseTotalDD)" in PROT
