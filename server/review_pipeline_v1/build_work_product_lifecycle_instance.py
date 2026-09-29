#!/usr/bin/env python3
"""NEXUS TASK #0008 - genera l'istanza canonica del ciclo di vita
WORK_PRODUCT_V1 (11 stati, transizioni fail-closed, MAX_REVIEW_LOOPS)."""
import json
import os
import sys

REVIEW_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(REVIEW_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, REVIEW_DIR)
from work_product import build_lifecycle_definition  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "server", "orchestrator_v1"))
from nxs_schema_validator import validate_or_raise  # noqa: E402


def main():
    payload = build_lifecycle_definition()
    with open(os.path.join(ROOT, "contracts", "work-product-lifecycle.schema.json"), encoding="utf-8") as f:
        schema = json.load(f)
    validate_or_raise(payload, schema, label="WORK_PRODUCT_LIFECYCLE_V1")
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(REVIEW_DIR, "example_instances", "work_product_lifecycle_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} ({len(payload['states'])} stati)")


if __name__ == "__main__":
    main()
