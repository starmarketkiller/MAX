#!/usr/bin/env python3
"""Phase 7.9I - artifact di feature engineering derivato (sola lettura
del dataset canonico 7.9H + raw data gia' congelati). Nessuna modifica
al dataset canonico, nessuna nuova esecuzione EA."""
import os
import sys

PHASE79I_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

sys.path.insert(0, PHASE79I_DIR)
import nxs_mechanism_context as ctx  # noqa: E402


def build():
    return ctx.build_feature_table()


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79I_DIR, "breakout_acc_feature_engineering_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"rows={len(payload['rows'])}")
    return doc


if __name__ == "__main__":
    main()
