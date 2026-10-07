import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

import company_control_plane
import strategy_registry
from business_units.ai_fashion_agency import pipeline
from business_units.ai_fashion_agency.store import AgencyStore
from executive_v1 import conversation as conv
from executive_v1.priority import InteractiveGate
from executive_v1.snapshots import SnapshotStore, diff
from executive_v1.state import ExecutiveStateBuilder, overall_progress
from jarvis_v1.local_operations import OperationsProjection
from jarvis_v1.service import JarvisService
from orchestrator_v1.nxs_schema_validator import validate

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "contracts/nexus-executive-state-v1.schema.json").read_text())


def providers(svc, agency, **overrides):
    base = {
        "version": lambda: {"git_sha": "df05c0c"},
        "ready": lambda: {"ok": True, "checks": {"database": {"ok": True, "writable": True},
                                                 "migrations": {"ok": True}}},
        "dispatcher": lambda: {"enabled": True, "running": True},
        "gateway": lambda: {"gateway_configured": True, "last_status": "ERROR",
                            "last_error": "LOCAL_WORKER_UNREACHABLE"},
        "bridge": lambda: {"configured": False, "items": []},
        "observations": lambda: {"ci": {"state": "FAILING", "failing_tests": 14},
                                 "main_head_sha": "cd4c40f"},
        "tasks": svc.queue.list_all, "queue": lambda: svc.queue,
        "revenue_operations": lambda: {"revenue_runner_enabled": False,
                                       "revenue_runner_running": False, "prospects_count": 0,
                                       "qualified_count": 0, "drafts_ready": 0,
                                       "followups_due": 0, "ventures_ready_to_test": 4,
                                       "ventures_testing": 0},
        "revenue_store": lambda: {"leads": [], "revenues": []},
        "revenue_drafts": lambda: [],
        "trading_registry": strategy_registry.all_records,
        "trading_control_plane": company_control_plane.CONTROL_PLANE.build,
        "trading_account": lambda: None, "agency_store": lambda: agency,
        "ledger_events": lambda: [],
    }
    base.update(overrides)
    return base


@pytest.fixture
def env(tmp_path):
    svc = JarvisService(queue_path=tmp_path / "q.json", ledger_path=tmp_path / "l.jsonl",
                        conversation_path=tmp_path / "c.json")
    agency = AgencyStore(tmp_path / "a.json")
    brief = pipeline.build_content_brief(agency, title="Fan Transition lookbook",
                                         content_category="fashion", hook="Four looks one fan",
                                         script="s", caption="Which? #AIcreator")
    pipeline.assign_model(agency, brief["brief_id"], model_id="MDL_LUXE_ELENA", actor="t")
    pipeline.build_generation_pack(agency, brief["brief_id"], today=date(2026, 10, 7))
    svc.set_operations_projection(OperationsProjection(
        revenue_store=None, revenue_runner=None, revenue_scheduler=None, queue=svc.queue,
        agency_store=agency))
    builder = ExecutiveStateBuilder(providers(svc, agency))
    svc.set_executive_state(builder, SnapshotStore(tmp_path / "snap.json"))
    return svc, agency, builder, tmp_path


def ask(svc, text, conversation="c1"):
    return svc.handle({"message_id": "m", "user_id": "u", "channel": "TELEGRAM",
                       "conversation_id": conversation, "timestamp": "2026-10-07T00:00:00+00:00",
                       "input_type": "TEXT", "text": text, "attachments": [], "reply_to": None,
                       "request_class": "UNKNOWN", "priority": "NORMAL", "metadata": {}})


def test_state_is_schema_valid_and_reports_real_blockers(env):
    _, _, builder, _ = env
    state = builder.build()
    assert validate(state, SCHEMA, SCHEMA) == []
    assert state["overall_status"] == "DEGRADED" and state["provider_errors"] == {}
    codes = [a["code"] for a in state["alerts"]]
    assert codes[:2] == ["CI_BLOCKING_DEPLOY", "LOCAL_WORKER_UNREACHABLE"]
    assert len(codes) == len(set(codes))  # deduplicated
    assert state["decisions_required"][0]["cost"] == {"credits": 2.25}
    assert state["system"]["key_metrics"]["deploy_behind_main"] is True


def test_no_invented_numbers(env):
    _, _, builder, _ = env
    state = builder.build()
    trading = state["trading"]["key_metrics"]
    for key in ("balance", "equity", "realized_pnl", "floating_pnl", "drawdown", "kill_switch"):
        assert trading[key] == "UNAVAILABLE"
    assert state["trading"]["key_metrics"]["live"] == 0
    assert state["revenue"]["key_metrics"]["revenue_eur"] == 0
    assert state["social"]["key_metrics"]["inbound"] == "UNAVAILABLE"
    assert state["finance"]["key_metrics"]["infrastructure_cost"] == "UNAVAILABLE"
    assert state["finance"]["key_metrics"]["local_model_cost"] == "NOT_METERED"


def test_stale_account_telemetry_is_never_shown(env):
    svc, agency, _, _ = env
    stale = {"_online": True, "_updated_ago": 7200, "balance": 1000.0, "equity": 990.0}
    state = ExecutiveStateBuilder(providers(svc, agency, trading_account=lambda: stale)).build()
    assert state["trading"]["key_metrics"]["balance"] == "UNAVAILABLE"
    fresh = {**stale, "_updated_ago": 30}
    state = ExecutiveStateBuilder(providers(svc, agency, trading_account=lambda: fresh)).build()
    assert state["trading"]["key_metrics"]["floating_pnl"] == -10.0


def test_provider_failure_is_isolated_and_cache_avoids_refetch(env):
    svc, agency, _, _ = env
    calls = []

    def boom():
        calls.append(1)
        raise RuntimeError("secret detail must not leak")
    builder = ExecutiveStateBuilder(providers(svc, agency, revenue_operations=boom))
    state = builder.build()
    builder.build()
    assert len(calls) == 1  # cached
    assert state["provider_errors"]["revenue_operations"] == "RuntimeError"
    assert state["revenue"]["status"] == "UNAVAILABLE"
    assert "secret" not in json.dumps(state)


def test_overall_progress_method_is_explicit_or_unavailable():
    sec = lambda status: {"status": status}
    known = overall_progress({"revenue": sec("FOUNDATION"), "trading": sec("PARTIAL"),
                              "ai_fashion_agency": sec("PARTIAL"), "social": sec("FOUNDATION")})
    assert known["value"] == 38 and "MATURITY_WEIGHTS" in known["method"]
    unknown = overall_progress({"revenue": sec("UNAVAILABLE"), "trading": sec("UNAVAILABLE"),
                                "ai_fashion_agency": sec("PARTIAL"), "social": sec("FOUNDATION")})
    assert unknown["value"] == "UNAVAILABLE"


@pytest.mark.parametrize("question,intent,expected", [
    ("A che punto è Nexus?", "OVERVIEW", "il deploy è bloccato da 14 failure CI"),
    ("Cosa sta funzionando e cosa no?", "WORKING_VS_NOT", "CI_BLOCKING_DEPLOY"),
    ("Come stanno andando Revenue, Trading e Agency?", "DOMAIN", "Trading (PARTIAL)"),
    ("Come vanno le revenue?", "DOMAIN", "automazione disattivata"),
    ("Cosa devo approvare?", "APPROVALS", "generazione Higgsfield per Elena per 2.25 crediti"),
    ("Qual è il problema più importante?", "TOP_PROBLEM", "CI rossa"),
    ("Quanto stiamo spendendo?", "SPEND", "Non misurati"),
    ("Cosa sta facendo Nexus?", "ACTIVITY", "modelle al lavoro: Elena"),
    ("Cosa è cambiato da ieri?", "CHANGES", "Non ho ancora uno snapshot precedente"),
])
def test_free_form_questions_answer_from_executive_state(env, question, intent, expected):
    svc = env[0]
    response = ask(svc, question)
    assert response["details"]["view"] == "EXECUTIVE_BRIEF"
    assert response["details"]["intent"] == intent
    assert expected in response["summary"]
    assert "{" not in response["summary"]  # no JSON dumps
    assert svc.queue.list_all() == []  # no task created


def test_multi_turn_domain_and_topic_followups(env):
    svc = env[0]
    ask(svc, "Come vanno le revenue?")
    trading = ask(svc, "E il trading invece?")
    assert trading["details"]["intent"] == "DOMAIN" and trading["summary"].startswith("Trading")
    ask(svc, "Qual è il problema più importante?")
    fix = ask(svc, "E possiamo risolverlo oggi?")
    assert fix["details"]["intent"] == "TOPIC_FOLLOWUP" and "CI_BLOCKING_DEPLOY" in fix["summary"]
    nxt = ask(svc, "E poi?")
    assert nxt["summary"].startswith("Poi: LOCAL_WORKER_UNREACHABLE")
    # Same elliptic phrase without executive context is not hijacked.
    fresh = ask(svc, "E possiamo risolverlo oggi?", conversation="other")
    assert (fresh.get("details") or {}).get("view") != "EXECUTIVE_BRIEF"


def test_existing_intents_keep_priority(env):
    svc = env[0]
    assert ask(svc, "/agency")["details"]["view"] == "AI_FASHION_AGENCY_STATE"
    assert ask(svc, "come va l'agenzia?", conversation="fresh")["details"]["view"] == \
        "AI_FASHION_AGENCY_STATE"
    listing = ask(svc, "quali devo approvare")
    assert "AI Fashion Agency: 1 decisioni in attesa" in listing["summary"]
    blocked = ask(svc, "Quali task sono bloccate?")
    assert blocked["details"]["view"] == "TASK_LIST"
    from jarvis_v1.service import classify
    assert classify("crea una task per analizzare il trading") == "TASK_REQUEST"


def test_analysis_requests_propose_a_draft_instead_of_creating_tasks(env):
    svc = env[0]
    response = ask(svc, "analizza quali business hanno più potenziale")
    assert "Vuoi che apra una nuova task" in response["summary"]
    assert svc.queue.list_all() == []


def test_why_question_uses_mistral_only_for_explanation(env, monkeypatch):
    svc = env[0]
    from jarvis_v1 import ministral_chat
    import executive_v1.priority as priority

    unavailable = ask(svc, "Perché le revenue stanno andando male?")
    assert unavailable["details"]["answer_source"] == "ANSWER_FROM_DOMAIN_STATE_MISTRAL_UNAVAILABLE"
    assert "0 vendite" in unavailable["summary"] and "solo i fatti" in unavailable["summary"]
    seen = {}

    def fake(prompt, history, timeout=None):
        seen["gate"] = priority.INTERACTIVE_GATE.active
        seen["prompt"] = prompt
        return {"ok": True, "reply": "Perché l'automazione è spenta e non ci sono lead."}
    monkeypatch.setattr(ministral_chat, "ask_mistral_direct", fake)
    answered = ask(svc, "Perché le revenue stanno andando male?", conversation="c2")
    assert answered["details"]["answer_source"] == "ASK_MISTRAL"
    assert seen["gate"] is True and "revenue_runner" not in answered["summary"]
    assert '"sales": 0' in seen["prompt"]  # numbers come from the state, not the model
    assert answered["summary"].startswith("Revenue (FOUNDATION)")


def test_what_changed_diff_between_snapshots(env):
    svc, agency, builder, tmp_path = env
    store = SnapshotStore(tmp_path / "s2.json", min_interval_seconds=0)
    before = builder.build(force=True)
    yesterday = datetime.now(timezone.utc) - timedelta(hours=25)
    store.record(before, now=yesterday)
    brief = pipeline.build_content_brief(agency, title="Second look", content_category="fashion",
                                         hook="Look two", script="s", caption="#AIcreator")
    pipeline.assign_model(agency, brief["brief_id"], model_id="MDL_STREET_NOVA", actor="t")
    pipeline.build_generation_pack(agency, brief["brief_id"], today=date(2026, 10, 7))
    after = ExecutiveStateBuilder(providers(svc, agency, observations=lambda: {
        "ci": {"state": "PASSING"}, "main_head_sha": "df05c0c"})).build()
    changes = diff(store.baseline(), after)
    assert any("awaiting_approval: 1 → 2" in c for c in changes["changes"])
    assert "CI_BLOCKING_DEPLOY" in changes["resolved_alerts"]
    assert any("Nova" in a for a in changes["new_approvals"])
    text = conv.changes_answer(after, changes)
    assert "risolti: CI_BLOCKING_DEPLOY" in text and "nuove decisioni" in text


def test_interactive_gate_makes_dispatcher_yield_background_work(tmp_path):
    from orchestrator_v1.core.dispatcher import DurableQueueDispatcher
    from orchestrator_v1.core.orchestrator import Orchestrator

    gate = InteractiveGate()
    orch = Orchestrator(queue_path=str(tmp_path / "q.json"), ledger_path=str(tmp_path / "l.jsonl"))
    claimed = []
    orch.queue.claim_next = lambda *a, **k: claimed.append(1)
    dispatcher = DurableQueueDispatcher(orch, yield_predicate=gate.background_should_yield)
    with gate.interactive():
        assert dispatcher.run_once() is False and claimed == []
    dispatcher.run_once()
    assert claimed == [1]  # background resumes after the interactive call
