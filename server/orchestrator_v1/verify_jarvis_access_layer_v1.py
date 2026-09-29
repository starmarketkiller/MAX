#!/usr/bin/env python3
"""Independent, read-only verifier for Jarvis Access Layer V1."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nxs_schema_validator import validate

ROOT = Path(__file__).resolve().parents[2]
required = [
    ROOT / "contracts/jarvis-message.schema.json",
    ROOT / "contracts/jarvis-response.schema.json",
    ROOT / "contracts/jarvis-card.schema.json",
    ROOT / "server/jarvis_v1/gateway.py",
    ROOT / "server/jarvis_v1/service.py",
    ROOT / "server/jarvis_v1/telegram_adapter.py",
]
checks = {str(path.relative_to(ROOT)): path.is_file() for path in required}
for schema in required[:3]:
    try: json.loads(schema.read_text(encoding="utf-8"))
    except Exception: checks[str(schema.relative_to(ROOT))] = False
result = {"decision": "JARVIS_ACCESS_LAYER_V1_OPERATIONAL_WITH_LIMITATIONS" if all(checks.values()) else "JARVIS_ACCESS_LAYER_V1_BLOCKED",
          "checks": checks, "limitations": ["Telegram production test requires deploy approval and configured secrets.",
          "Production SHA remains UNKNOWN until /api/version is deployed."]}
packet_path = Path(__file__).with_name("jarvis_access_layer_v1_result_packet.json")
if packet_path.is_file():
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "contracts/result-packet.schema.json").read_text(encoding="utf-8"))
    packet_errors = validate(packet, schema)
    result["result_packet_valid"] = not packet_errors
    if packet_errors:
        result["decision"] = "JARVIS_ACCESS_LAYER_V1_BLOCKED"
        result["limitations"].append(f"RESULT_PACKET invalid: {packet_errors}")
print(json.dumps(result, indent=2))
raise SystemExit(0 if all(checks.values()) and result.get("result_packet_valid", True) else 1)
