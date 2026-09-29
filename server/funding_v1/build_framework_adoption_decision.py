#!/usr/bin/env python3
"""NEXUS TASK #0007 - Adopt Funding Framework V1 + Vault Namespace Cleanup.

Promuove il Funding Priority & Opportunity Framework da WAITING_APPROVAL ad
ADOPTED. Questa task e' housekeeping/governance, NON design: non tocca
scoring/pesi/gate/dataset. Per rendere quella promessa verificabile (non solo
dichiarata in prosa) questo builder congela l'hash SHA256 dei file sorgente
che contengono la logica (scoring/hard gates/capital scenarios/capability
coverage/lifecycle) e il canonical_sha256 degli artifact canonici a questo
momento - il verificatore indipendente (verify_nexus_task_0007.py) ricalcola
entrambi e li confronta, fail-closed, con quanto registrato qui."""
import hashlib
import os
import sys
from datetime import datetime, timezone

FUNDING_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(FUNDING_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

# File che contengono la LOGICA (mai gli artifact dati, quelli sono coperti da
# canonical_sha256 sotto) - devono restare bit-per-bit identici a prima di #0007.
_LOGIC_FILES = [
    "opportunity_scoring.py", "hard_gates.py", "capital_scenarios.py",
    "capability_coverage.py", "opportunity_lifecycle.py", "self_funding_loop.py",
    "opportunity_assembly.py",
]
# Artifact dati - il canonical_sha256 gia' presente nel wrapper di provenance basta,
# non serve ricalcolarlo qui: lo leggiamo e lo congeliamo cosi' com'e'.
_FROZEN_ARTIFACTS = [
    "example_instances/opportunities_v1.json",
    "opportunity_priority_queue_v1.json",
    "opportunity_briefs_v1.json",
    "example_instances/opportunity_lifecycle_v1.json",
    "example_instances/self_funding_loop_v1.json",
]

_VAULT_REPORTS = [
    "vault/02-Business/Opportunity-Funding/NEXUS TASK 0005 - Funding Priority and "
    "Opportunity Framework V1.md",
    "vault/02-Business/Opportunity-Funding/NEXUS TASK 0006 - Funding Framework "
    "Completion and Hardening.md",
]


def _sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def build():
    logic_hashes = {name: _sha256_file(os.path.join(FUNDING_DIR, name))
                    for name in _LOGIC_FILES}
    artifact_hashes = {}
    for rel in _FROZEN_ARTIFACTS:
        doc = load_json(os.path.join(FUNDING_DIR, rel))
        artifact_hashes[rel] = doc["canonical_sha256"]

    for rel in _VAULT_REPORTS:
        abs_path = os.path.join(ROOT, rel)
        if not os.path.isfile(abs_path):
            raise AssertionError(f"report vault atteso e non trovato: {rel}")

    return {
        "framework_name": "FUNDING_PRIORITY_AND_OPPORTUNITY_FRAMEWORK_V1",
        "depends_on": ["NEXUS_TASK_0005", "NEXUS_TASK_0006"],
        "this_task": "NEXUS_TASK_0007",
        "baseline_commit": "7dafeae",
        "previous_status": "WAITING_APPROVAL",
        "new_status": "ADOPTED",
        "decision": "FUNDING_FRAMEWORK_V1_ADOPTED",
        "adopted_at": datetime.now(timezone.utc).isoformat(),
        "scope_declaration": {
            "scoring_logic_modified": False,
            "gates_modified": False,
            "new_opportunities_added": False,
            "opportunity_scores_changed": False,
            "commercial_action_taken": False,
            "premium_call_made_automatically": False,
            "note": "Solo governance (promozione di stato) + housekeeping del namespace "
                   "Vault (spostamento report da 01-Trading a 02-Business/Opportunity-"
                   "Funding, con storia git preservata via rename) - nessuna logica di "
                   "scoring/gate/dataset toccata, verificato per hash indipendente.",
        },
        "frozen_logic_file_sha256": logic_hashes,
        "frozen_artifact_canonical_sha256": artifact_hashes,
        "vault_report_paths": _VAULT_REPORTS,
        "vault_report_previous_paths": [
            "vault/01-Trading/NEXUS TASK 0005 - Funding Priority and Opportunity "
            "Framework V1.md",
            "vault/01-Trading/NEXUS TASK 0006 - Funding Framework Completion and "
            "Hardening.md",
        ],
        "vault_namespace": "vault/02-Business/Opportunity-Funding/",
        "knowledge_browser_root_updated": "vault-business -> vault/02-Business",
        "next_step_note": "Uso del framework su opportunity reali - non ancora una NEXUS "
                         "TASK, richiede scelta esplicita dell'utente su quale opportunity "
                         "validare per prima e resta comunque soggetto ad approval prima "
                         "di qualunque azione commerciale reale.",
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(FUNDING_DIR, "framework_adoption_decision_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path}")
    print(f"  {payload['previous_status']} -> {payload['new_status']} "
         f"({payload['decision']})")


if __name__ == "__main__":
    main()
