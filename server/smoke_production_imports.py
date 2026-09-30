"""Fail-fast import smoke for the production dependency set."""
from __future__ import annotations

import importlib
import re


REQUIRED_RUNTIME_MODULES = (
    "app",
    "jarvis_v1.service",
    "orchestrator_v1.core.dispatcher",
    "orchestrator_v1.core.provider_connector",
    "orchestrator_v1.core.provider_policy",
    "orchestrator_v1.core.ollama_worker",
)


def main() -> None:
    for module_name in REQUIRED_RUNTIME_MODULES:
        importlib.import_module(module_name)
    context_packet = importlib.import_module("orchestrator_v1.core.context_packet")
    head = context_packet._current_head()
    assert re.fullmatch(r"[0-9a-f]{7,40}", head), f"invalid production build identity: {head!r}"
    print("production imports OK:", ", ".join(REQUIRED_RUNTIME_MODULES))


if __name__ == "__main__":
    main()
