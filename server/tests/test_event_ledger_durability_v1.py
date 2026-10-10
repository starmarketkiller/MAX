import json
import os
import sys

import pytest


ORCH_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "orchestrator_v1"))
sys.path.insert(0, ORCH_DIR)

from core.ledger import EventLedger, LedgerCorruptionError  # noqa: E402


def _line(event_type="TASK_CREATED", task_id="TASK_1"):
    return json.dumps({
        "event_id": "evt_test0000000001",
        "event_type": event_type,
        "task_id": task_id,
        "timestamp": "2026-10-10T00:00:00+00:00",
        "tenant_id": "default",
        "payload": {"actor": "test"},
    }).encode("utf-8")


def test_append_flushes_before_fsync(tmp_path, monkeypatch):
    path = tmp_path / "ledger.jsonl"
    observed = []

    def fake_fsync(_fd):
        observed.append(path.read_bytes())

    monkeypatch.setattr(os, "fsync", fake_fsync)
    EventLedger(path=str(path)).append("TASK_CREATED", "TASK_1", {})

    assert len(observed) == 1
    assert observed[0].endswith(b"\n")
    assert b'"event_type": "TASK_CREATED"' in observed[0]


def test_restart_ignores_only_incomplete_final_record(tmp_path):
    path = tmp_path / "ledger.jsonl"
    path.write_bytes(_line() + b"\n" + b'{"event_id":"truncated"')

    restarted = EventLedger(path=str(path))
    assert [event["event_type"] for event in restarted.read_all()] == ["TASK_CREATED"]


def test_append_repairs_incomplete_tail_and_remains_readable(tmp_path):
    path = tmp_path / "ledger.jsonl"
    path.write_bytes(_line() + b"\n" + b'{"event_id":"truncated"')

    ledger = EventLedger(path=str(path))
    ledger.append("FILE_READ", "TASK_1", {"files": ["safe.py"]})

    assert [event["event_type"] for event in ledger.read_all()] == ["TASK_CREATED", "FILE_READ"]
    assert b"truncated" not in path.read_bytes()


def test_valid_final_record_without_newline_is_preserved_on_append(tmp_path):
    path = tmp_path / "ledger.jsonl"
    path.write_bytes(_line())

    ledger = EventLedger(path=str(path))
    ledger.append("FILE_READ", "TASK_1", {"files": []})

    assert len(ledger.read_all()) == 2


@pytest.mark.parametrize("content", [
    _line() + b"\n" + b"not-json\n" + _line("FILE_READ") + b"\n",
    _line() + b"\n" + b"not-json\n",
    _line() + b"\n\n",
])
def test_complete_corruption_is_never_hidden(tmp_path, content):
    path = tmp_path / "ledger.jsonl"
    path.write_bytes(content)

    with pytest.raises(LedgerCorruptionError, match="complete record"):
        EventLedger(path=str(path)).read_all()


def test_append_does_not_hide_preexisting_intermediate_corruption(tmp_path):
    path = tmp_path / "ledger.jsonl"
    original = _line() + b"\nnot-json\n"
    path.write_bytes(original)

    ledger = EventLedger(path=str(path))
    ledger.append("FILE_READ", "TASK_1", {})

    assert path.read_bytes().startswith(original)
    with pytest.raises(LedgerCorruptionError):
        ledger.read_all()
