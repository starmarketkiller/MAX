#!/usr/bin/env python3
"""Phase 7.25 punto 10 - lancia il run OOS/forward dedicato per
LIQ_SWEEP, finestra genuinamente untouched 2026.07.01-2026.09.27 (mai
attraversata da nessun run/analisi precedente - vedi
data_exposure_map_v1.json), usando l'harness di isolamento di Phase
7.23 (stessa identita' canonica: selettore 7, GOLD, H4, lotto fisso
0.01)."""
import os
import sys

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
PHASE723_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_23")
sys.path.insert(0, PHASE723_DIR)
from nxs_research_run_harness import build_ini, launch  # noqa: E402

RUN_DIR = os.path.join(PHASE725_DIR, "runs", "liq_sweep_oos_forward")


def main():
    manifest, manifest_path, ini_path = build_ini(
        run_dir=RUN_DIR, strategy_identity="LIQ_SWEEP", selector=7, symbol="GOLD",
        period=("2026.07.01", "2026.09.27"), chart_period="H4", fixed_lot=0.01, leverage=100)
    print(f"run_id: {manifest['run_id']}")
    print(f"ini: {ini_path}")
    manifest = launch(manifest, manifest_path)
    print("Tester lanciato. Attendere il completamento (verificare tramite tasklist/log), poi "
         "eseguire collect_oos_forward_run.py.")
    print(f"manifest_path: {manifest_path}")


if __name__ == "__main__":
    main()
