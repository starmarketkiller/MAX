"""Test di regressione per NEXUS TASK #0003 (Approve Safety Net Backfill).
Non richiede Ollama (nessuna chiamata al modello in questa task) -
complementare a verify_nexus_task_0003.py (che ricontrolla anche contro i
dati grezzi e lo stato reale del repository)."""
import json
import os

ORCH_DIR = os.path.join(os.path.dirname(__file__), "..", "orchestrator_v1")
PHASE726_DIR = os.path.join(os.path.dirname(__file__), "..", "research_scripts", "phase7",
                          "phase7_26")


def _load(fname):
    with open(os.path.join(ORCH_DIR, fname), encoding="utf-8") as f:
        return json.load(f)


def test_final_state_completed():
    result = _load("nexus_task_0003_result_v1.json")
    assert result["final_state"] == "COMPLETED"


def test_decision_approved_and_applied():
    result = _load("nexus_task_0003_result_v1.json")
    assert result["decision"] == "BACKFILL_APPROVED_AND_APPLIED"


def test_premium_zero():
    result = _load("nexus_task_0003_result_v1.json")
    assert result["premium_calls"] == 0
    assert result["premium_cost"] == 0


def test_order_block_exit_efficiency_untouched():
    with open(os.path.join(PHASE726_DIR, "cross_strategy_learning_packets_v1.json"),
             encoding="utf-8") as f:
        doc = json.load(f)
    assert doc["payload"]["packets"]["ORDER_BLOCK"]["exit_efficiency"] == "NOT_AVAILABLE"


def test_breakout_acc_fields_populated():
    with open(os.path.join(PHASE726_DIR, "cross_strategy_learning_packets_v1.json"),
             encoding="utf-8") as f:
        doc = json.load(f)
    ba = doc["payload"]["packets"]["BREAKOUT_ACC"]
    for field in ("temporal_concentration", "exit_efficiency", "execution_degradation",
                 "favorable_before_loss", "adverse_before_win"):
        assert ba[field] != "NOT_AVAILABLE", f"{field} dovrebbe essere popolato"


def test_confidence_high():
    result = _load("nexus_task_0003_result_v1.json")
    assert result["result_packet"]["confidence"] == "HIGH"
