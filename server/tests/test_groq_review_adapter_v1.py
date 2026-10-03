"""GroqReviewAdapter - the FREE_ONLINE reviewer for the NEXUS Dynamic
Specialist Review. Deliberately separate from GroqEvaluationAdapterV1
(benchmark-only, never promoted to production by this class existing).
"""
import json

from jarvis_v1.free_coding_worker import FreeCodingWorkerHandler  # noqa: F401 - sets up sys.path for core.*
from core.groq_evaluation import GroqReviewAdapter
from core.provider_connector import ProviderConnectorV1, MockProviderAdapter, OfflineProviderAdapter
from core.specialist_review import validate_rework_response, REVIEWER_SYSTEM_PROMPT
from test_dynamic_specialist_review_v1 import setup_rejected_task


REVIEW = {"problems_found": ["wrong arity"], "rework_instructions": "use two args",
         "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []}


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, *, headers, payload=None, timeout=30):
        self.calls.append({"method": method, "url": url, "headers": headers, "payload": payload})
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def _chat_response(status, body, headers=None):
    return (status, headers or {}, body)


def test_state_reflects_configuration_and_model():
    assert GroqReviewAdapter(api_key="", model_id="").state() == "OFFLINE"
    assert GroqReviewAdapter(api_key="k", model_id="").state() == "OFFLINE"
    assert GroqReviewAdapter(api_key="", model_id="m").state() == "OFFLINE"
    assert GroqReviewAdapter(api_key="k", model_id="m",
                            transport=FakeTransport([])).state() == "AVAILABLE"


def test_from_environment_defaults_to_gpt_oss_120b(monkeypatch):
    monkeypatch.delenv("NEXUS_GROQ_REVIEW_MODEL", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "k")
    adapter = GroqReviewAdapter.from_environment()
    assert adapter._model_id == "openai/gpt-oss-120b"


def test_invoke_returns_success_with_valid_review_json():
    transport = FakeTransport([_chat_response(200, {
        "choices": [{"message": {"content": json.dumps(REVIEW)}}]})])
    adapter = GroqReviewAdapter(api_key="k", model_id="m", transport=transport)
    result = adapter.invoke({"objective": "fix"}, idempotency_key="abc123", timeout_seconds=90)
    assert result.status == "SUCCESS"
    assert result.output == REVIEW
    ok, errors = validate_rework_response(result.output)
    assert ok and errors == []
    assert adapter.state() == "AVAILABLE"  # a success never trips the breaker


def test_invoke_strips_markdown_fences():
    fenced = "```json\n" + json.dumps(REVIEW) + "\n```"
    transport = FakeTransport([_chat_response(200, {"choices": [{"message": {"content": fenced}}]})])
    adapter = GroqReviewAdapter(api_key="k", model_id="m", transport=transport)
    result = adapter.invoke({}, idempotency_key="k", timeout_seconds=90)
    assert result.output == REVIEW


def test_malformed_response_fails_validation_not_the_connector():
    transport = FakeTransport([_chat_response(200, {
        "choices": [{"message": {"content": "Sure, here is my analysis..."}}]})])
    adapter = GroqReviewAdapter(api_key="k", model_id="m", transport=transport)
    result = adapter.invoke({}, idempotency_key="k", timeout_seconds=90)
    assert result.status == "SUCCESS"  # transport worked
    ok, errors = validate_rework_response(result.output)
    assert ok is False and errors  # but the shape is rejected


def test_429_maps_to_rate_limited_and_opens_breaker_after_threshold():
    transport = FakeTransport([_chat_response(429, {})] * 3)
    adapter = GroqReviewAdapter(api_key="k", model_id="m", transport=transport,
                                failure_threshold=3)
    for _ in range(3):
        result = adapter.invoke({}, idempotency_key="k", timeout_seconds=90)
        assert result.status == "RATE_LIMITED"
    assert adapter.state() == "RATE_LIMITED"  # breaker open after 3 failures


def test_this_specific_account_not_seeing_the_model_is_its_own_diagnostic():
    # The user's own point: public catalog availability != this account's
    # availability. A 400/404 from Groq for an unrecognized model must be
    # distinguishable from "no quota left" (429), never conflated.
    transport = FakeTransport([_chat_response(404, {"error": {"message": "model not found"}})])
    adapter = GroqReviewAdapter(api_key="k", model_id="openai/gpt-oss-120b", transport=transport)
    result = adapter.invoke({}, idempotency_key="k", timeout_seconds=90)
    assert result.status == "UNKNOWN"
    assert result.error_class == "GROQ_HTTP_404"


def test_auth_error_maps_to_offline_not_rate_limited():
    transport = FakeTransport([_chat_response(401, {})])
    adapter = GroqReviewAdapter(api_key="bad-key", model_id="m", transport=transport)
    result = adapter.invoke({}, idempotency_key="k", timeout_seconds=90)
    assert result.status == "OFFLINE"


def test_success_resets_failure_count():
    transport = FakeTransport([
        _chat_response(429, {}), _chat_response(429, {}),
        _chat_response(200, {"choices": [{"message": {"content": json.dumps(REVIEW)}}]}),
        _chat_response(429, {}), _chat_response(429, {}),
    ])
    adapter = GroqReviewAdapter(api_key="k", model_id="m", transport=transport,
                                failure_threshold=3)
    adapter.invoke({}, idempotency_key="1", timeout_seconds=90)
    adapter.invoke({}, idempotency_key="2", timeout_seconds=90)
    adapter.invoke({}, idempotency_key="3", timeout_seconds=90)  # success resets the counter
    adapter.invoke({}, idempotency_key="4", timeout_seconds=90)
    adapter.invoke({}, idempotency_key="5", timeout_seconds=90)
    # Two more failures after the reset - still below threshold=3, not open yet.
    assert adapter.state() == "AVAILABLE"


def test_never_asks_groq_to_write_or_run_code():
    transport = FakeTransport([_chat_response(200, {
        "choices": [{"message": {"content": json.dumps(REVIEW)}}]})])
    adapter = GroqReviewAdapter(api_key="k", model_id="m", transport=transport)
    adapter.invoke({"objective": "x"}, idempotency_key="k", timeout_seconds=90)
    system_message = transport.calls[0]["payload"]["messages"][0]
    assert system_message["role"] == "system"
    assert system_message["content"] == REVIEWER_SYSTEM_PROMPT
    assert "non scrivi mai codice" in REVIEWER_SYSTEM_PROMPT.lower()


def test_full_fallback_chain_groq_unavailable_then_codex_then_claude(tmp_path, monkeypatch):
    """The exact routing requested: GROQ -> CODEX -> CLAUDE, and zero premium
    calls if an earlier candidate in the list succeeds."""
    orch, project, task_id, calls = setup_rejected_task(tmp_path, monkeypatch)
    groq = GroqReviewAdapter(api_key="", model_id="")  # not configured -> OFFLINE
    codex = MockProviderAdapter("CODEX", "AVAILABLE", result={
        "problems_found": ["x"], "rework_instructions": "fix it",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    claude = MockProviderAdapter("CLAUDE", "AVAILABLE")
    connector = ProviderConnectorV1(orch, {"GROQ": groq, "CODEX": codex, "CLAUDE": claude})

    record = connector.request_review(task_id, "human rejected")
    assert codex.calls and not claude.calls  # Groq skipped (offline), Codex used, Claude never touched
    assert record["escalation"]["target"] == "CODEX"
    assert record["state"] == "QUEUED"


def test_zero_premium_calls_when_groq_completes_the_review(tmp_path, monkeypatch):
    orch, project, task_id, calls = setup_rejected_task(tmp_path, monkeypatch)
    groq_transport = FakeTransport([_chat_response(200, {
        "choices": [{"message": {"content": json.dumps({
            "problems_found": ["wrong value"], "rework_instructions": "use VALUE = 3, not 2",
            "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})}}]})])
    groq = GroqReviewAdapter(api_key="k", model_id="openai/gpt-oss-120b", transport=groq_transport)
    codex = MockProviderAdapter("CODEX", "AVAILABLE")
    claude = MockProviderAdapter("CLAUDE", "AVAILABLE")
    connector = ProviderConnectorV1(orch, {"GROQ": groq, "CODEX": codex, "CLAUDE": claude})

    record = connector.request_review(task_id, "human rejected: wrong value")
    assert record["escalation"]["target"] == "GROQ"
    assert codex.calls == [] and claude.calls == []  # zero premium calls
    assert record["state"] == "QUEUED"
    assert "use VALUE = 3" in record["action_params"]["rework_instructions"]

    record = orch.process_task(task_id)
    assert record["state"] == "WAITING_APPROVAL"
    assert codex.calls == [] and claude.calls == []  # still zero premium after local rework
