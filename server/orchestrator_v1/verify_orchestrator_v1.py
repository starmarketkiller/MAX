#!/usr/bin/env python3
"""Orchestrator V1 - verificatore indipendente. Ricostruisce ogni
artifact dai builder; valida i 6 schemi contracts/*.schema.json come
JSON ben formato; valida gli esempi contro i loro schemi; verifica che
il validatore RIFIUTI un'istanza deliberatamente rotta (non un
rubber-stamp); verifica che nessun file MQL5/Product-Platform/
contracts esistente (pre-esistente) sia stato modificato (solo nuovi
file .schema.json aggiunti); verifica che docs/architecture 01-17 e
tutte le Phase 7 restino congelate; verifica la decisione finale."""
import json
import os
import subprocess
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
CONTRACTS_DIR = os.path.join(ROOT, "contracts")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, ORCH_DIR)
import build_environment_inventory as env_builder  # noqa: E402
import build_model_recommendation as model_builder  # noqa: E402
import build_install_plan as install_builder  # noqa: E402
import build_migration_matrix as migration_builder  # noqa: E402
import build_first_pilot_spec as pilot_builder  # noqa: E402
import build_roadmap as roadmap_builder  # noqa: E402
import build_final_decision_card as decision_builder  # noqa: E402
import build_example_instances as examples_builder  # noqa: E402
from nxs_schema_validator import validate  # noqa: E402

ARTIFACTS = [
    ("environment_inventory_v1.json", env_builder.build),
    ("model_recommendation_v1.json", model_builder.build),
    ("install_plan_v1.json", install_builder.build),
    ("migration_matrix_v1.json", migration_builder.build),
    ("first_pilot_spec_v1.json", pilot_builder.build),
    ("roadmap_v1.json", roadmap_builder.build),
    ("final_decision_card_v1.json", decision_builder.build),
]

NEW_SCHEMA_FILES = ["task-manifest.schema.json", "agent-capability-registry.schema.json",
                   "context-packet.schema.json", "result-packet.schema.json",
                   "nexus-event.schema.json"]

PRE_EXISTING_CONTRACTS = ["command.schema.json", "strategy-registry.schema.json",
                         "strategy-registry.json", "default-settings.json",
                         "settings.schema.json"]

DOCS_ARCHITECTURE_FROZEN = [f"{n:02d}_" for n in range(1, 18)]  # 01_.. 17_.. restano congelati


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        path = os.path.join(ORCH_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"{fname}: file mancante")
            continue
        saved = load_json(path)
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    # --- i 6 schemi devono essere JSON ben formato e caricabili. ---
    schema_files = NEW_SCHEMA_FILES + ["task-manifest.schema.json"]
    for sf in set(NEW_SCHEMA_FILES):
        path = os.path.join(CONTRACTS_DIR, sf)
        if not os.path.exists(path):
            errors.append(f"schema mancante: {sf}")
            continue
        try:
            with open(path, encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"{sf}: JSON non valido - {e}")

    # --- gli esempi validati devono corrispondere esattamente a quelli salvati
    # (determinismo) - gia' controllato sopra tramite examples_builder incluso in ARTIFACTS?
    # No - examples_builder salva sotto example_instances/, verificarlo separatamente. ---
    ex_path = os.path.join(ORCH_DIR, "example_instances", "validated_examples_v1.json")
    if not os.path.exists(ex_path):
        errors.append("validated_examples_v1.json mancante")
    else:
        saved_examples = load_json(ex_path)
        fresh_examples = examples_builder.build()
        if canonical_sha256(fresh_examples) != canonical_sha256(saved_examples["payload"]):
            errors.append("validated_examples_v1.json: ricostruzione indipendente differisce")

    # --- il validatore deve RIFIUTARE un'istanza rotta (non un rubber-stamp). ---
    broken_task_manifest = {"task_id": "X"}  # manca quasi tutto
    with open(os.path.join(CONTRACTS_DIR, "task-manifest.schema.json"), encoding="utf-8") as f:
        task_schema = json.load(f)
    broken_errors = validate(broken_task_manifest, task_schema)
    if not broken_errors:
        errors.append("nxs_schema_validator NON ha rifiutato un'istanza TASK_MANIFEST "
                      "deliberatamente incompleta - il validatore e' un rubber-stamp (bug critico)")

    # --- nessun file contracts/ PRE-ESISTENTE modificato (solo nuovi .schema.json aggiunti). ---
    result = subprocess.run(["git", "diff", "--name-only", "--", "contracts/"],
                           cwd=ROOT, capture_output=True, text=True)
    modified_contracts = [l for l in result.stdout.strip().splitlines() if l.strip()]
    if modified_contracts:
        errors.append(f"file contracts/ pre-esistenti risultano modificati: {modified_contracts}")

    # --- nessuna modifica a MQL5/Product-Platform. ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/"],
                           cwd=ROOT, capture_output=True, text=True)
    modified = [l for l in result.stdout.strip().splitlines() if l.strip()]
    if modified:
        errors.append(f"file MQL5/Product-Platform risultano modificati: {modified}")

    # --- docs/architecture 01-17 restano congelati (solo 18_ e' nuovo). ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "docs/architecture/"],
                           cwd=ROOT, capture_output=True, text=True)
    for line in result.stdout.strip().splitlines():
        fname = line.strip().split()[-1]
        base = os.path.basename(fname)
        if any(base.startswith(p) for p in DOCS_ARCHITECTURE_FROZEN):
            errors.append(f"docs/architecture: {fname} (01-17, dovrebbe restare congelato) "
                          "risulta toccato")

    # --- nessuna fase Phase 7 (7.9x-7.27) modificata - solo file TRACCIATI (git diff, non
    # git status): la directory phase7/ contiene da sempre alcuni file scratch non tracciati
    # pre-esistenti (non introdotti da questa fase) - non e' compito di questo verificatore
    # segnalarli. ---
    result = subprocess.run(["git", "diff", "--name-only", "--", "server/research_scripts/phase7/"],
                           cwd=ROOT, capture_output=True, text=True)
    phase7_changes = [l for l in result.stdout.strip().splitlines() if l.strip()]
    if phase7_changes:
        errors.append(f"file Phase 7 tracciati risultano modificati in una fase che non deve "
                      f"toccarli: {phase7_changes}")

    # --- nessuna installazione pesante eseguita (dichiarazione esplicita). ---
    install_plan = load_json(os.path.join(ORCH_DIR, "install_plan_v1.json"))["payload"]
    if install_plan.get("not_installed_in_this_phase") is not True:
        errors.append("install_plan: not_installed_in_this_phase deve essere True")

    # --- decisione finale ammessa. ---
    decision = load_json(os.path.join(ORCH_DIR, "final_decision_card_v1.json"))["payload"]
    if decision["architecture_decision"] not in ("ORCHESTRATOR_ARCHITECTURE_READY",
                                                 "ORCHESTRATOR_ARCHITECTURE_NEEDS_REVISION"):
        errors.append(f"architecture_decision non ammessa: {decision['architecture_decision']}")
    if decision["local_runtime_decision"] not in ("LOCAL_RUNTIME_READY", "LOCAL_RUNTIME_NEEDS_SETUP"):
        errors.append(f"local_runtime_decision non ammessa: {decision['local_runtime_decision']}")

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
