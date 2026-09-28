"""Test di regressione per il Local Model Bake-Off V1
(server/orchestrator_v1/bakeoff_final_report_v1.json e artifact correlati).
Non richiede Ollama in esecuzione (non ricontatta la rete) - verifica solo la
coerenza interna e la presenza dei file attesi, complementare a
verify_bakeoff.py (che ricontrolla anche contro i dati grezzi)."""
import json
import math
import os

ORCH_DIR = os.path.join(os.path.dirname(__file__), "..", "orchestrator_v1")


def _load(fname):
    with open(os.path.join(ORCH_DIR, fname), encoding="utf-8") as f:
        return json.load(f)["payload"]


def test_final_report_has_valid_decision():
    payload = _load("bakeoff_final_report_v1.json")
    assert payload["decision"] in ("LOCAL_MODEL_SELECTION_VALIDATED", "CURRENT_MODEL_REMAINS_BEST",
                                   "LOCAL_AGENT_CAPABILITY_IMPROVED_BUT_LIMITED",
                                   "INSUFFICIENT_HARDWARE_FOR_USEFUL_TIER2")


def test_no_deploy_no_strategy_no_backtest_flags():
    payload = _load("bakeoff_final_report_v1.json")
    assert payload["no_deploy"] is True
    assert payload["no_strategy_modified"] is True
    assert payload["no_backtest_run"] is True
    assert payload["no_models_secrets_credentials_committed"] is True


def test_scorecard_all_five_models_present():
    scorecard = _load("bakeoff_scorecard_v1.json")
    expected = {"qwen2.5:3b-instruct", "qwen2.5:7b-instruct", "qwen3:4b", "ministral-3:3b",
               "gemma3:4b"}
    assert set(scorecard["scorecard"].keys()) == expected


def test_qwen3_decisively_disqualified():
    scorecard = _load("bakeoff_scorecard_v1.json")
    ranked = dict(scorecard["ranked_by_weighted_score"])
    assert ranked["qwen3:4b"] < 0.6, "qwen3:4b dovrebbe avere score basso per l'88% timeout rate"


def test_pilot_v2_corrected_passes_and_documents_corrections():
    pilot = _load("pilot_run_v2_result_CORRECTED_v1.json")
    assert pilot["overall_pilot_passed"] is True
    assert len(pilot["float_comparison_corrections_applied"]) >= 1


def test_agent_capability_registry_has_two_ministral_agents():
    registry = _load("agent_capability_registry_v1.json")
    assert registry["schema_version"] == 1
    agent_ids = {a["agent_id"] for a in registry["agents"]}
    assert agent_ids == {"LOCAL_FAST_MINISTRAL3B", "LOCAL_STRONG_MINISTRAL3B"}
    for a in registry["agents"]:
        assert a["model_or_runtime"].startswith("ministral-3:3b")


def test_gemma3_no_native_tool_support_documented():
    toolcalling = _load("toolcalling_probe_results_v1.json")
    assert toolcalling["results"]["gemma3:4b"]["classification"] == "TEXT_ONLY_OR_LIMITED_AGENT_USE"


def test_raw_bakeoff_files_exist_for_all_candidates():
    for model_slug in ("qwen2.5-3b-instruct", "qwen2.5-7b-instruct", "qwen3-4b", "ministral-3-3b",
                      "gemma3-4b"):
        path = os.path.join(ORCH_DIR, f"bakeoff_results_{model_slug}_v1.json")
        assert os.path.exists(path), f"file mancante: {path}"
