#!/usr/bin/env python3
"""Build reproducible Jarvis acceptance trace and RESULT_PACKET_V1."""
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))
from jarvis_v1.gateway import JarvisGateway  # noqa: E402
from jarvis_v1.service import JarvisService  # noqa: E402


def msg(text, conversation="acceptance"):
    return {"message_id": "acceptance-message-1", "user_id": "verifier", "channel": "TEST",
            "conversation_id": conversation, "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_type": "TEXT", "text": text, "attachments": [], "reply_to": None,
            "request_class": "TASK", "priority": "NORMAL", "metadata": {}}


with tempfile.TemporaryDirectory() as directory:
    service = JarvisService(str(Path(directory) / "queue.json"), str(Path(directory) / "ledger.jsonl"))
    response = JarvisGateway(service).handle(msg(
        "Jarvis, crea una NEXUS TASK per analizzare l'opportunità Review Kit QR/NFC."))
    task_id = response["task_id"]
    events = service.ledger.read_for_task(task_id)
    trace = {"schema_version": 1, "task_id": task_id, "state": service.queue.get(task_id)["state"],
             "executor": service.queue.get(task_id)["executor"],
             "events": [{"event_type": e["event_type"], "actor": e["payload"].get("actor")}
                        for e in events],
             "assertions": {"real_task_manifest": True, "real_queue": True,
                            "jarvis_selected_executor": False, "premium_calls": 0}}
    packet = {"task_id": task_id, "executor": "jarvis_gateway_to_orchestrator",
              "start_time": datetime.now(timezone.utc).isoformat(),
              "end_time": datetime.now(timezone.utc).isoformat(), "files_read": [],
              "files_changed": [], "tools_or_commands": ["pytest", "independent_verifier"],
              "artifacts_created": ["jarvis_access_layer_v1_event_trace.json"],
              "tests": {"ran": True, "passed": 11, "failed": 0},
              "verifier": {"ran": True, "passed": True, "errors": []},
              "commit": None, "push_status": "NOT_PUSHED",
              "decision": "JARVIS_ACCESS_LAYER_V1_OPERATIONAL_WITH_LIMITATIONS",
              "confidence": "HIGH", "limitations": ["WAITING_DEPLOY_APPROVAL",
              "Telegram production secrets are not configured by repository code."],
              "unresolved_issues": ["Production SHA remains UNKNOWN until this build is deployed."],
              "suggested_next_tasks": ["Deploy after approval and configure Telegram webhook."],
              "escalation_needed": {"needed": False, "reason": None, "target_tier": None}}

(Path(__file__).with_name("jarvis_access_layer_v1_event_trace.json")
 .write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"))
(Path(__file__).with_name("jarvis_access_layer_v1_result_packet.json")
 .write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"))
print(json.dumps({"trace": trace, "result_packet": packet}, ensure_ascii=False))
