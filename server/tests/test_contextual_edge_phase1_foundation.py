import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
FOUNDATION = ROOT / "server/research_scripts/contextual_edge_phase1"
DATASET = ROOT / "server/research_datasets/market_state_v1"


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, FOUNDATION / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_recovered_market_state_dataset_is_byte_identical_and_versioned():
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset_id"] == "MARKET_STATE_V1_436265d450475aaa"
    assert manifest["dataset_version"] == "V1_RECOVERED_BYTE_IDENTICAL"
    assert manifest["validation_integrity"] == "DISCOVERY_REUSE"
    assert manifest["source"]["raw_tick_manifest_materialized"] is False
    for filename, expected in manifest["files"].items():
        path = DATASET / filename
        assert path.exists()
        assert _sha256(path) == expected["sha256"]
        assert sum(1 for _ in path.open(encoding="utf-8")) - 1 == expected["rows"]


def test_macd_definition_is_frozen_and_causal():
    module = _load_module("phase1_macd_features", "macd_features.py")
    bars = pd.DataFrame({"close": [float(i) for i in range(1, 50)]})
    original = module.extract_macd_features(bars)
    changed = bars.copy()
    changed.loc[40:, "close"] = 1_000_000.0
    changed_features = module.extract_macd_features(changed)
    pd.testing.assert_frame_equal(original.iloc[:40], changed_features.iloc[:40])
    assert list(original.columns) == [
        "macd_main", "macd_signal", "histogram", "histogram_slope", "crossover"
    ]
    assert original["macd_signal"].iloc[:8].isna().all()


def test_macd_crossover_uses_current_and_previous_closed_bar_only():
    module = _load_module("phase1_macd_features_cross", "macd_features.py")
    bars = pd.DataFrame({"close": [100.0] * 40 + [90.0] * 10 + [120.0] * 10})
    features = module.extract_macd_features(bars)
    events = features[features["crossover"].isin(["BULLISH_CROSS", "BEARISH_CROSS"])]
    assert not events.empty
    for idx, row in events.iterrows():
        previous = features.loc[idx - 1, "histogram"]
        current = row["histogram"]
        if row["crossover"] == "BULLISH_CROSS":
            assert previous <= 0 < current
        else:
            assert previous >= 0 > current


def test_both_mt5_parity_fixtures_pass_frozen_tolerance(monkeypatch):
    features = _load_module("macd_features", "macd_features.py")
    monkeypatch.syspath_prepend(str(FOUNDATION))
    parity = _load_module("phase1_verify_macd_parity", "verify_macd_parity.py")
    report = parity.build_report()
    assert report["status"] == "MACD_PARITY_PASS"
    assert report["scientific_outcomes_read"] is False
    assert len(report["fixtures"]) == 2
    assert all(item["status"] == "PASS" for item in report["fixtures"])
    assert all(
        max(item["max_abs_error_macd_main"], item["max_abs_error_macd_signal"])
        <= features.PARITY_ABS_TOLERANCE
        for item in report["fixtures"]
    )


def test_regime_compatibility_is_outcome_blind_and_partial(monkeypatch):
    monkeypatch.syspath_prepend(str(FOUNDATION))
    module = _load_module("phase1_regime_compatibility", "compare_regime_classifiers.py")
    report = module.build_report()
    assert report["scientific_outcomes_read"] is False
    assert report["diagnostic_only"] is True
    assert report["semantic_compatibility"] == "PARTIAL"
    assert report["full_compatibility_possible"] is False
    assert report["phase1_regime_source"] == "PHASE5_5_H4_REGIME_V1"
    assert report["coverage"]["h4_rows_matched_to_d1_calendar_date"] > 0
    assert report["comparable_facets"]["n"] > 0


def test_preregistration_is_frozen_and_preserves_stage_separation():
    prereg = json.loads((FOUNDATION / "macd_preregistration_v1.json").read_text(encoding="utf-8"))
    assert prereg["status"] == "FROZEN_NOT_EXECUTED"
    assert prereg["component_scope"]["other_components_in_scope"] == []
    assert prereg["observation_unit"]["primary"] == "CAUSAL_CROSSOVER"
    assert prereg["stage_separation"]["order"] == ["DIAGNOSTIC", "SELECTION", "TEST"]
    assert prereg["execution_state"]["preregistration_frozen"] is True
    assert prereg["execution_state"]["selection_executed"] is False
    assert prereg["execution_state"]["scientific_test_executed"] is False
    assert prereg["decision_constraints"]["supported_possible_in_this_run"] is False
    assert prereg["cost_profiles"]["profiles"] == [
        "ZERO_COST", "BROKER_BASELINE", "CONSERVATIVE", "STRESS"
    ]


def test_frozen_family_and_baseline_policy_are_exact():
    prereg = json.loads((FOUNDATION / "macd_preregistration_v1.json").read_text(encoding="utf-8"))
    cells = prereg["test_family"]["cells"]
    assert len(cells) == len(set(cells)) == 60
    assert prereg["test_family"]["horizon_H4_bars"] == 40
    assert prereg["test_family"]["bh_fdr_q"] == 0.10
    assert prereg["regime"]["states_in_frozen_order"] == [
        "HIGH_VOL", "LOW_VOL", "TRANSITION", "TRENDING", "RANGING"
    ]
    assert prereg["baseline"]["match_dimensions"] == ["regime_v1", "period_bucket"]
    assert prereg["baseline"]["controls_per_event_k"] == 5
    assert prereg["baseline"]["minimum_control_pool_after_filters"] == 20
    assert prereg["baseline"]["max_control_reuse_per_run"] == 3
    assert prereg["baseline"]["within_split_only"] is True


def test_dependence_diagnostics_do_not_gate_bh_or_economic_admission():
    prereg = json.loads((FOUNDATION / "macd_preregistration_v1.json").read_text(encoding="utf-8"))
    dependence = prereg["dependence_diagnostics"]
    assert dependence["diagnostic_may_gate_p_value_or_bh"] is False
    assert dependence["ess_estimates_may_not_be_merged"] is True
    assert "primary statistical criterion" in prereg["cost_profiles"]["economic_stage_admission_rule"]
    assert prereg["cost_profiles"]["cost_results_do_not_modify_original_bh_family"] is True


def test_preregistration_hash_and_diagnostic_outcome_blindness(monkeypatch):
    monkeypatch.syspath_prepend(str(FOUNDATION))
    verifier = _load_module("phase1_prereg_verifier", "verify_macd_preregistration.py")
    result = verifier.verify()
    assert result["status"] == "PASS"
    assert result["cell_count"] == 60
    assert result["preregistration_sha256"] == result["sidecar_sha256"]
    assert all(
        item["scientific_outcomes_read"] is False
        for item in result["diagnostics"].values()
    )


def test_selection_manifest_is_frozen_outcome_blind_and_complete():
    selection = json.loads((FOUNDATION / "macd_selection_manifest_v1.json").read_text(encoding="utf-8"))
    digest = _sha256(FOUNDATION / "macd_selection_manifest_v1.json")
    sidecar = (FOUNDATION / "macd_selection_manifest_v1.sha256").read_text(encoding="ascii").split()[0]
    assert digest == sidecar == "3a70d28a56ff7f3dab2fdbe49630963d453e7bb45f1fdac20720d47ecfd6d23e"
    assert selection["status"] == "FROZEN_BEFORE_OUTCOME_TEST"
    assert selection["outcome_data_read"] is False
    assert selection["forbidden_inputs_used"] == []
    assert len(selection["cells"]) == 60
    assert selection["event_summary"]["BUY"] == selection["event_summary"]["SELL"] == 186


def test_execution_result_preserves_frozen_family_and_no_promotion(monkeypatch):
    monkeypatch.syspath_prepend(str(FOUNDATION))
    verifier = _load_module("phase1_execution_verifier", "verify_macd_execution_result.py")
    report = verifier.verify()
    assert report["status"] == "PASS"
    assert report["family_size"] == 60
    assert report["primary_cells"] == report["economic_cells"]
    result = json.loads((FOUNDATION / "macd_contextual_edge_test_result_v1.json").read_text(encoding="utf-8"))
    assert result["validation_integrity"] == "DISCOVERY_REUSE"
    assert result["summary"]["supported"] is False
    assert all(cell["bh"]["m_family"] == 60 for cell in result["cells"])
    assert all(
        cell["raw_p_value"] == 1.0
        for cell in result["cells"]
        if not cell["selection_eligible"] or cell["test_reason_codes"]
    )


def test_macd_closure_is_weak_scoped_and_registry_update_is_proposal_only():
    decision = json.loads((FOUNDATION / "macd_decision_card_v1.json").read_text(encoding="utf-8"))
    evidence = json.loads((FOUNDATION / "macd_evidence_record_v1.json").read_text(encoding="utf-8"))
    proposal = json.loads(
        (FOUNDATION / "macd_component_value_registry_proposal_v1.json").read_text(encoding="utf-8")
    )
    assert decision["decision"] == "WEAK"
    assert decision["closure_status"] == "CLOSED_WEAK"
    assert decision["automatic_registry_mutation"] is False
    observation = decision["post_hoc_observation"]
    assert observation["classification"] == "POST_HOC_OBSERVATION_NOT_CONFIRMED"
    assert observation["cell_id"] == "MACD__LOW_VOL__SELL__T1_0_ATR"
    assert observation["raw_p_value"] < 0.05
    assert observation["bh_q_value"] == 1.0
    assert evidence["post_hoc_observations"] == [observation]
    assert proposal["field"] == "component_value_status"
    assert proposal["current_value"] == "NOT_EVALUATED"
    assert proposal["proposed_value"] == "WEAK"
    assert proposal["automatic_mutation"] is False
    assert proposal["scope"]["timeframe"] == "H4"
    assert proposal["scope"]["parameters"] == {
        "fast": 12, "slow": 26, "signal": 9, "price": "PRICE_CLOSE"
    }
    assert proposal["scope"]["representation"] == "CAUSAL_CROSSOVER"
    assert "continuous MACD value" in proposal["does_not_apply_to"]
    registry = json.loads((ROOT / "contracts/edge-validation-registry.json").read_text(encoding="utf-8"))
    macd = next(item for item in registry["strategies"] if item["strategy_id"] == "MACD")
    assert macd["component_value_status"] == "NOT_EVALUATED"
