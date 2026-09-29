"""Jarvis Gateway: validation boundary shared by Telegram and future clients."""
from __future__ import annotations

import json
import os
from pathlib import Path

from orchestrator_v1.nxs_schema_validator import validate

from .service import JarvisService

SERVER = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = SERVER.parent
CONTRACTS = Path(os.environ["NEXUS_CONTRACTS_DIR"]) if os.environ.get("NEXUS_CONTRACTS_DIR") else (
    SERVER / "contracts" if (SERVER / "contracts").is_dir() else REPOSITORY_ROOT / "contracts"
)
MESSAGE_SCHEMA = json.loads((CONTRACTS / "jarvis-message.schema.json").read_text(encoding="utf-8"))
RESPONSE_SCHEMA = json.loads((CONTRACTS / "jarvis-response.schema.json").read_text(encoding="utf-8"))


class JarvisGateway:
    def __init__(self, service=None): self.service = service or JarvisService()

    def handle(self, message):
        errors = validate(message, MESSAGE_SCHEMA)
        if errors: raise ValueError(f"JARVIS_MESSAGE_V1 invalid: {errors}")
        response = self.service.handle(dict(message))
        errors = validate(response, RESPONSE_SCHEMA)
        if errors: raise AssertionError(f"JARVIS_RESPONSE_V1 invalid: {errors}")
        return response
