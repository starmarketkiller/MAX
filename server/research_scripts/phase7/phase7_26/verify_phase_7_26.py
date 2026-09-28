#!/usr/bin/env python3
"""Phase 7.26 - verificatore indipendente principale. Ri-deriva ogni
registry/artifact dai builder; delega a verify_leakage.py i controlli
strutturali trasversali; verifica che nessuna fase precedente (7.9x-
7.25) e nessun file MQL5/Product-Platform/contracts sia stato
modificato."""
import os
import subprocess
import sys

PHASE726_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE726_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE726_DIR)
import build_data_exposure_registry as exposure_builder  # noqa: E402
import build_experiment_registry as experiment_builder  # noqa: E402
import build_hypothesis_registry as hypothesis_builder  # noqa: E402
import build_failure_map as failure_builder  # noqa: E402
import build_cross_strategy_learning_packet as packet_builder  # noqa: E402
import build_cross_strategy_synthesis as synthesis_builder  # noqa: E402
import build_research_priority_queue as priority_builder  # noqa: E402
import build_multiple_testing_registry as mtr_builder  # noqa: E402
import verify_leakage  # noqa: E402

FROZEN_PHASE_DIRS = [f"phase7_{n}" for n in
                    ["9c", "9d", "9e", "9f", "9g", "9h", "9i", "9j", "9k", "12", "13", "14", "15",
                     "16", "17", "18", "20", "21", "22", "23", "24", "25"]]

ARTIFACTS = [
    ("data_exposure_registry_v1.json", lambda: exposure_builder.build()[0]),
    ("experiment_registry_v1.json", experiment_builder.build),
    ("hypothesis_registry_v1.json", hypothesis_builder.build),
    ("failure_map_v1.json", failure_builder.build),
    ("cross_strategy_learning_packets_v1.json", packet_builder.build),
    ("cross_strategy_synthesis_v1.json", synthesis_builder.build),
    ("research_priority_queue_v1.json", priority_builder.build),
    ("multiple_testing_registry_v1.json", mtr_builder.build),
]


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        path = os.path.join(PHASE726_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"{fname}: file mancante")
            continue
        saved = load_json(path)
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    leakage_errors = verify_leakage.verify()
    errors += [f"[leakage] {e}" for e in leakage_errors]

    for phase_dir in FROZEN_PHASE_DIRS:
        result = subprocess.run(["git", "diff", "--name-only", "--",
                                f"server/research_scripts/phase7/{phase_dir}"],
                               cwd=ROOT, capture_output=True, text=True)
        if result.stdout.strip():
            errors.append(f"{phase_dir} risulta modificato in una fase che deve lasciarlo "
                          f"congelato: {result.stdout.strip()}")

    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                            "contracts/"], cwd=ROOT, capture_output=True, text=True)
    modified = [l for l in result.stdout.strip().splitlines() if l.strip()]
    if modified:
        errors.append(f"file MQL5/Product-Platform/contracts risultano modificati: {modified}")

    # --- ogni experiment_id nel registro esperimenti deve avere un
    # hypothesis_id che esiste nel registro delle ipotesi (nessun
    # esperimento orfano). ---
    hyp_ids = {h["hypothesis_id"] for h in hypothesis_builder.build()["hypotheses"]}
    for e in experiment_builder.build()["experiments"]:
        if e["hypothesis_id"] not in hyp_ids:
            errors.append(f"esperimento {e['experiment_id']} referenzia hypothesis_id "
                          f"'{e['hypothesis_id']}' inesistente nel registro delle ipotesi")

    # --- ogni dataset_id referenziato da experiment/hypothesis registry deve
    # esistere nel data exposure registry (nessun riferimento orfano). ---
    _, by_id = exposure_builder.build()
    known_dataset_ids = set(by_id.keys())
    for e in experiment_builder.build()["experiments"]:
        if e["dataset_id"] not in known_dataset_ids:
            errors.append(f"esperimento {e['experiment_id']} referenzia dataset_id "
                          f"'{e['dataset_id']}' assente dal data exposure registry")
    for h in hypothesis_builder.build()["hypotheses"]:
        ids_to_check = [h["discovery_dataset_id"]] + h["validation_dataset_ids"]
        for did in ids_to_check:
            if did not in known_dataset_ids and not did.startswith("CROSS_STRATEGY_SYNTHESIS"):
                errors.append(f"hypothesis {h['hypothesis_id']} referenzia dataset_id '{did}' "
                              "assente dal data exposure registry")

    return errors


def main():
    errors = verify()
    if errors:
        print(f"VERIFY FAILED: {len(errors)} problemi")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("VERIFY OK: tutti i controlli indipendenti passati (0 problemi)")
    sys.exit(0)


if __name__ == "__main__":
    main()
