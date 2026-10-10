"""Floor handoff with the Agency store attached: comply/model/style/pack run for real."""
import json

from test_floor_workflow_v1 import _context, _message, _service  # imports app (core path)
from core.dispatcher import DurableQueueDispatcher
from business_units.ai_fashion_agency.store import AgencyStore
from jarvis_v1.floor_workflow import AGENCY_STATIONS, WORKFLOW_ID, project_trace
from jarvis_v1.local_operations import OperationsProjection
from jarvis_v1.gateway import JarvisGateway


def _attach(service, tmp_path):
    store = AgencyStore(tmp_path / "agency.json")
    service.set_operations_projection(OperationsProjection(
        revenue_store=None, revenue_runner=None, revenue_scheduler=None,
        queue=service.queue, agency_store=store))
    return store


def _run(tmp_path, monkeypatch):
    service, calls = _service(tmp_path, monkeypatch)
    store = _attach(service, tmp_path)
    task_id = service.floor_workflow.submit(
        objective="internal handoff", context=_context(), created_by="jarvis:42")
    dispatcher = DurableQueueDispatcher(service.orchestrator, poll_seconds=0.05, lease_seconds=30)
    assert dispatcher.run_once() is True
    return service, store, task_id, dispatcher, calls


def test_agency_stations_run_and_stop_at_generation_approval(tmp_path, monkeypatch):
    service, store, task_id, _, _ = _run(tmp_path, monkeypatch)
    record = service.queue.get(task_id)
    assert record["state"] == "WAITING_APPROVAL"
    stations = [e["payload"]["station_id"] for e in service.ledger.read_for_task(task_id)
                if e["event_type"] in {"STEP_COMPLETED", "TASK_WAITING_APPROVAL"}
                and e["payload"].get("workflow_id") == WORKFLOW_ID]
    assert stations == [
        "jarvis.intake", "jarvis.intent", "jarvis.plan", "jarvis.orch",
        "fashion.trend", "fashion.discover", "fashion.verify", "fashion.plan",
        "fashion.comply", "fashion.model", "fashion.style", "fashion.pack",
        "fashion.handoff", "jarvis.approval",
    ]
    snap = store.snapshot()
    brief = next(b for b in snap["briefs"] if b.get("source_task_id") == task_id)
    assert brief["model_id"] == "MDL_LUXE_ELENA"  # outerwear wardrobe + fresh quote
    pack = snap["generation_packs"][0]
    assert pack["state"] == "WAITING_APPROVAL" and pack["quoted_credits"] == 2.25
    assert pack["credits_spent"] == 0
    product = snap["products"][0]
    assert product["title"] == "linen jacket" and product["status"] == "EVALUATING"
    artifacts = record["result_packet"]["artifacts_created"]
    assert any(a.startswith("agency:pack:") for a in artifacts)
    trace = project_trace(service.queue, service.ledger, owner="42")
    assert set(AGENCY_STATIONS).isdisjoint(trace["not_run"])
    assert trace["not_run_reasons"]["fashion.campaign"].startswith("commercial campaigns need")
    assert trace["not_run_reasons"]["fashion.asset"].startswith("paid Higgsfield generation")


def test_accepting_the_handoff_spends_nothing_and_does_not_rerun(tmp_path, monkeypatch):
    service, store, task_id, dispatcher, calls = _run(tmp_path, monkeypatch)
    approved = JarvisGateway(service).handle(_message(task_id, "APPROVE"))
    assert approved["status"] == "PROPOSAL_ACCEPTED"
    assert dispatcher.run_once() is False and calls["n"] == 1
    snap = store.snapshot()
    assert len(snap["briefs"]) == 1 and len(snap["generation_packs"]) == 1
    assert snap["generation_packs"][0]["state"] == "WAITING_APPROVAL"
    assert snap["costs"] == [] and snap["social_posts"] == []
    assert "AGENCY_CONTENT_PUBLISHED" not in json.dumps(snap["event_outbox"])


def test_without_agency_store_the_sequence_is_unchanged(tmp_path, monkeypatch):
    service, _ = _service(tmp_path, monkeypatch)
    task_id = service.floor_workflow.submit(
        objective="internal handoff", context=_context(), created_by="jarvis:42")
    DurableQueueDispatcher(service.orchestrator, poll_seconds=0.05, lease_seconds=30).run_once()
    trace = project_trace(service.queue, service.ledger, owner="42")
    assert set(AGENCY_STATIONS) <= set(trace["not_run"])
    assert "no Agency store attached" in trace["not_run_reasons"]["fashion.model"]
    assert trace["task_id"] == task_id
