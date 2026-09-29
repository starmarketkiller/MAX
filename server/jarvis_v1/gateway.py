"""Jarvis Gateway: validation boundary shared by Telegram and future clients."""
from __future__ import annotations

import json

from orchestrator_v1.nxs_schema_validator import validate
from path_resolver import resolve_contracts_dir

from .service import JarvisService

CONTRACTS = resolve_contracts_dir(__file__)
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
