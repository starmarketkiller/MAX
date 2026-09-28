#!/usr/bin/env python3
"""Orchestrator V1 - Parte B, punti 24-28: inventario hardware/runtime/
modelli/repo/connettivita' rilevato DIRETTAMENTE su questa macchina
(comandi eseguiti in sessione, non stimati). Nessun software installato
da questo script - solo lettura. I valori sotto sono stati misurati
tramite PowerShell/Bash in questa stessa sessione (systeminfo, WMI/CIM,
`command -v`, ricerca file su disco, `gh auth status`, `git remote`) -
non rieseguibile automaticamente in futuro senza rieseguire quei
comandi (l'hardware/i runtime possono cambiare)."""
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    payload = {
        "measured_at_utc": "2026-09-28 (sessione corrente)",
        "measurement_method": "Comandi eseguiti direttamente in questa sessione (PowerShell CIM/"
            "WMI, Bash command -v, ricerca file su disco, gh auth status, git remote) - non uno "
            "score/stima, valori osservati.",
        "hardware": {
            "os": "Microsoft Windows 11 Pro, build 10.0.26100, 64-bit",
            "cpu": "Intel(R) Core(TM) i5-7200U CPU @ 2.50GHz (Kaby Lake, 2017) - 2 core fisici, "
                  "4 thread logici, clock max ~2.71GHz",
            "ram_total_gb": 19.85, "ram_free_gb_at_measurement": 9.01,
            "gpu": "Intel(R) HD Graphics 620 (integrata, condivisa con la RAM di sistema - "
                  "AdapterRAM riportato 1GB e' allocazione condivisa, NON VRAM dedicata)",
            "gpu_acceleration_available": "NESSUNA accelerazione GPU praticabile per inferenza LLM "
                "(nessuna CUDA/ROCm, Intel HD 620 non ha un percorso maturo/veloce per inferenza "
                "quantizzata via llama.cpp/Ollama su Windows) - CPU-only e' l'unico percorso "
                "realistico.",
            "npu": "Nessuna NPU rilevata.",
            "disk_free_gb": 279.63, "disk_total_gb": 476.84,
            "constraint_summary": "Hardware GENUINAMENTE limitato per LLM locali: CPU mobile "
                "dual-core del 2017, nessuna GPU utile, ~9GB RAM liberi al momento della misura "
                "(su 20GB totali - il resto gia' impegnato da altri processi). Questo esclude "
                "modelli grandi (13B+) e context enormi (128K) come impraticabili su questa "
                "macchina - non e' un giudizio generico, e' specifico di QUESTO hardware.",
        },
        "runtime_inventory": {
            "ollama": {"installed": False}, "docker": {"installed": False},
            "lm_studio": {"installed": False}, "llama_cpp": {"installed": False},
            "vllm": {"installed": False},
            "python": {"installed": True, "path": "/c/Users/User/AppData/Local/Programs/Python/Python312/python",
                      "version": "3.12.10", "note": "Interprete usato da tutti i builder Phase 7 di questo progetto."},
            "python_windowsapps_alias": {"installed": True, "version": "3.14.6",
                "note": "Un secondo Python (WindowsApps alias) - NON quello usato dal progetto, "
                       "da NON confondere quando si installano pacchetti."},
            "node": {"installed": True, "version": "v24.18.0", "path": "/c/Program Files/nodejs/node"},
            "npm": {"installed": True, "version": "11.16.0", "global_packages": "nessuno (vuoto)"},
            "git": {"installed": True, "version": "2.55.0.windows.1", "path": "/mingw64/bin/git"},
            "github_cli": {"installed": True, "version": "2.96.0", "authenticated": True,
                          "account": "starmarketkiller", "token_scopes": ["gist", "read:org", "repo", "workflow"]},
        },
        "existing_local_models": {
            "found": False,
            "search_performed": "Ricerca *.gguf/*.safetensors/*.bin in Downloads/Desktop/Documents "
                "(ricorsiva) + directory comuni di Ollama/LM Studio/HuggingFace cache/GPT4All - "
                "TUTTE risultate assenti o vuote.",
            "qwen_check": "Nessun modello Qwen (o di qualunque altra famiglia) gia' presente sul "
                         "disco - richiede un download da zero, qualunque sia la scelta finale.",
        },
        "repository_readiness": {
            "repo_present_locally": True, "path": str(ROOT),
            "branch": "main", "head": "227965be7b7c687d505e8da7f4380874341d24e9",
            "remote_origin": "https://github.com/starmarketkiller/MAX.git",
            "second_remote_found": "codex-local -> C:/Users/User/Documents/Codex/2026-08-05/"
                "sto-lavorando-con-claude-sullo-stesso/MAX (una seconda copia locale del repo "
                "gestita dalla sessione Codex - confermata esistente su disco, non ispezionata "
                "oltre - fuori scope di questa fase).",
            "github_auth": "Autenticato (gh CLI, account starmarketkiller, scope repo/workflow - "
                          "sufficiente per push).",
            "working_tree_clean_at_measurement": True,
            "ability_to_run_tests": "Confermata - pytest gia' usato per l'intera suite Phase 7 in "
                                   "questa stessa sessione.",
        },
        "connectivity_distinction": {
            "repository": "READ_WRITE (git clone locale + push autenticato via gh CLI).",
            "vault_research_artifacts": "READ_WRITE (file JSON locali sotto server/research_scripts/, "
                "nessun servizio remoto - il 'Vault' di questo progetto e' filesystem+git, non un "
                "database esterno).",
            "render_api_control_plane": "Non ispezionato in questa fase (richiederebbe credenziali "
                "di deploy/produzione - fuori scope, nessuna azione privilegiata presa).",
            "mt5_logs_artifacts": "READ_WRITE per i file .csv/.certificate.txt/manifest gia' "
                "dimostrato in Phase 7.23-7.25 (harness di isolamento) - EXECUTE (lancio Tester) "
                "gia' dimostrato funzionante in questa sessione.",
            "privileged_actions_not_tested": ["deploy produzione", "modifica credenziali/config "
                "live", "trading reale"],
        },
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "environment_inventory_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
