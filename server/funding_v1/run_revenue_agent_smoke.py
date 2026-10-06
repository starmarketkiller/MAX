"""Real bounded local smoke for NEXUS_REVENUE_AGENT_V1; no external actions."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from funding_v1.first_revenue import FirstRevenueStore
from funding_v1.revenue_agent import RevenueAgentCoordinator
from jarvis_v1.ministral_task_compiler import decode_bounded_output
from orchestrator_v1.core.orchestrator import Orchestrator


def run():
    with tempfile.TemporaryDirectory(prefix="nexus-revenue-agent-smoke-") as tmp:
        root = Path(tmp)
        store = FirstRevenueStore(root / "revenue.json")
        orchestrator = Orchestrator(queue_path=str(root / "queue.json"),
                                    ledger_path=str(root / "ledger.jsonl"))
        coordinator = RevenueAgentCoordinator(store, orchestrator)
        context = {
            "prospect_facts": [
                "Prospect provides local services",
                "Website has no visible review follow-up",
            ],
            "offer": {"price": {"amount": 25, "currency": "EUR", "reviewed": True}},
        }
        task_id = coordinator.submit("LEAD_QUALIFICATION", context=context,
                                     references={"prospect_id": "SMOKE_1"},
                                     created_by="revenue_agent_real_smoke")
        record = orchestrator.process_task(task_id)
        artifacts = (record.get("result_packet") or {}).get("artifacts_created", [])
        return {
            "task_id": task_id,
            "state": record["state"],
            "executor": record.get("executor"),
            "retry_count": record.get("retry_count", 0),
            "premium_allowed": record["manifest"]["premium_allowed"],
            "verified_output": decode_bounded_output(artifacts),
            "verifier_errors": (record.get("result_packet") or {}).get("verifier_errors", []),
            "escalation": record.get("escalation"),
            "external_action_performed": False,
        }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
