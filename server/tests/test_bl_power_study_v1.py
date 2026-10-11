"""BL-01 power verification, BL-02 sizing and their record in Research Memory.

All computations are synthetic; the only data-derived inputs are the H4
structural counts committed in the study report.
"""
from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research_scripts"
sys.path.insert(0, str(RESEARCH))

from bl_power_study_v1 import record_knowledge, run_study  # noqa: E402
from research_intelligence_v1 import pilot  # noqa: E402
from research_intelligence_v1 import power as P  # noqa: E402
from research_intelligence_v1.memory import MemoryViolation, ResearchMemory  # noqa: E402

STUDY = RESEARCH / "bl_power_study_v1"
MEMORY = RESEARCH / "research_intelligence_v1" / "memory"


def test_null_barrier_rate_and_moments():
    assert P.null_rate(2.0) == pytest.approx(1 / 3)
    mu, sd = P.moments(1 / 3)
    assert mu == pytest.approx(0.0, abs=1e-12) and sd == pytest.approx(math.sqrt(2))
    mu_c, _ = P.moments(1 / 3, cost_r=0.05, timeout_share=0.15)
    assert mu_c == pytest.approx(-0.05)


def test_loop_v1_figures_are_reproduced_and_explained():
    r = P.replicate_loop_v1()
    assert r["n_for_80pct"] == 372
    assert r["alpha"] == pytest.approx(0.05 / 6) and r["n"] == 80
    assert r["analytic_power"] == pytest.approx(0.2008, abs=1e-3)
    assert 0.15 < r["simulated_power"] < 0.30


def test_sample_size_and_mde_are_inverse():
    for mu in (0.1, 0.2, 0.3):
        n = P.n_required(mu, 1.4, deff=1.1)
        assert P.mde(n, 1.4, deff=1.1) <= mu < P.mde(n - 1, 1.4, deff=1.1) + 1e-9
        assert P.power_ci_low_positive(mu, 1.4, n, deff=1.1) == pytest.approx(0.8, abs=0.01)
    assert P.n_required(0.0, 1.4) == math.inf


def test_bl01_rule_simulation_is_deterministic_and_calibrated():
    a = P.simulate_bl01_rule(delta_p=0.08, conversion=0.6, month_sd=0.05, reps=300)
    b = P.simulate_bl01_rule(delta_p=0.08, conversion=0.6, month_sd=0.05, reps=300)
    assert a == b
    null = P.simulate_bl01_rule(delta_p=0.0, conversion=0.8, month_sd=0.05, reps=800)
    assert null["decision_rates"]["GO"] <= 0.03
    strong = P.simulate_bl01_rule(delta_p=0.16, conversion=0.8, month_sd=0.05, reps=800)
    assert strong["decision_rates"]["GO"] > null["decision_rates"]["GO"] + 0.2
    small = P.simulate_bl01_rule(delta_p=0.08, conversion=0.4, reps=800)
    assert small["decision_rates"]["GO"] == 0.0  # n >= 60 essentially unreachable
    expected_short = 1 - run_study.poisson_tail_ge(83.3 * 0.4, 30)
    assert small["decision_rates"]["STOP_SAMPLE"] == pytest.approx(expected_short, abs=0.05)


def test_committed_report_is_reproducible():
    committed = json.loads((STUDY / "bl01_power_report_v1.json").read_text())
    regenerated = json.loads(json.dumps(run_study.main(), sort_keys=True))
    assert regenerated == committed
    assert committed["bl01"]["p_trades_ge_60"]["0.6"] == pytest.approx(0.093, abs=0.002)
    assert committed["inputs_structural"]["pullbacks"] == 167


def test_bl02_draft_keeps_hypothesis_frozen_and_uses_unseen_data():
    draft = json.loads((STUDY / "BL-02_proposal_draft_v0.json").read_text())
    assert draft["status"] == "DRAFT_NOT_FROZEN"
    assert draft["hypothesis"]["params_sha256"] == pilot.PARAMS_SHA
    window = draft["data"]["primary_window"]
    assert window["end_utc"] <= "2019-01-01T00:00:00+00:00"  # before MARKET_STATE_V1, Phase 6 and Phase 7 data
    exposure = json.loads((RESEARCH / "phase7" / "phase7_26" / "data_exposure_registry_v1.json").read_text())
    for rec in exposure.get("payload", exposure)["records"]:
        start = (rec["date_range"] or [None])[0]
        if start:
            assert start.replace(".", "-") >= "2019-01-01", rec["dataset_id"]
    assert draft["minimum_effect"]["status"].startswith("PROPOSED")
    assert "never changed after BL-01" in draft["sample_size"]["rule_declared_now"]


def test_record_knowledge_is_idempotent_and_keeps_bl01_unchanged(tmp_path):
    for name in ("research_memory_v1.jsonl", "research_memory_v1.checkpoints.jsonl"):
        shutil.copy(MEMORY / name, tmp_path / name)
    mem = ResearchMemory(str(tmp_path / "research_memory_v1.jsonl"))
    hyp_hash = mem.get("HYP-BL-H4M15-IPC-001")["record_hash"]
    record_knowledge.record(mem)
    assert record_knowledge.record(mem) == []
    assert mem.verify() == []
    assert mem.get("HYP-BL-H4M15-IPC-001")["record_hash"] == hyp_hash
    cur = mem.current("EXP-BL-01-DISCOVERY")
    assert cur["record_id"] == "EXP-BL-01-DISCOVERY.R1" and cur["body"]["status"] == "NOT_RUN"
    assert cur["body"]["method"]["params_sha256"] == pilot.PARAMS_SHA and cur["body"]["method"]["preregistered"]
    assert any("preregistration kept unchanged" in c for c in cur["body"]["conclusions"])
    obs = mem.get("OBS-BL01-POWER-ANALYSIS-V1")["body"]
    assert "presence or absence of an edge" in obs["not_evidence_for"]


def test_history_cannot_fork(tmp_path):
    for name in ("research_memory_v1.jsonl", "research_memory_v1.checkpoints.jsonl"):
        shutil.copy(MEMORY / name, tmp_path / name)
    mem = ResearchMemory(str(tmp_path / "research_memory_v1.jsonl"))
    record_knowledge.record(mem)
    old = mem.get("EXP-BL-01-DISCOVERY")
    with pytest.raises(MemoryViolation, match="already superseded"):
        mem.append("EXPERIMENT", "EXP-BL-01-DISCOVERY.FORK", old["body"], author="t", origin="HUMAN",
                   project="P", family="BL-H4M15", relations=[{"type": "SUPERSEDES", "target": old["record_id"]}])


def test_committed_memory_holds_the_study():
    mem = ResearchMemory(str(MEMORY / "research_memory_v1.jsonl"))
    for rid in ("OBS-BL-H4-PULLBACK-FREQUENCY-2019-2022", "OBS-BL01-POWER-ANALYSIS-V1", "EXP-BL-01-DISCOVERY.R1",
                "PROP-POWER_MODEL_MISMATCH-C606CB6FC8", "PROP-PLANNING_ALPHA_FAMILY-2E57835FA5",
                "PROP-BL02_POWERED_REPLICATION-FA11F3CDCC"):
        assert mem.get(rid), rid
    assert mem.verify() == []
