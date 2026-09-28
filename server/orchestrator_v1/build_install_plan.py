#!/usr/bin/env python3
"""Orchestrator V1 - punto 36: install plan. SOLO pianificazione - nessuna
installazione eseguita da questo script o in questa fase."""
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def build():
    rec = load_json(os.path.join(ORCH_DIR, "model_recommendation_v1.json"))["payload"]["final_recommendation"]

    payload = {
        "already_ready": ["Python 3.12.10", "Node v24.18.0", "Git 2.55.0", "GitHub CLI 2.96.0 "
                         "(autenticato)", "Repository locale (working tree pulito, HEAD "
                         "aggiornato)"],
        "missing": ["Ollama (runtime)", f"Modello {rec['primary_local_model']}",
                   f"Modello opzionale {rec['optional_fast_model']}"],
        "steps": [
            {"step": 1, "action": "Installare Ollama per Windows (installer .exe ufficiale)",
            "login_required": False, "download_size_mb_approx": 200,
            "disk_usage_after_install_mb_approx": 700},
            {"step": 2, "action": f"ollama pull {rec['primary_local_model']}",
            "login_required": False, "download_size_gb_approx": 4.7,
            "ram_requirement_gb_approx": 5.0},
            {"step": 3, "action": f"ollama pull {rec['optional_fast_model']} (opzionale, solo se "
                                  "si conferma la strategia a due modelli dopo il pilota)",
            "login_required": False, "download_size_gb_approx": 2.0,
            "ram_requirement_gb_approx": 2.5},
        ],
        "total_disk_estimate_gb": 6.9,
        "total_download_estimate_gb": 6.9,
        "free_disk_available_gb": 279.63,
        "disk_headroom_after_install_gb_approx": 272.7,
        "no_login_required_for_any_step": True,
        "not_installed_in_this_phase": True,
        "rationale_for_deferring_install": "Il task chiede esplicitamente di completare "
            "l'inventario e produrre una raccomandazione PRIMA di installare - l'installazione "
            "effettiva e il pilota (Parte C, punto 39) sono un passo successivo, da eseguire solo "
            "dopo revisione di questa raccomandazione.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "install_plan_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
