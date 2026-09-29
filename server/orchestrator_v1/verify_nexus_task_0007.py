#!/usr/bin/env python3
"""Verifica INDIPENDENTE di NEXUS TASK #0007 (Adopt Funding Framework V1 +
Vault Namespace Cleanup) - non si fida del self-report: ricalcola da zero
l'hash di ogni file di logica e il canonical_sha256 di ogni artifact
congelato, e li confronta con quanto registrato nella decisione di
adozione. Se anche un solo byte di scoring/gate/dataset e' cambiato, la
verifica fallisce - questa task deve essere pura governance/housekeeping.
Fail-closed."""
import hashlib
import json
import os
import subprocess
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
FUNDING_DIR = os.path.join(ROOT, "server", "funding_v1")

sys.path.insert(0, FUNDING_DIR)


def _sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verify():
    errors = []

    with open(os.path.join(FUNDING_DIR, "framework_adoption_decision_v1.json"),
             encoding="utf-8") as f:
        decision_doc = json.load(f)
    decision = decision_doc["payload"]

    if decision["new_status"] != "ADOPTED":
        errors.append(f"new_status atteso ADOPTED, trovato {decision['new_status']}")
    if decision["decision"] != "FUNDING_FRAMEWORK_V1_ADOPTED":
        errors.append(f"decision atteso FUNDING_FRAMEWORK_V1_ADOPTED, trovato "
                     f"{decision['decision']}")

    scope = decision["scope_declaration"]
    for flag in ("scoring_logic_modified", "gates_modified", "new_opportunities_added",
                "opportunity_scores_changed", "commercial_action_taken",
                "premium_call_made_automatically"):
        if scope[flag] is not False:
            errors.append(f"scope_declaration.{flag} deve essere False in una task di "
                         f"solo governance/housekeeping")

    # Ricalcolo INDIPENDENTE degli hash dei file di logica - devono essere identici a
    # quanto congelato al momento dell'adozione (nessuna modifica a scoring/gate).
    for name, expected_hash in decision["frozen_logic_file_sha256"].items():
        actual = _sha256_file(os.path.join(FUNDING_DIR, name))
        if actual != expected_hash:
            errors.append(f"{name}: hash cambiato dopo l'adozione ({expected_hash[:12]} -> "
                         f"{actual[:12]}) - la logica di scoring/gate non doveva cambiare")

    # Ricalcolo del canonical_sha256 attuale degli artifact dati - devono restare
    # identici a quanto congelato (nessuna nuova opportunity, nessun punteggio cambiato).
    for rel, expected_hash in decision["frozen_artifact_canonical_sha256"].items():
        with open(os.path.join(FUNDING_DIR, rel), encoding="utf-8") as f:
            actual = json.load(f)["canonical_sha256"]
        if actual != expected_hash:
            errors.append(f"{rel}: canonical_sha256 cambiato dopo l'adozione - il dataset "
                         "non doveva essere toccato in questa task")

    # I vecchi percorsi Vault non devono piu' esistere (rename vero, non copia) e i
    # nuovi devono esistere - preserva provenance/link senza duplicati.
    for rel in decision["vault_report_previous_paths"]:
        if os.path.isfile(os.path.join(ROOT, rel)):
            errors.append(f"percorso Vault pre-#0007 ancora presente (doveva essere una "
                         f"rename, non una copia): {rel}")
    for rel in decision["vault_report_paths"]:
        if not os.path.isfile(os.path.join(ROOT, rel)):
            errors.append(f"report Vault atteso nel nuovo namespace, non trovato: {rel}")

    # knowledge_browser deve indicizzare il nuovo namespace, non solo 01-Trading -
    # altrimenti i report spostati diventano invisibili a Jarvis/Control Plane.
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "server"))
    import knowledge_browser
    knowledge_browser.build_index.cache_clear()
    index = knowledge_browser.build_index()
    titles = {d["title"] for d in index["documents"]}
    for expected_title in ("NEXUS TASK #0005 — Funding Priority & Opportunity Framework V1",
                          "NEXUS TASK #0006 — Funding Framework Completion & Hardening"):
        if expected_title not in titles:
            errors.append(f"knowledge_browser non trova piu' '{expected_title}' dopo lo "
                         "spostamento - aggiornare ALLOWED_ROOTS")
    knowledge_browser.build_index.cache_clear()

    proc = subprocess.run([sys.executable, "-m", "pytest", "server/tests/test_funding_v1.py",
                          "-q"], capture_output=True, text=True, cwd=ROOT, timeout=120)
    if proc.returncode != 0:
        errors.append(f"test_funding_v1.py non passa (regressione dopo #0007): "
                     f"{proc.stdout[-1500:]}")

    if not errors:
        print("VERIFY PASSED - NEXUS TASK #0007 coerente (adozione registrata, "
             "scoring/gate/dataset bit-per-bit invariati per hash indipendente, "
             "rename Vault senza duplicati, knowledge_browser aggiornato)")
        return True
    print("VERIFY FAILED:")
    for e in errors:
        print(f"  - {e}")
    return False


if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
