"""Fail-fast import smoke for the production dependency set."""
from __future__ import annotations

import importlib


REQUIRED_RUNTIME_MODULES = (
    "app",
    "jarvis_v1.service",
    "orchestrator_v1.core.ollama_worker",
)


def main() -> None:
    for module_name in REQUIRED_RUNTIME_MODULES:
        importlib.import_module(module_name)
    print("production imports OK:", ", ".join(REQUIRED_RUNTIME_MODULES))


if __name__ == "__main__":
    main()
