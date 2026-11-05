"""T01 anchored local cycle.

The configured local model stays ministral-3:3b. NEXUS_PROBE_LOCAL_MODEL can
name another entry of KNOWN_MODELS for one process. An unknown name fails
before any model call and is not replaced. The live generation is a separate
probe; these tests plant worker text only to exercise the canonical verifier.
"""
import base64
import hashlib
import json

import pytest

from jarvis_v1 import ministral_task_compiler as compiler
from jarvis_v1.service import JarvisService

from core import ollama_worker


HEAD = "76a5dfb0d9a2ec40fe8ed25bcf1780ae8ded08c5"
SECRET = "PROBE_SECRET_TOKEN_t01"
COMPLETE = (
    b'{"records":[{"id":"E1","kind":"timeout","detail":"gateway closed after 30s"},'
    b'{"id":"E2","kind":"missing_field","detail":"account_id absent"}],'
    b'"required":["fill_price"]}'
)
INCOMPLETE = b'{"note":"partial"}'


def _service(tmp_path, monkeypatch):
    monkeypatch.delenv(ollama_worker.PROBE_MODEL_ENV, raising=False)
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    return JarvisService(str(tmp_path / "q.json"), str(tmp_path / "l.jsonl"), str(tmp_path / "c.json"))


def _plant(monkeypatch, text):
    calls = []

    def invoke(prompt, model, json_mode=False, ensure_single_resident=True):
        calls.append({"prompt": prompt, "model": model, "json_mode": json_mode,
                      "ensure_single_resident": ensure_single_resident})
        return {"success": True, "model": model, "response_text": text,
                "error": None, "wall_seconds": 0.01}

    monkeypatch.setattr("core.orchestrator.ollama_worker.call_local_model", invoke)
    return calls


def _delegate(svc, raw, name):
    return svc.delegate_to_ministral(
        "anchored_failure_report_v1",
        goal="Classifica il documento e dichiara i dati assenti.",
        relevant_paths=[name], input_bytes=raw, input_name=name, current_head=HEAD)


def test_unset_override_preserves_ministral(monkeypatch):
    monkeypatch.delenv(ollama_worker.PROBE_MODEL_ENV, raising=False)
    model, error = ollama_worker.resolve_model("ministral-3:3b")
    assert model == "ministral-3:3b"
    assert error is None
    assert ollama_worker.DEFAULT_MODEL == "ministral-3:3b"


def test_known_override_is_explicit(monkeypatch):
    monkeypatch.setenv(ollama_worker.PROBE_MODEL_ENV, "qwen2.5:3b-instruct")
    model, error = ollama_worker.resolve_model("ministral-3:3b")
    assert model == "qwen2.5:3b-instruct"
    assert error is None


def test_unknown_override_fails_closed_without_a_call(tmp_path, monkeypatch):
    svc = _service(tmp_path, monkeypatch)
    monkeypatch.setenv(ollama_worker.PROBE_MODEL_ENV, "llama3:8b")
    calls = _plant(monkeypatch, "{}")
    task_id = _delegate(svc, COMPLETE, "input.json")
    record = svc.orchestrator.process_task(task_id)
    assert calls == []
    assert record["state"] == "FAILED"
    assert record["dispatch_last_error"].startswith("NEXUS_PROBE_LOCAL_MODEL=")
    events = [row for row in svc.ledger.read_all() if row["task_id"] == task_id]
    assert any(row["event_type"] == "TASK_FAILED"
               and row["payload"]["reason"] == "LOCAL_MODEL_OVERRIDE_REJECTED" for row in events)


def test_context_packet_carries_the_input_hash_and_excludes_the_secret(tmp_path, monkeypatch):
    svc = _service(tmp_path, monkeypatch)
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "input.json").write_bytes(COMPLETE)
    (fixture / "side.secret").write_text(SECRET, encoding="utf-8")
    svc.orchestrator.local_handlers["anchored_failure_report_v1"].project_root = fixture
    calls = _plant(monkeypatch, json.dumps({
        "classification": "timeout", "cited_ids": ["E1", "E2"], "missing": ["fill_price"],
    }))
    task_id = _delegate(svc, COMPLETE, "input.json")
    record = svc.orchestrator.process_task(task_id)
    packet = record["action_params"]["context_packet"]
    digest = record["action_params"]["deterministic_inventory"]["input_sha256"]
    assert packet["canonical_artifacts"][0]["canonical_sha256"] == digest
    assert packet["canonical_artifacts"][0]["source_artifact"] == "input.json"
    assert packet["allowed_files"] == ["input.json"]
    assert packet["current_head"] == HEAD
    blob = json.dumps({"prompt": calls[0]["prompt"], "packet": packet, "result": record["result_packet"]})
    assert SECRET not in blob
    assert 'cited_ids=["E1", "E2"]' in calls[0]["prompt"]
    assert calls[0]["model"] == "ministral-3:3b"
    assert calls[0]["json_mode"] is True
    assert record["state"] == "COMPLETED"
    persisted = "\n".join(record["result_packet"]["artifacts_created"])
    assert "deterministic_inventory_v1:" in persisted
    assert '"count": 2' in persisted
    assert digest in persisted


def test_incomplete_input_must_be_admitted(tmp_path, monkeypatch):
    svc = _service(tmp_path, monkeypatch)
    calls = _plant(monkeypatch, json.dumps({
        "classification": "insufficient", "cited_ids": [], "missing": ["records"],
    }))
    task_id = _delegate(svc, INCOMPLETE, "partial.json")
    record = svc.orchestrator.process_task(task_id)
    assert record["state"] == "COMPLETED"
    assert calls[0]["prompt"].count("insufficient") >= 1
    assert '"cited_ids": []' in calls[0]["prompt"] or "cited_ids=[]" in calls[0]["prompt"]
    decoded = compiler.decode_bounded_output(record["result_packet"]["artifacts_created"])
    assert decoded["classification"] == "insufficient"
    assert decoded["missing"] == ["records"]


def test_factual_answer_without_summary_is_accepted(tmp_path, monkeypatch):
    svc = _service(tmp_path, monkeypatch)
    _plant(monkeypatch, json.dumps({
        "classification": "timeout", "cited_ids": ["E1", "E2"], "missing": ["fill_price"],
    }))
    task_id = _delegate(svc, COMPLETE, "input.json")
    record = svc.orchestrator.process_task(task_id)
    assert record["state"] == "COMPLETED"
    decoded = compiler.decode_bounded_output(record["result_packet"]["artifacts_created"])
    assert decoded["cited_ids"] == ["E1", "E2"]
    assert decoded["missing"] == ["fill_price"]


def test_authorized_snapshot_ignores_a_changed_disk_file(tmp_path, monkeypatch):
    svc = _service(tmp_path, monkeypatch)
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    disk = fixture / "input.json"
    disk.write_bytes(b'{"records":[{"id":"E7","kind":"other","detail":"DISK_BEFORE_DELEGATE"}]}')
    svc.orchestrator.local_handlers["anchored_failure_report_v1"].project_root = fixture
    calls = _plant(monkeypatch, json.dumps({
        "classification": "timeout", "cited_ids": ["E1", "E2"], "missing": ["fill_price"],
    }))
    task_id = _delegate(svc, COMPLETE, "input.json")
    disk.write_bytes(b'{"records":[{"id":"E8","kind":"other","detail":"DISK_AFTER_DELEGATE"}]}')
    record = svc.orchestrator.process_task(task_id)
    prompt = calls[0]["prompt"]
    document = prompt.split("--- input.json ---\n", 1)[1].split("\n\nFATTI DETERMINISTICI", 1)[0]
    digest = hashlib.sha256(COMPLETE).hexdigest()
    inventory = record["action_params"]["deterministic_inventory"]
    assert document.encode("utf-8") == COMPLETE
    assert inventory["input_sha256"] == digest
    assert inventory["ids"] == ["E1", "E2"]
    assert record["action_params"]["context_packet"]["canonical_artifacts"][0]["canonical_sha256"] == digest
    assert "DISK_BEFORE_DELEGATE" not in prompt
    assert "DISK_AFTER_DELEGATE" not in prompt
    assert record["state"] == "COMPLETED"


def test_tampered_snapshot_fails_before_the_model(tmp_path, monkeypatch):
    svc = _service(tmp_path, monkeypatch)
    calls = _plant(monkeypatch, "{}")
    task_id = _delegate(svc, COMPLETE, "input.json")
    params = dict(svc.queue.get(task_id)["action_params"])
    params["authorized_snapshot_b64"] = base64.b64encode(
        b'{"records":[{"id":"E8","kind":"other","detail":"DISK_AFTER_DELEGATE"}]}').decode()
    svc.queue.annotate(task_id, action_params=params)
    record = svc.orchestrator.process_task(task_id)
    assert calls == []
    assert record["state"] == "FAILED"
    assert "authorized snapshot" in record["dispatch_last_error"]
    events = [row for row in svc.ledger.read_all() if row["task_id"] == task_id]
    assert any(row["payload"].get("reason") == "SNAPSHOT_MISMATCH" for row in events)


def test_false_summary_is_rejected(tmp_path, monkeypatch):
    svc = _service(tmp_path, monkeypatch)
    _plant(monkeypatch, json.dumps({
        "classification": "timeout", "cited_ids": ["E1", "E2"], "missing": ["fill_price"],
        "summary": "E1 e E2 descrivono un ordine eseguito a prezzo 100.",
    }))
    task_id = _delegate(svc, COMPLETE, "input.json")
    record = svc.orchestrator.process_task(task_id)
    assert record["state"] != "COMPLETED"
    failed = [row for row in svc.ledger.read_all()
              if row["task_id"] == task_id and row["event_type"] == "TEST_FAILED"]
    assert failed
    assert any("free prose" in error for error in failed[0]["payload"]["errors"])


def test_invented_id_is_rejected_and_not_accepted(tmp_path, monkeypatch):
    svc = _service(tmp_path, monkeypatch)
    _plant(monkeypatch, json.dumps({
        "classification": "timeout", "cited_ids": ["E999"], "missing": ["fill_price"],
    }))
    task_id = _delegate(svc, COMPLETE, "input.json")
    record = svc.orchestrator.process_task(task_id)
    assert record["state"] != "COMPLETED"
    assert record.get("result_packet", {}).get("decision") != "COMPLETED"


def test_anchored_template_requires_the_input():
    with pytest.raises(ValueError):
        compiler.attach_input_provenance({}, source_name="input.json", raw=COMPLETE, current_head="HEAD")
