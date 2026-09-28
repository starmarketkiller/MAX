"""Test di regressione per NEXUS TASK #0002 (Research Safety Net Auto-
Backfill). Non richiede Ollama in esecuzione (non ricontatta la rete) -
verifica solo la coerenza interna e la presenza dei file attesi,
complementare a verify_nexus_task_0002.py (che ricontrolla anche contro i
dati grezzi e lo stato reale del repository)."""
import json
import os

ORCH_DIR = os.path.join(os.path.dirname(__file__), "..", "orchestrator_v1")


def _load(fname):
    with open(os.path.join(ORCH_DIR, fname), encoding="utf-8") as f:
        return json.load(f)["payload"]


def test_final_state_is_waiting_approval_never_completed():
    result = _load("nexus_task_0002_result_v1.json")
    assert result["final_task_state"] == "WAITING_APPROVAL"


def test_changed_fields_plus_genuine_escalations_equals_seven():
    """Esito non deterministico per costruzione (LLM): il numero di campi
    DERIVABLE_NOW completati con successo in QUESTA esecuzione + il numero
    di escalation genuine deve sempre sommare a 7 (i campi classificati
    DERIVABLE_NOW) - un campo o viene completato o viene escalato, mai
    perso silenziosamente."""
    result = _load("nexus_task_0002_result_v1.json")
    assert len(result["changed_fields"]) + result["escalation_packets"]["count"] == 7


def test_decision_is_valid():
    result = _load("nexus_task_0002_result_v1.json")
    assert result["decision"] in ("SAFETY_NET_BACKFILL_COMPLETED",
                                  "SAFETY_NET_BACKFILL_COMPLETED_WITH_ESCALATIONS",
                                  "SAFETY_NET_BACKFILL_BLOCKED")


def test_premium_calls_and_cost_are_zero():
    result = _load("nexus_task_0002_result_v1.json")
    assert result["premium_calls"] == 0
    assert result["premium_cost"] == 0


def test_real_learning_packet_was_not_available_at_task_0002_time():
    """Verifica STORICA (non lo stato live del file): al momento di NEXUS TASK
    #0002 questi campi erano NOT_AVAILABLE nel file reale, che TASK #0002 non
    ha mai scritto (solo proposto) - vedi not_available_inventory nel proprio
    risultato salvato. NEXUS TASK #0003 (successiva, con approvazione
    esplicita dell'utente) ha poi legittimamente applicato questi campi al
    file reale - questo test NON deve piu' controllare lo stato live del
    file (quello e' verificato da test_nexus_task_0003.py)."""
    result = _load("nexus_task_0002_result_v1.json")
    assert "temporal_concentration" in result["not_available_inventory"]["BREAKOUT_ACC"]
    assert "exit_efficiency" in result["not_available_inventory"]["BREAKOUT_ACC"]
    assert "temporal_concentration" in result["not_available_inventory"]["ORDER_BLOCK"]


def test_proposed_update_file_changed_fields_are_subset_of_expected():
    result = _load("nexus_task_0002_result_v1.json")
    changed = {(c["strategy"], c["field"]) for c in result["changed_fields"]}
    expected = {("BREAKOUT_ACC", "temporal_concentration"),
              ("BREAKOUT_ACC", "exit_efficiency"),
              ("BREAKOUT_ACC", "execution_degradation"),
              ("BREAKOUT_ACC", "favorable_before_loss"),
              ("BREAKOUT_ACC", "adverse_before_win"),
              ("ORDER_BLOCK", "temporal_concentration"),
              ("ORDER_BLOCK", "exit_efficiency")}
    assert changed.issubset(expected)
    # i 3 campi puramente deterministici (nessun Ministral coinvolto) devono SEMPRE
    # riuscire - solo le narrative Ministral possono, in casi rari, escalare.
    assert {("BREAKOUT_ACC", "execution_degradation"), ("BREAKOUT_ACC", "favorable_before_loss"),
           ("BREAKOUT_ACC", "adverse_before_win")}.issubset(changed)


def test_provenance_map_has_entry_for_every_changed_field():
    result = _load("nexus_task_0002_result_v1.json")
    prov_keys = set(result["provenance_map"].keys())
    for c in result["changed_fields"]:
        assert f"{c['strategy']}.{c['field']}" in prov_keys


def test_classification_has_no_source_conflict_or_not_applicable():
    result = _load("nexus_task_0002_result_v1.json")
    summary = result["classification_summary"]
    assert summary["source_conflict_count"] == 0
    assert summary["not_applicable_count"] == 0


def test_coverage_report_covers_all_four_strategies():
    result = _load("nexus_task_0002_result_v1.json")
    assert set(result["coverage_report"].keys()) == {"BREAKOUT_ACC", "ORDER_BLOCK", "LIQ_SWEEP",
                                                     "TSI"}
    for strat, cov in result["coverage_report"].items():
        assert cov["coverage_after_pct"] >= cov["coverage_before_pct"]


def test_future_task_proposals_cover_tsi_and_context_tagging():
    result = _load("nexus_task_0002_result_v1.json")
    ids = {p["proposal_id"] for p in result["future_task_proposals"]}
    assert "FUTURE_TASK_TSI_CLEAN_DATASET" in ids
    assert "FUTURE_TASK_REGIME_TAGGING_PIPELINE" in ids


def test_data_exposure_safety_check_confirms_untouched():
    result = _load("nexus_task_0002_result_v1.json")
    assert result["data_exposure_safety_check"]["data_exposure_registry_modified"] is False
