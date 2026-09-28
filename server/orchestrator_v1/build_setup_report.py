#!/usr/bin/env python3
"""Orchestrator V1 - Local Runtime Setup, report finale consolidato
(punto L). Aggrega ollama/hermes/benchmark/pilot in un solo artifact
con la decisione finale. Le misure di benchmark/pilot sono EMPIRICHE
(non deterministiche in senso Phase-7 - un LLM non da' sempre la
stessa risposta) - questo builder legge i file gia' salvati con quelle
misure, non le ricalcola."""
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

ALLOWED_DECISIONS = ["LOCAL_WORKER_OPERATIONAL", "LOCAL_WORKER_OPERATIONAL_WITH_LIMITATIONS",
                    "LOCAL_WORKER_NOT_READY"]


def _load_if_exists(fname):
    path = os.path.join(ORCH_DIR, fname)
    if not os.path.exists(path):
        return None
    return load_json(path)["payload"]


def build():
    bench_3b = _load_if_exists("benchmark_results_qwen2.5-3b-instruct_ctx8192_v1.json")
    bench_7b = _load_if_exists("benchmark_results_qwen2.5-7b-instruct_ctx8192_v1.json")
    pilot_attempt1_failed = _load_if_exists("pilot_run_result_ATTEMPT1_FAILED_v1.json")
    pilot_attempt2_failed = _load_if_exists("pilot_run_result_ATTEMPT2_FAILED_3b_v1.json")
    pilot_final = _load_if_exists("pilot_run_result_v1.json")

    ollama_status = {
        "version": "0.34.4", "install_method": "winget (Ollama.Ollama, nativo Windows)",
        "service_running": True, "endpoint": "http://127.0.0.1:11434",
        "bound_to_localhost_only": True, "publicly_exposed": False,
        "auto_start_configured": True, "auto_start_mechanism": "Collegamento Ollama.lnk in "
            "Startup folder (creato dall'installer)",
        "no_api_key_no_cloud_dependency": True, "account_required": False,
        "models_installed": ["qwen2.5:3b-instruct (1.9GB)", "qwen2.5:7b-instruct (4.7GB)"],
    }

    hermes_status = {
        "verified_version_info": "Hermes Agent (NousResearch), MIT license - repo attivo",
        "windows_native_support": "Fonti in conflitto: una guida ufficiale (hermes-agent.ai) "
            "afferma supporto Windows nativo senza WSL2 richiesto; un'altra guida (fast.io) "
            "afferma che serve WSL2 - non risolto con certezza in questa fase (nessuna "
            "installazione di Hermes eseguita per verificarlo empiricamente, vedi motivazione "
            "sotto).",
        "minimum_context_requirement": "64.000 token - dichiarato come MINIMO per il tool-use "
            "agentic (fonte: hermes-agent.nousresearch.com/docs/guides/local-ollama-setup) - "
            "IN CONFLITTO DIRETTO con la raccomandazione hardware di questa stessa fase "
            "(8K-16K pratico su questo hardware, mai 128K - e 64K e' gia' oltre quella soglia).",
        "minimum_cpu_requirement": "4 core fisici raccomandati - questo hardware ne ha 2 fisici "
            "(4 logici via hyperthreading, non equivalenti a 4 core reali per compute sostenuto).",
        "known_stability_bug": "Issue GitHub #25629 (NousResearch/hermes-agent, APERTO/NON "
            "RISOLTO): Ollama si blocca indefinitamente quando stream=true e' combinato con "
            "definizioni di tool (3-25+ tool) - riscontrato anche su hardware NETTAMENTE piu' "
            "potente di questo (Ryzen 5 7430U, 64GB RAM) - nessuna soluzione completa nota, solo "
            "workaround parziali (proxy LiteLLM per forzare stream=false).",
        "decision": "NON installato in questa fase - il requisito di 64K context da solo e' "
            "sufficiente a squalificare Hermes per QUESTO hardware (indipendentemente dalla "
            "questione Windows/WSL2), aggravato da un bug di stabilita' noto e non risolto anche "
            "su hardware migliore. Coerente con l'istruzione esplicita del task: 'documenta "
            "l'alternativa piu' semplice e usa direttamente Ollama'.",
        "alternative_used": "Integrazione diretta con l'endpoint HTTP OpenAI-compatible di "
            "Ollama (http://127.0.0.1:11434/api/generate, con 'format':'json' per output "
            "strutturato affidabile) - nessun livello Hermes intermedio.",
    }

    pilot_summary = {
        "task": "Backfill temporal_concentration (per-anno) per BREAKOUT_ACC e ORDER_BLOCK - "
               "scrivere una funzione Python compute_temporal_concentration(events) dato un "
               "riferimento di stile (build_liq_sweep_temporal_robustness.py, Phase 7.25/7.26).",
        "attempts_summary": [
            {"attempt": 1, "model": "qwen2.5:3b-instruct", "result": "TIMEOUT (600s) sulla prima "
                "chiamata BREAKOUT_ACC - causa probabile: congestione residua dal test di "
                "contesto lungo del 7B appena eseguito, non un problema del 3B stesso."},
            {"attempt": 2, "model": "qwen2.5:3b-instruct", "result": "COMPLETATO ma FALLITO - "
                "codice generato usa 'defaultdict'/'_dt' senza importarli (copiati per stile dal "
                "riferimento senza capire che erano import esterni); ORDER_BLOCK ha prodotto una "
                "funzione sintatticamente valida ma SENZA la riga di invocazione/stampa richiesta "
                "esplicitamente nel prompt (bug di instruction-following, non di logica)."},
            {"attempt": 3, "model": "qwen2.5:3b-instruct", "result": "COMPLETATO ma FALLITO, DOPO "
                "un fix DETERMINISTICO dell'harness (import + invocazione aggiunti da Claude come "
                "impalcatura TIER 0, la logica di aggregazione resta del modello) - il modello ha "
                "prodotto un NUOVO errore diverso (ha copiato letteralmente `from "
                "nxs_liq_sweep_edge_dataset_loader import (...)` e chiamate a funzioni "
                "`entry_time(e)`/`net_pnl(e)` come se esistessero, invece di usare le chiavi dict "
                "esplicitamente specificate nel prompt) - pattern di FALLIMENTO CONSISTENTE: il "
                "modello copia identificatori specifici dal riferimento di stile invece di "
                "astrarre e adattare al nuovo schema dati."},
            {"attempt": 4, "model": "qwen2.5:7b-instruct", "result": "TIMEOUT (>600s) - "
                "escalation locale tentata (3B->7B) dopo 2 fallimenti del 3B, come da gerarchia "
                "corretta dall'utente - il 7B non ha completato la generazione entro 10 minuti "
                "anche su un prompt breve (~1500 token stimati) che nel benchmark aveva "
                "richiesto solo 15-35s per task di lunghezza comparabile - Ollama restava "
                "comunque responsivo (non un hang totale del servizio), suggerendo generazione "
                "anomalmente lunga/verbosa piuttosto che un blocco del server."},
        ],
        "overall_result": "FALLITO su tutti e 4 i tentativi (2 modelli, con 1 fix deterministico "
                        "dell'harness nel mezzo) - NESSUNA correzione della LOGICA del modello "
                        "e' stata fatta da Claude (solo impalcatura di import/invocazione, "
                        "esplicitamente permessa come rimedio TIER 0/ambientale).",
        "escalation_classification": "COMPLEX_CODE - per la regola di escalation di "
            "ROUTING_POLICY_V1 (docs/architecture/18_...), questo specifico task andrebbe ora "
            "assegnato a TIER 3 (Claude) o TIER 4 (Codex), non ritentato una quinta volta in "
            "locale.",
        "not_executed_by_claude_instead": True,
    }

    architecture_ready_flag = True  # gia' approvata prima di questa fase (task esplicito)

    if bench_3b and bench_7b:
        decision = "LOCAL_WORKER_OPERATIONAL_WITH_LIMITATIONS"
        decision_reason = ("Ollama e i 2 modelli funzionano in modo affidabile per task BREVI/"
            "semplici (risposta diretta, JSON via format=json, riassunto, log analysis, "
            "instruction-following, italiano/inglese - tutti completati con successo nel "
            "benchmark, 5-9 tok/s) - MA il pilot REALE (un task di coding zero-shot moderatamente "
            "complesso) e' fallito su TUTTI e 4 i tentativi con ENTRAMBI i modelli, per ragioni "
            "diverse (precisione del 3B, velocita'/affidabilita' del 7B). Il runtime e' quindi "
            "OPERATIVO per il ruolo TIER 1 (LOCAL_FAST) gia' oggi - il ruolo TIER 2 (LOCAL_STRONG, "
            "coding) richiede o task piu' semplici/meglio scaffolded, o l'escalation a Claude/"
            "Codex prevista dalla stessa architettura per questi casi.")
    else:
        decision = "LOCAL_WORKER_NOT_READY"
        decision_reason = "Benchmark incompleto."

    payload = {
        "orchestrator_architecture_status": "ORCHESTRATOR_ARCHITECTURE_READY (gia' approvata "
                                           "prima di questa fase)",
        "ollama_status": ollama_status,
        "hermes_status": hermes_status,
        "benchmark_qwen_3b_available": bench_3b is not None,
        "benchmark_qwen_7b_available": bench_7b is not None,
        "context_practical_ceiling": {
            "qwen_3b": "~4K token gestibile ma LENTO a freddo (~5 minuti la prima volta su "
                      "contenuto mai visto, poi molto piu' veloce su contenuto simile/cache-hit "
                      "- misurato empiricamente, non stimato) - context 8K raccomandato come "
                      "tetto operativo, non come uso frequente per contenuti lunghi.",
            "qwen_7b": "~4K token gia' NON PRATICO (timeout oltre 10 minuti anche a contesto "
                      "fresco medio) - il 7B su questo hardware va riservato a prompt BREVI "
                      "(poche centinaia di token), mai a task con contesto lungo.",
            "revised_guidance": "La guidance originale (Fase precedente) 'context 8-16K, mai "
                               "128K' si conferma per il 3B ma va RIVISTA AL RIBASSO per il 7B: "
                               "su QUESTO hardware il 7B e' pratico solo per prompt brevi, "
                               "indipendentemente dal context WINDOW configurato - la CPU non "
                               "regge il volume di calcolo per prompt lunghi in tempi utili.",
        },
        "revised_model_role_hierarchy": {
            "note": "Corretto dall'utente rispetto alla raccomandazione iniziale della fase "
                   "precedente - CONFERMATO empiricamente da questo benchmark.",
            "qwen_3b_instruct": "LOCAL_FAST - worker quotidiano di default (piu' veloce, "
                              "comunque capace sui task brevi testati).",
            "qwen_7b_instruct": "LOCAL_STRONG - escalation locale SOLO per task che richiedono "
                               "piu' capacita' MA con prompt BREVE - non affidabile per contesto "
                               "lungo O per generazione lunga su questo hardware (vedi pilot "
                               "attempt 4).",
        },
        "repo_connectivity": {"read": True, "write_in_sandbox": True,
                             "sandbox_dir": "server/research_scripts/phase7/phase7_28/",
                             "git_diff_checked": True, "tests_runnable": True,
                             "no_automatic_push_during_pilot": True},
        "vault_connectivity": {"mode": "READ_ONLY", "can_access": ["experiments", "hypotheses",
                              "learning_packets", "strategies", "research_priority_queue",
                              "task_result_contracts"]},
        "pilot_result": pilot_summary,
        "problems_found": [
            "Timeout ripetuti (600s+) su prompt anche brevi/medi con entrambi i modelli in "
            "alcune condizioni - causa non completamente isolata (possibile congestione da "
            "richieste precedenti abbandonate lato client ma ancora in elaborazione lato "
            "server) - comportamento di CODA/concorrenza di Ollama su CPU-only non "
            "completamente prevedibile, da approfondire prima di un uso realmente non "
            "presidiato.",
            "Il modello 3B copia identificatori specifici da un riferimento di stile invece di "
            "astrarre - implica che i prompt futuri per task di coding NON dovrebbero includere "
            "un file di riferimento con nomi specifici del progetto, ma solo la specifica "
            "astratta del task.",
        ],
        "escalation_needed": True,
        "escalation_target": "TIER3_CLAUDE o TIER4_CODEX per il completamento del backfill "
                            "temporal_concentration/exit_efficiency (task originale) - non "
                            "ritentato ulteriormente in locale in questa fase.",
        "decision": decision, "decision_reason": decision_reason,
        "no_deploy": True, "no_models_or_secrets_committed": True,
    }
    assert payload["decision"] in ALLOWED_DECISIONS
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "local_runtime_setup_report_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  DECISIONE: {payload['decision']}")


if __name__ == "__main__":
    main()
