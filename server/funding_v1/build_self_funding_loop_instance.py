#!/usr/bin/env python3
"""NEXUS TASK #0006 punto 8 - genera l'istanza canonica di
SELF_FUNDING_LOOP_V1 (struttura di allocazione futura, MAI un forecast di
revenue) a partire da self_funding_loop.py::build_self_funding_loop()."""
import os
import sys

FUNDING_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(FUNDING_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, FUNDING_DIR)
from self_funding_loop import build_self_funding_loop  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "server", "orchestrator_v1"))
from nxs_schema_validator import validate_or_raise  # noqa: E402


def main():
    payload = build_self_funding_loop()
    schema_path = os.path.join(ROOT, "contracts", "self-funding-loop.schema.json")
    import json
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    validate_or_raise(payload, schema, label="SELF_FUNDING_LOOP_V1")

    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(FUNDING_DIR, "example_instances", "self_funding_loop_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} ({len(payload['stages'])} stage)")


if __name__ == "__main__":
    main()
