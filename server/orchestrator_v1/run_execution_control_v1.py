"""Operator CLI for NEXUS Execution Control V1 (no external mutations)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from orchestrator_v1.core.execution_control import ExecutionControl, load_seed
from orchestrator_v1.core.shared_cognitive_state import SharedCognitiveState
from orchestrator_v1.core.task_queue import TaskQueue


HERE = Path(__file__).resolve().parent
DEFAULT_SEED = HERE / "execution_control_seed_v1.json"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("bootstrap", "report", "snapshot"))
    parser.add_argument("--state", required=True, help="Existing SharedCognitiveState JSON path")
    parser.add_argument("--seed", default=str(DEFAULT_SEED))
    parser.add_argument("--queue", help="Optional existing TaskQueue JSON path for one combined view")
    args = parser.parse_args(argv)
    queue = TaskQueue(args.queue) if args.queue else None
    control = ExecutionControl(SharedCognitiveState(args.state, task_queue=queue))
    if args.command == "bootstrap":
        control.import_seed(load_seed(args.seed))
        print(control.render_markdown(), end="")
    elif args.command == "report":
        print(control.render_markdown(), end="")
    else:
        print(json.dumps(control.report(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
