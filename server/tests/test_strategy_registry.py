import json
import re
from pathlib import Path

import pytest

import backtest
import strategy_registry


def test_registry_reconciles_live_and_research_sets():
    assert len(strategy_registry.LIVE_STRATEGY_IDS) == 38
    assert len(strategy_registry.STRATEGIES) == 42
    assert set(backtest.STRATEGIES) == set(strategy_registry.RESEARCH_STRATEGY_IDS)


def test_selector_indices_are_complete_and_unique():
    selectors = sorted(record["selector_index"] for record in strategy_registry.STRATEGIES if record["selector_index"] is not None)
    assert selectors == list(range(1, 38))


def test_live_only_gap_is_explicit():
    assert not strategy_registry.BY_ID["ELLIOTT"]["research_implementation"]
    assert not strategy_registry.BY_ID["THREE_BAR_DELIVERY_BREAK"]["research_implementation"]


def test_unknown_strategy_is_an_error():
    with pytest.raises(ValueError, match="unknown strategy_id"):
        strategy_registry.require_strategy("TYPO_STRATEGY", research=True)
    with pytest.raises(ValueError, match="unknown strategy_id"):
        backtest.run_backtest(strategy="TYPO_STRATEGY", bars=20)


def test_proxy_targets_are_canonical():
    for record in strategy_registry.STRATEGIES:
        if record["proxy_for"]:
            assert record["proxy_for"] in strategy_registry.BY_ID


def test_json_schema_declares_required_status_and_parity_enums():
    schema_path = Path(__file__).resolve().parents[2] / "contracts" / "strategy-registry.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    props = schema["properties"]["strategies"]["items"]["properties"]
    assert "RESEARCH_ONLY" in props["status"]["enum"]
    assert "PROXY" in props["research_parity"]["enum"]


def test_frontend_adapter_matches_canonical_registry():
    adapter = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "contracts" / "strategyRegistry.js").read_text(encoding="utf-8")
    adapter_ids = re.findall(r'\["([A-Z][A-Z0-9_]*)","', adapter)
    assert adapter_ids == [record["strategy_id"] for record in strategy_registry.STRATEGIES]


def test_mql_adapter_matches_canonical_live_registry():
    adapter = (Path(__file__).resolve().parents[2] / "MQL5" / "Include" / "NEXUS_v1" / "NXS_StrategyRegistry.mqh").read_text(encoding="utf-8")
    adapter_ids = re.findall(r'id=="([A-Z][A-Z0-9_]*)"', adapter)
    assert adapter_ids == list(strategy_registry.LIVE_STRATEGY_IDS)
