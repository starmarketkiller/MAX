import json

import projection_freshness as pf
import strategy_pipeline_read_model as sp


def _by_id(model):
    return {item["strategy_id"]: item for item in model["items"]}


def test_breakout_is_stale_without_ingesting_newer_scientific_state():
    model = sp.StrategyPipelineCatalog().build()
    breakout = _by_id(model)["BREAKOUT_ACC"]
    freshness = breakout["projection_freshness"]
    assert freshness["freshness_status"] == "STALE"
    assert freshness["canonical_latest_phase"] == "7.9F"
    assert freshness["projected_latest_phase"] == "7.9B"
    assert freshness["provenance"]["canonical_sha256"]
    # The scientific projection remains the explicit 7.9B state.
    assert breakout["research_readiness"] == "HOLD_NEEDS_MORE_EVIDENCE"
    assert breakout["formalization_verdict"] == "FULL_STRATEGY_SPEC_VERIFIED"
    assert not any("final_verdict" in key for key in breakout)


def test_volbrk_is_current_and_scientific_counts_do_not_change():
    model = sp.StrategyPipelineCatalog().build()
    volbrk = _by_id(model)["VOLATILITY_BREAKOUT_CONFIRMED"]
    freshness = volbrk["projection_freshness"]
    assert freshness["freshness_status"] == "CURRENT"
    assert freshness["canonical_latest_phase"] == freshness["projected_latest_phase"] == "7.9A"
    assert volbrk["research_readiness"] == "REFUTED_ARCHIVED"
    assert model["meta_filter_ready_count"] == 0
    assert model["execution_candidate_count"] == 0
    assert model["deployable_count"] == 0


def test_missing_or_malformed_latest_source_yields_unknown(monkeypatch, tmp_path):
    malformed = tmp_path / "breakout_acc_identity_adjudication_v1.json"
    malformed.write_text("{bad", encoding="utf-8")
    sources = tuple({**source, "path": malformed} if source["phase"] == "7.9F" else source for source in pf.CANONICAL_SOURCES)
    monkeypatch.setattr(pf, "CANONICAL_SOURCES", sources)
    model = sp.StrategyPipelineCatalog().build()
    breakout = _by_id(model)["BREAKOUT_ACC"]
    assert breakout["projection_freshness"]["freshness_status"] == "UNKNOWN"
    assert any(warning["scope"] == "FRESHNESS" for warning in model["warnings"])
    assert model["count"] == 7


def test_freshness_output_is_deterministic_and_provenance_only():
    first = sp.StrategyPipelineCatalog().build()["freshness"]
    second = sp.StrategyPipelineCatalog().build()["freshness"]
    assert first["items"] == second["items"]
    assert first["latest_canonical_phase"] == "7.9F"
    assert first["latest_projection_phase"] == "7.9B"
    assert all(item["blocking_or_informational"] == "INFORMATIONAL" for item in first["items"])
    assert "profit" not in json.dumps(first).lower()
