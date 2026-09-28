"""Test di regressione per il report Local Runtime Setup + First NEXUS Pilot
(server/orchestrator_v1/local_runtime_setup_report_v1.json). Non richiede
Ollama in esecuzione (non ricontatta la rete) - verifica solo la coerenza
interna e la presenza dei file attesi, complementare a verify_setup_report.py
(che invece fa anche una chiamata live a Ollama, fail-closed se non c'e')."""
import json
import os

ORCH_DIR = os.path.join(os.path.dirname(__file__), "..", "orchestrator_v1")


def _load(fname):
    with open(os.path.join(ORCH_DIR, fname), encoding="utf-8") as f:
        return json.load(f)["payload"]


def test_report_exists_and_has_valid_decision():
    payload = _load("local_runtime_setup_report_v1.json")
    assert payload["decision"] in ("LOCAL_WORKER_OPERATIONAL",
                                   "LOCAL_WORKER_OPERATIONAL_WITH_LIMITATIONS",
                                   "LOCAL_WORKER_NOT_READY")


def test_no_deploy_and_no_secrets_flags_set():
    payload = _load("local_runtime_setup_report_v1.json")
    assert payload["no_deploy"] is True
    assert payload["no_models_or_secrets_committed"] is True


def test_pilot_result_documents_failure_honestly():
    payload = _load("local_runtime_setup_report_v1.json")
    pilot = payload["pilot_result"]
    assert len(pilot["attempts_summary"]) == 4
    assert pilot["not_executed_by_claude_instead"] is True
    assert "FALLITO" in pilot["overall_result"]


def test_repo_and_vault_connectivity_documented():
    payload = _load("local_runtime_setup_report_v1.json")
    assert payload["repo_connectivity"]["no_automatic_push_during_pilot"] is True
    assert payload["vault_connectivity"]["mode"] == "READ_ONLY"


def test_benchmark_raw_files_present():
    for model_slug in ("qwen2.5-3b-instruct", "qwen2.5-7b-instruct"):
        path = os.path.join(ORCH_DIR, f"benchmark_results_{model_slug}_ctx8192_v1.json")
        assert os.path.exists(path), f"file mancante: {path}"


def test_ollama_endpoint_not_publicly_exposed_documented():
    payload = _load("local_runtime_setup_report_v1.json")
    assert payload["ollama_status"]["publicly_exposed"] is False
    assert payload["ollama_status"]["bound_to_localhost_only"] is True
