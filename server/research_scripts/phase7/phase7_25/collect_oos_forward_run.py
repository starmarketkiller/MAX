#!/usr/bin/env python3
"""Phase 7.25 - raccoglie il run OOS/forward dopo che il Tester ha
terminato (verificare esternamente via tasklist/log prima di
eseguire questo script)."""
import glob
import json
import os
import sys

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
PHASE723_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_23")
sys.path.insert(0, PHASE723_DIR)
from nxs_research_run_harness import collect_after_run  # noqa: E402

RUN_DIR = os.path.join(PHASE725_DIR, "runs", "liq_sweep_oos_forward")


def main():
    candidates = sorted(glob.glob(os.path.join(RUN_DIR, "*.manifest.json")))
    if not candidates:
        print("Nessun manifest trovato.")
        return
    manifest_path = candidates[-1]
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    manifest = collect_after_run(manifest, manifest_path)
    print(f"status: {manifest['status']}")
    print(f"trades_csv_dest: {manifest.get('trades_csv_dest')}")
    print(f"certificate_dest: {manifest.get('certificate_dest')}")
    print(f"new_certificates_detected: {manifest.get('new_certificates_detected')}")
    print(f"reconciliation: {manifest.get('reconciliation')}")
    print(f"warnings: {manifest.get('warnings')}")


if __name__ == "__main__":
    main()
