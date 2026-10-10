"""A torn final line must not hide earlier ledger events."""
import json

from orchestrator_v1.core.ledger import EventLedger


def test_trailing_partial_line_keeps_earlier_events(tmp_path):
    ledger = EventLedger(str(tmp_path / "event_ledger_v1.jsonl"))
    ledger.append("TOOL_USED", "TASK_ONE", {"tool": "probe"})
    with open(ledger.path, "a", encoding="utf-8") as handle:
        handle.write('{"event_id": "evt_torn", "event_type":')
        handle.flush()
    events = ledger.read_all()
    assert [event["task_id"] for event in events] == ["TASK_ONE"]


def test_corrupt_middle_line_is_not_ignored(tmp_path):
    ledger = EventLedger(str(tmp_path / "event_ledger_v1.jsonl"))
    ledger.append("TOOL_USED", "TASK_ONE", {"tool": "probe"})
    with open(ledger.path, "a", encoding="utf-8") as handle:
        handle.write("{not-json}\n")
        handle.write(json.dumps({"event_id": "evt_ok", "event_type": "TOOL_USED",
                                 "task_id": "TASK_TWO", "timestamp": "t",
                                 "tenant_id": "tenant-1", "payload": {}}) + "\n")
    try:
        ledger.read_all()
        raise AssertionError("a corrupt middle line must fail the read")
    except json.JSONDecodeError:
        pass
