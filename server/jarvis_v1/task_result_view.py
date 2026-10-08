"""Read-only projection of canonical task and child result records."""
from __future__ import annotations

from .ministral_task_compiler import BOUNDED_OUTPUT_PREFIX, decode_bounded_output


def _visible_artifacts(packet):
    return [item for item in (packet.get("artifacts_created") or [])
            if isinstance(item, str) and not item.startswith(BOUNDED_OUTPUT_PREFIX)]


def _child_result(queue, step):
    task_id = step.get("child_task_id")
    base = {"task_id": task_id, "state": step.get("state"),
            "required_capability": step.get("required_capability"),
            "selected_skill": step.get("selected_skill"),
            "selected_tool": step.get("selected_tool"),
            "selected_agent": step.get("selected_agent")}
    if not task_id:
        return {**base, "result_status": "RESULT_UNAVAILABLE", "reason": "CHILD_NOT_CREATED"}
    try:
        child = queue.get(task_id)
    except KeyError:
        return {**base, "state": "UNKNOWN", "result_status": "RESULT_UNAVAILABLE",
                "reason": "CHILD_RECORD_NOT_FOUND"}
    packet = child.get("result_packet") or {}
    output = decode_bounded_output(packet.get("artifacts_created"))
    verifier = packet.get("verifier") or {}
    bridge = child.get("local_bridge") or {}
    errors = list(verifier.get("errors") or [])
    if child.get("dispatch_last_error"):
        errors.append(child["dispatch_last_error"])
    return {**base, "state": child.get("state"), "action": child.get("action"),
            "worker": child.get("executor"),
            "transport_capability": bridge.get("capability"),
            "verifier": {"name": step.get("verifier"), "passed": verifier.get("passed"),
                         "errors": list(verifier.get("errors") or [])},
            "output": output, "artifacts": _visible_artifacts(packet), "errors": errors,
            "result_status": "AVAILABLE" if output or packet else "RESULT_UNAVAILABLE",
            "reason": None if output or packet else "RESULT_PACKET_MISSING"}


def build_task_result(queue, record):
    """Build a deterministic view; never executes or regenerates missing work."""
    packet = record.get("result_packet") or {}
    plan = record.get("multi_stage_execution") or {}
    children = [_child_result(queue, step) for step in (plan.get("steps") or [])]
    direct_output = decode_bounded_output(packet.get("artifacts_created"))
    outputs = [item["output"] for item in children if item.get("output")]
    if direct_output:
        outputs.insert(0, direct_output)
    summaries = [str(item.get("summary") or "").strip() for item in outputs
                 if str(item.get("summary") or "").strip()]
    evidence, risks = [], []
    for child in children:
        output = child.get("output") or {}
        evidence.extend({"child_task_id": child.get("task_id"), "text": finding}
                        for finding in (output.get("findings") or []))
        risks.extend({"child_task_id": child.get("task_id"), "text": risk}
                     for risk in (output.get("risks") or []))
    errors = [error for child in children for error in (child.get("errors") or [])]
    artifacts = _visible_artifacts(packet)
    for child in children:
        artifacts.extend(child.get("artifacts") or [])
    result_available = bool(packet or outputs)
    summary = " ".join(summaries)
    if not summary and result_available:
        summary = f"Task completata con decisione {packet.get('decision') or record.get('state')}."
    return {"view": "TASK_RESULT", "task_id": record.get("task_id"),
            "state": record.get("state"),
            "objective": (record.get("manifest") or {}).get("objective"),
            "result_status": "AVAILABLE" if result_available else "RESULT_UNAVAILABLE",
            "unavailable_reason": None if result_available else "RESULT_PACKET_MISSING",
            "summary": summary or "RESULT_UNAVAILABLE", "decision": packet.get("decision"),
            "verifier": packet.get("verifier") or {}, "children": children,
            "evidence": evidence, "risks": risks, "errors": errors,
            "artifacts": list(dict.fromkeys(artifacts)),
            "next_steps": packet.get("suggested_next_tasks") or [],
            "source_refs": ["orchestrator queue", "RESULT_PACKET_V1", "Activity Ledger"]}
