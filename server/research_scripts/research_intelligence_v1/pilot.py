"""BL-01 pilot: seed Research Memory with the Behavior Lab family.

Writes, never changes:
  HYP-BL-H4M15-IPC-001   the preregistered hypothesis as declared on PR #39
                         (params sha 7c66d51c..., commit 613a9a8), HUMAN origin
  OBS-BL-H4-SELECTIVITY-2019-2022
                         impulse -> pullback counts on MARKET_STATE_V1 H4 bars:
                         EXPLORATORY, outside the BL-01 splits, not evidence for
                         the hypothesis
  EXP-BL-01-DISCOVERY    the planned discovery run, NOT_RUN until the real
                         summary.json is ingested with ingest.import_behavior_lab_summary
Then alternatives to the low selectivity are generated as proposals; the
preregistered hypothesis and its parameters are untouched.
"""
from __future__ import annotations

from .generator import register_candidates, selectivity_alternatives
from .hypotheses import FamilyBudget, register

FAMILY = "BL-H4M15"
PROJECT = "NEXUS_TRADING_RESEARCH"
PREREG_COMMIT = "613a9a852788ebc6086eb218a94779f83db77b15"
PREREG_REF = "server/research_scripts/behavior_lab_v1/prereg_BL-H4M15-IPC-001.json"
PARAMS_SHA = "7c66d51c10a33e0012dc874eedd7efdb7c49d3f30ebd758d022600579f7235c9"
H4_BARS_SHA = "4f4a248ddfab4f0dafcab5274633e3001c9b6adcb922b71c733069668cf7ebcb"
DISCOVERY_DATA = "DUKASCOPY_XAUUSD_TICKS_2022-11_2024-08"

BL001_SPEC = {
    "event_family": "XAUUSD_H4_IMPULSE_PULLBACK_M15_MICROBREAK", "direction": "WITH_IMPULSE",
    "state_conditions": [
        {"feature_id": "impulse_body_atr_mult", "operator": ">=", "threshold": 1.5},
        {"feature_id": "impulse_body_to_range_min", "operator": ">=", "threshold": 0.6},
        {"feature_id": "pullback_retrace_min", "operator": ">=", "threshold": 0.382},
        {"feature_id": "pullback_max_h4_bars", "operator": "<=", "threshold": 6},
        {"feature_id": "confirm_window_m15_bars", "operator": "<=", "threshold": 16},
    ],
    "outcome_definition": "+2R before -1R net of spread within 96 M15 bars",
    "mechanism": "after a displacement leg and a partial retrace, a micro-break in the impulse direction marks "
                 "the return of the impulse flow",
    "falsification": "p_target_first not above the no-context M15 control net of spread on discovery "
                     "(BL01_DECISION_RULES_V1)",
    "data_needed": [DISCOVERY_DATA], "overfitting_risk": "MEDIUM", "expected_information_value": "HIGH",
    "version": "1+A1",
}
SELECTIVITY_VALUES = {"h4_bars": 4809, "impulses": 183, "impulse_rate": 0.0381, "pullbacks": 167,
                      "pullback_rate": 0.0347, "conversion_impulse_to_pullback": 0.913,
                      "impulse_status": "NORMAL", "pullback_status": "NORMAL",
                      "pullbacks_per_year": {"2019": 60, "2020": 58, "2021": 45, "2022": 4},
                      "note_2022": "dataset ends 2022-02-03: the 2022 count covers one month"}


def seed(memory, *, author="research-memory-curator", created_at=None):
    """Idempotent: existing records are kept as they are."""
    out = {"added": [], "kept": []}
    hyp = "HYP-BL-H4M15-IPC-001"
    if memory.get(hyp):
        out["kept"].append(hyp)
    else:
        register(memory, "BL-H4M15-IPC-001", BL001_SPEC,
                 statement="XAUUSD: H4 impulse -> H4 pullback >= 38.2% -> M15 micro-break -> +2R before -1R",
                 origin="HUMAN", author="preregistration PR #39", project=PROJECT, family=FAMILY,
                 lifecycle_state="PREREGISTERED", evidence_level="NONE_PROPOSAL", created_at=created_at,
                 provenance=[{"kind": "GIT_COMMIT", "ref": PREREG_COMMIT, "note": PREREG_REF},
                             {"kind": "PR", "ref": "starmarketkiller/MAX#39"}])
        out["added"].append(hyp)

    obs = "OBS-BL-H4-SELECTIVITY-2019-2022"
    if memory.get(obs):
        out["kept"].append(obs)
    else:
        memory.append("OBSERVATION", obs, {
            "statement": "On 2019-02..2022-02 H4 bars, 91.3% of H4 impulses (BL-H4M15-IPC-001 rule) are "
                         "followed by a qualifying pullback: the pullback filter is barely selective",
            "scope": "EXPLORATORY",
            "dataset": {"dataset_id": "MARKET_STATE_V1_436265d450475aaa", "sha256": H4_BARS_SHA,
                        "split": "outside_splits", "period": "2019-02-03..2022-02-03", "exposure": "DISCOVERY_REUSE"},
            "values": SELECTIVITY_VALUES, "evidence_level": "EXPLORATORY",
            "not_evidence_for": ["BL-H4M15-IPC-001 outcome or edge", "parameter choice",
                                 "any split of BL-01 (2022-11 onwards)"]},
            author=author, origin="HUMAN", project=PROJECT, family=FAMILY, created_at=created_at,
            provenance=[{"kind": "FILE", "ref": "server/research_datasets/market_state_v1/xauusd_h4_bars.csv",
                         "sha256": H4_BARS_SHA, "note": "structural health check run with behavior_lab_v1 detectors"}],
            relations=[{"type": "SAME_FAMILY", "target": hyp}])
        out["added"].append(obs)

    exp = "EXP-BL-01-DISCOVERY"
    if memory.get(exp):
        out["kept"].append(exp)
    else:
        memory.append("EXPERIMENT", exp, {
            "hypothesis_id": "BL-H4M15-IPC-001", "status": "NOT_RUN", "result": "NOT_AVAILABLE",
            "datasets": [{"dataset_id": DISCOVERY_DATA, "sha256": "UNVERIFIED", "split": "discovery",
                          "period": "2023-02-04..2024-08-04", "exposure": "UNSEEN"}],
            "method": {"description": "behavior_lab_v1 bl01 runner: smoke then discovery, STOP rules first",
                       "params_sha256": PARAMS_SHA, "code_commit": PREREG_COMMIT, "preregistered": True,
                       "control": "same M15 rule at other H4 closes, no H4 context",
                       "multiple_testing_family": FAMILY},
            "metrics": {}, "limits": ["tick data only on the research PC; not run from the cloud container"],
            "anomalies": [], "alternative_explanations": [], "conclusions": [], "evidence_level": "NONE_PROPOSAL",
            "decision": "PENDING"},
            author=author, origin="HUMAN", project=PROJECT, family=FAMILY, created_at=created_at,
            provenance=[{"kind": "GIT_COMMIT", "ref": PREREG_COMMIT, "note": PREREG_REF}],
            relations=[{"type": "TESTS", "target": hyp}])
        out["added"].append(exp)
    return out


def generate_alternatives(memory, *, max_per_family=6, created_at=None):
    budget = FamilyBudget(memory, max_hypotheses_per_family=max_per_family)
    obs = memory.get("OBS-BL-H4-SELECTIVITY-2019-2022")
    candidates = selectivity_alternatives("BL-H4M15", BL001_SPEC, obs)
    return register_candidates(memory, candidates, base_record="HYP-BL-H4M15-IPC-001", source_record=obs["record_id"],
                               family=FAMILY, budget=budget, author="hypothesis-generator-rules",
                               created_at=created_at)
