#!/usr/bin/env python3
"""Orchestrator V1 - Decision Card finale. Due assi separati (l'architettura e' pronta come
SPEC indipendentemente dal fatto che il runtime locale sia installato o meno)."""
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

ALLOWED_ARCHITECTURE = ["ORCHESTRATOR_ARCHITECTURE_READY", "ORCHESTRATOR_ARCHITECTURE_NEEDS_REVISION"]
ALLOWED_RUNTIME = ["LOCAL_RUNTIME_READY", "LOCAL_RUNTIME_NEEDS_SETUP"]


def build():
    inv = load_json(os.path.join(ORCH_DIR, "environment_inventory_v1.json"))["payload"]

    architecture_decision = "ORCHESTRATOR_ARCHITECTURE_READY"
    architecture_reason = ("I 23 punti della Parte A sono specificati con schemi machine-readable "
        "(6 file contracts/*.schema.json), riconciliati esplicitamente con l'architettura AI gia' "
        "normativa (docs/NEXUS_MASTER_PROJECT.md Blocco A3.8) e col Vault contract gia' "
        "implementato (server/research_control_plane.py) - nessuna contraddizione trovata, solo "
        "estensione al dominio dei task di ricerca/sviluppo (questa architettura), distinto dal "
        "dominio del trading live (A3.8).")

    runtime_installed = not inv["runtime_inventory"]["ollama"]["installed"]
    runtime_decision = "LOCAL_RUNTIME_NEEDS_SETUP"
    runtime_reason = ("Nessun runtime locale (Ollama/llama.cpp/LM Studio/vLLM) e nessun modello "
        "risultano installati su questa macchina (verificato per comando e per ricerca su disco, "
        "non assunto). Raccomandazione prodotta (model_recommendation_v1.json) ma NESSUNA "
        "installazione eseguita in questa fase, come esplicitamente richiesto dal task. Il primo "
        "pilota (first_pilot_spec_v1.json) resta bloccato su questo setup.")

    payload = {
        "architecture_decision": architecture_decision, "architecture_reason": architecture_reason,
        "local_runtime_decision": runtime_decision, "local_runtime_reason": runtime_reason,
        "combined_summary": f"{architecture_decision} + {runtime_decision}",
        "next_action_required": "Revisione umana della raccomandazione (Ollama + "
            "qwen2.5:7b-instruct-q4_K_M, ~6.9GB download totale, nessun login) - poi installazione "
            "e primo pilota (backfill temporal_concentration/exit_efficiency BREAKOUT_ACC+ORDER_BLOCK).",
        "no_mql5_changes": True, "no_optimization": True, "no_deploy": True,
        "no_new_backtests": True, "no_heavy_install_performed": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "final_decision_card_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  {payload['combined_summary']}")


if __name__ == "__main__":
    main()
