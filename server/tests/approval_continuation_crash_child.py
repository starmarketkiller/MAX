"""Isolated child used to stop a real process between write and finalization.

It is not a test module. The parent kills it after the ready file appears.
"""
import sys
import time
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import jarvis_v1.service as service_module
import core.ollama_worker as ollama_worker
from jarvis_v1.free_coding_worker import FreeCodingWorkerHandler
from jarvis_v1.service import JarvisService
from test_approval_continuation_v1 import SOURCE, FIXED, _approve, _patch, _plant


def main():
    root = Path(sys.argv[1])
    project = Path(sys.argv[2])
    ready = Path(sys.argv[3])

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("model call")

    ollama_worker.call_local_model = _forbidden
    service_module.is_ollama_reachable = lambda timeout=1: False
    service = JarvisService(str(root / "queue.json"), str(root / "ledger.jsonl"),
                            str(root / "conversation.json"))
    handler = FreeCodingWorkerHandler(project_root=project, workspace_root=root / "workspaces")
    service.orchestrator.register_local_handler("conversational_programming", handler)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    _plant(service, "TASK_CRASH", patch)
    original = service.queue.transition

    def _blocked(task_id, new_state, **updates):
        if new_state == "COMPLETED":
            ready.write_text("ready", encoding="utf-8")
            time.sleep(30)
        return original(task_id, new_state, **updates)

    service.queue.transition = _blocked
    _approve(service, "TASK_CRASH", patch)


if __name__ == "__main__":
    main()
