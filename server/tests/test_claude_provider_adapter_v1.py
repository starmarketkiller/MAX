"""ClaudeProviderAdapter - the real Claude reviewer for the NEXUS Dynamic
Specialist Review. Reuses the existing production _anthropic_chat() client
(same one serving the AI Coach) rather than a second HTTP client.
"""
import json

import app as backend
from core.specialist_review import validate_rework_response
from core.provider_connector import ProviderConnectorV1, OfflineProviderAdapter

from test_dynamic_specialist_review_v1 import setup_rejected_task


REVIEW = {"problems_found": ["wrong arity"], "rework_instructions": "use two args",
         "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []}


def test_state_reflects_configuration_and_breaker(monkeypatch):
    adapter = backend.ClaudeProviderAdapter()
    monkeypatch.setattr(backend, "ANTHROPIC_API_KEY", "")
    assert adapter.state() == "OFFLINE"

    monkeypatch.setattr(backend, "ANTHROPIC_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(backend.ANTHROPIC_BREAKER, "is_open", lambda: False)
    assert adapter.state() == "AVAILABLE"

    monkeypatch.setattr(backend.ANTHROPIC_BREAKER, "is_open", lambda: True)
    assert adapter.state() == "RATE_LIMITED"


def test_invoke_returns_success_with_valid_review_json(monkeypatch):
    monkeypatch.setattr(backend, "_anthropic_chat",
                        lambda system, messages, max_tokens=1536: (json.dumps(REVIEW), None))
    adapter = backend.ClaudeProviderAdapter()
    result = adapter.invoke({"objective": "fix sample.py"}, idempotency_key="abc123", timeout_seconds=90)
    assert result.status == "SUCCESS"
    assert result.output == REVIEW
    ok, errors = validate_rework_response(result.output)
    assert ok and errors == []


def test_invoke_strips_markdown_fences(monkeypatch):
    fenced = "```json\n" + json.dumps(REVIEW) + "\n```"
    monkeypatch.setattr(backend, "_anthropic_chat", lambda *a, **k: (fenced, None))
    adapter = backend.ClaudeProviderAdapter()
    result = adapter.invoke({}, idempotency_key="k", timeout_seconds=90)
    assert result.status == "SUCCESS"
    assert result.output == REVIEW


def test_malformed_response_fails_validation_not_the_connector(monkeypatch):
    # The model ignoring instructions is a VERIFICATION_FAILED case (handled
    # by validate_rework_response, with the connector's existing bounded
    # retry) - never a transport/connector-level error of its own.
    monkeypatch.setattr(backend, "_anthropic_chat",
                        lambda *a, **k: ("Sure, here is my analysis in prose...", None))
    adapter = backend.ClaudeProviderAdapter()
    result = adapter.invoke({}, idempotency_key="k", timeout_seconds=90)
    assert result.status == "SUCCESS"  # transport worked
    ok, errors = validate_rework_response(result.output)
    assert ok is False and errors  # but the shape is rejected


def test_invoke_maps_provider_errors_to_correct_states(monkeypatch):
    adapter = backend.ClaudeProviderAdapter()
    monkeypatch.setattr(backend, "_anthropic_chat", lambda *a, **k: (None, "provider_not_configured"))
    assert adapter.invoke({}, idempotency_key="k", timeout_seconds=90).status == "OFFLINE"

    monkeypatch.setattr(backend, "_anthropic_chat", lambda *a, **k: (None, "provider_circuit_open"))
    assert adapter.invoke({}, idempotency_key="k", timeout_seconds=90).status == "RATE_LIMITED"

    monkeypatch.setattr(backend, "_anthropic_chat", lambda *a, **k: (None, "provider_timeout"))
    assert adapter.invoke({}, idempotency_key="k", timeout_seconds=90).status == "UNKNOWN"


def test_never_sends_a_prompt_that_asks_claude_to_write_or_run_code(monkeypatch):
    captured = {}
    def fake_chat(system, messages, max_tokens=1536):
        captured["system"] = system
        return json.dumps(REVIEW), None
    monkeypatch.setattr(backend, "_anthropic_chat", fake_chat)
    adapter = backend.ClaudeProviderAdapter()
    adapter.invoke({"objective": "x"}, idempotency_key="k", timeout_seconds=90)
    system = captured["system"].lower()
    assert "non scrivi mai codice" in system
    assert "non esegui mai" in system
    assert "push o deploy" in system


def test_full_reject_review_rework_cycle_with_the_real_adapter_class(tmp_path, monkeypatch):
    """Integration wiring: the exact TASK_6FEA7BDE04D2/TASK_4517052FD6EC
    scenario validated live, now through backend.ClaudeProviderAdapter
    instead of MockProviderAdapter - only _anthropic_chat (the network call)
    is mocked, nothing about the review/rework machinery itself."""
    orch, project, task_id, calls = setup_rejected_task(tmp_path, monkeypatch, patch_content="VALUE = 2\n")
    monkeypatch.setattr(backend, "ANTHROPIC_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(backend.ANTHROPIC_BREAKER, "is_open", lambda: False)
    monkeypatch.setattr(backend, "_anthropic_chat",
                        lambda system, messages, max_tokens=1536: (json.dumps({
                            "problems_found": ["wrong value"],
                            "rework_instructions": "use VALUE = 3, not 2",
                            "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []
                        }), None))
    connector = ProviderConnectorV1(orch, {"CODEX": OfflineProviderAdapter("CODEX"),
                                           "CLAUDE": backend.ClaudeProviderAdapter()})

    record = connector.request_review(task_id, "human rejected: wrong value")
    assert record["state"] == "QUEUED"  # handed back to the local worker, never completed here
    assert record["escalation"]["target"] == "CLAUDE"
    assert "use VALUE = 3" in record["action_params"]["rework_instructions"]
    events = [e["event_type"] for e in orch.ledger.read_for_task(task_id)]
    assert "REVIEW_COMPLETED" in events and "REWORK_INSTRUCTIONS_RECEIVED" in events

    record = orch.process_task(task_id)
    assert len(calls) == 2  # original local attempt + the reworked local attempt
    assert "use VALUE = 3" in calls[-1]["prompt_seen"]
    assert record["state"] == "WAITING_APPROVAL"  # back to a human, never auto-merged
    assert record["proposed_patch"]["changes"][0]["content"] == "VALUE = 2\n"
