#!/usr/bin/env python3
"""NEXUS TASK #0008 - genera l'istanza canonica di REVIEW_MATRIX_V1."""
import json
import os
import sys

REVIEW_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(REVIEW_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, REVIEW_DIR)
from review_matrix import build_review_matrix  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "server", "orchestrator_v1"))
from nxs_schema_validator import validate_or_raise  # noqa: E402


def main():
    payload = build_review_matrix()
    with open(os.path.join(ROOT, "contracts", "review-matrix.schema.json"), encoding="utf-8") as f:
        schema = json.load(f)
    validate_or_raise(payload, schema, label="REVIEW_MATRIX_V1")
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(REVIEW_DIR, "example_instances", "review_matrix_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} ({len(payload['entries'])} work_type)")


if __name__ == "__main__":
    main()
