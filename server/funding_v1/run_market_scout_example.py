"""Run one bounded local Market Scout through the canonical Orchestrator path."""
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "orchestrator_v1"))

from funding_v1.market_scout import (MarketScoutLocalHandler, codex_review_market_scout,
                                     compile_market_scout_task)
from core.orchestrator import Orchestrator
from core.task_queue import new_task_id


def run():
    prospect = {"prospect_id": "P1", "facts": ["Prospect provides local services",
                                                  "Website has no visible review follow-up"]}
    compiled = compile_market_scout_task(prospect)
    task_id = new_task_id()
    now = datetime.now(timezone.utc).isoformat()
    manifest = {
        "task_id": task_id, "title": "Bounded first-revenue market scout",
        "objective": "Classify only the supplied prospect facts", "task_type": "MAINTENANCE",
        "priority": "NORMAL", "risk_level": "A0", "scientific_risk": "NONE",
        "code_risk": "NONE", "financial_risk": "NONE",
        "required_capabilities": ["json_structured_output", "native_tool_calling"],
        "deterministic_tools_available": False, "repo_scope": "NONE", "files_allowed": [],
        "files_forbidden": ["**/*"], "dependencies": [], "blockers": [],
        "expected_artifacts": ["market_scout_draft"],
        "success_criteria": ["schema-valid grounded JSON draft"],
        "verifier": "funding_v1.market_scout.validate_market_scout_output",
        "estimated_complexity": "TRIVIAL", "estimated_runtime": "2m",
        "premium_allowed": False, "preferred_executor": "TIER1_LOCAL_CHEAP",
        "fallback_executors": ["TIER2_LOCAL_STRONG"],
        "approval_required": "REVIEW_REQUIRED",
        "created_by": "codex_first_revenue_v1", "created_at": now,
        "tenant_id": "tenant-1", "account_scope_id": None,
    }
    handler = MarketScoutLocalHandler()
    with tempfile.TemporaryDirectory(prefix="nexus-market-scout-") as temp_dir:
        root = Path(temp_dir)
        orchestrator = Orchestrator(queue_path=str(root / "queue.json"),
                                    ledger_path=str(root / "ledger.jsonl"))
        orchestrator.register_local_handler("first_revenue_market_scout", handler)
        orchestrator.submit(manifest, action="first_revenue_market_scout",
                            action_params={"prospect": prospect})
        record = orchestrator.process_task(task_id)
        events = orchestrator.ledger.read_all()
    output = handler.verified_output
    review = codex_review_market_scout(compiled, output) if output else None
    return {"task": compiled, "task_id": task_id, "state": record["state"],
            "executor": record.get("executor"), "retry_count": record.get("retry_count", 0),
            "output": output, "codex_review": review,
            "ledger_trace": [{"event_type": event["event_type"],
                              "payload": event.get("payload", {})} for event in events]}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
