#!/usr/bin/env python3
"""NEXUS TASK #0006 punto 6 - genera l'istanza canonica di
OPPORTUNITY_LIFECYCLE_V1 (13 stati, transizioni fail-closed) a partire da
opportunity_lifecycle.py::build_lifecycle_definition() - stessa disciplina
di provenance/validazione di ogni altro artifact canonico del progetto."""
import os
import sys

FUNDING_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(FUNDING_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, FUNDING_DIR)
from opportunity_lifecycle import build_lifecycle_definition  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "server", "orchestrator_v1"))
from nxs_schema_validator import validate_or_raise  # noqa: E402


def main():
    payload = build_lifecycle_definition()
    schema_path = os.path.join(ROOT, "contracts", "opportunity-lifecycle.schema.json")
    import json
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    validate_or_raise(payload, schema, label="OPPORTUNITY_LIFECYCLE_V1")

    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(FUNDING_DIR, "example_instances", "opportunity_lifecycle_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} ({len(payload['states'])} stati)")


if __name__ == "__main__":
    main()
