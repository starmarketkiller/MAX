"""Test di regressione per NEXUS TASK #0004 (Merge Escalation Resolution) -
complementare a verify_nexus_task_0004.py."""
import json
import os

ORCH_DIR = os.path.join(os.path.dirname(__file__), "..", "orchestrator_v1")
PHASE726_DIR = os.path.join(os.path.dirname(__file__), "..", "research_scripts", "phase7",
                          "phase7_26")


def _load(fname):
    with open(os.path.join(ORCH_DIR, fname), encoding="utf-8") as f:
        return json.load(f)


def test_final_state_completed():
    result = _load("nexus_task_0004_result_v1.json")
    assert result["final_state"] == "COMPLETED"


def test_decision_escalation_merged():
    result = _load("nexus_task_0004_result_v1.json")
    assert result["decision"] == "ESCALATION_MERGED"


def test_claude_resolution_is_field_value_not_keep_not_available():
    result = _load("nexus_task_0004_result_v1.json")
    assert result["claude_resolution"]["verdict"] == "FIELD_VALUE"
    assert result["claude_resolution"]["source_artifact"]
    assert result["claude_resolution"]["confidence"]
    assert len(result["claude_resolution"]["limitations"]) > 0


def test_order_block_exit_efficiency_now_populated():
    with open(os.path.join(PHASE726_DIR, "cross_strategy_learning_packets_v1.json"),
             encoding="utf-8") as f:
        doc = json.load(f)
    assert doc["payload"]["packets"]["ORDER_BLOCK"]["exit_efficiency"] != "NOT_AVAILABLE"


def test_all_seven_derivable_now_fields_finally_complete():
    """Chiude il ciclo NEXUS TASK #0002 -> #0003 -> #0004: tutti e 7 i campi
    originariamente classificati DERIVABLE_NOW sono ora popolati nel Vault
    canonico - zero escalation aperte residue."""
    with open(os.path.join(PHASE726_DIR, "cross_strategy_learning_packets_v1.json"),
             encoding="utf-8") as f:
        packets = json.load(f)["payload"]["packets"]
    for field in ("temporal_concentration", "exit_efficiency", "execution_degradation",
                 "favorable_before_loss", "adverse_before_win"):
        assert packets["BREAKOUT_ACC"][field] != "NOT_AVAILABLE"
    for field in ("temporal_concentration", "exit_efficiency"):
        assert packets["ORDER_BLOCK"][field] != "NOT_AVAILABLE"
