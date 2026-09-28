#!/usr/bin/env python3
"""Local Model Bake-Off V1 - Fase 16: report finale consolidato (22 punti
richiesti dal task PUSH RECOVERY + LOCAL MODEL BAKE-OFF V1). Aggrega tutti
gli artifact gia' prodotti in questa fase, non ricalcola nulla."""
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

ALLOWED_DECISIONS = ["LOCAL_MODEL_SELECTION_VALIDATED", "CURRENT_MODEL_REMAINS_BEST",
                    "LOCAL_AGENT_CAPABILITY_IMPROVED_BUT_LIMITED",
                    "INSUFFICIENT_HARDWARE_FOR_USEFUL_TIER2"]


def _load(fname):
    path = os.path.join(ORCH_DIR, fname)
    if not os.path.exists(path):
        return None
    return load_json(path)["payload"]


def build():
    scorecard = _load("bakeoff_scorecard_v1.json")
    registry = _load("agent_capability_registry_v1.json")
    pilot_corrected = _load("pilot_run_v2_result_CORRECTED_v1.json")
    toolcalling = _load("toolcalling_probe_results_v1.json")

    push_recovery_report = {
        "pre_existing_commit": "dd6f5a5", "local_head_before": "dd6f5a5",
        "origin_main_before": "453f2ff (un commit indietro - email non ancora verificata)",
        "action": "git push origin main (nessun force, nessun rebase necessario - "
                 "avanzamento lineare semplice)",
        "local_head_after": "dd6f5a5", "origin_main_after": "dd6f5a5",
        "working_tree_after": "pulito (solo file non tracciati pre-esistenti non correlati)",
        "push_status": "SUCCESS",
    }

    baseline_qwen25_summary = {
        "qwen2.5_3b": "5.76-8.93 tok/s task brevi, JSON affidabile via format:json, lento su "
                    "contesto lungo (~297-304s per ~4K token freschi), NON affidabile nel pilot "
                    "di coding REALE della fase precedente (0/4 tentativi completati "
                    "correttamente).",
        "qwen2.5_7b": "2.97-4.75 tok/s (~meta' del 3B), context lungo impraticabile (timeout "
                    ">600s), NON affidabile nel pilot di coding REALE della fase precedente "
                    "(0/4 tentativi).",
        "status": "Riusati come baseline in questo bake-off (ri-testati con la NUOVA suite "
                 "comprehensiva A-H per confronto equo con i nuovi candidati) - non solo "
                 "riferiti dalla memoria della fase precedente.",
    }

    shortlist = {
        "candidati_valutati": ["qwen3:4b (~4B, Apache 2.0)", "ministral-3:3b (~3.8B, Apache 2.0)",
                              "gemma3:4b (~4B, Google Gemma Terms of Use)"],
        "candidati_scartati_prima_del_download": [],
        "nota": "Tutti e 3 i candidati della shortlist richiesta sono risultati realmente "
              "disponibili su Ollama in formato pratico (Q4_K_M) - nessuno scartato in fase "
              "di static filter, tutti scaricati e testati (entro il limite di 3 nuovi "
              "candidati).",
    }

    static_filter = {
        "qwen3:4b": {"licenza": "Apache 2.0, no login", "dimensione": "2.5GB Q4_K_M",
                    "context_dichiarato": "256K (teorico - irrilevante su questo hardware)",
                    "rischio_noto_pre_download": "Nessuno rilevato in fase di ricerca - "
                                                "il problema del thinking-mode non "
                                                "disattivabile e' emerso SOLO durante il test "
                                                "empirico, non documentato chiaramente nelle "
                                                "fonti consultate prima del download."},
        "ministral-3:3b": {"licenza": "Apache 2.0, no login", "dimensione": "3.0GB Q4_K_M",
                          "context_dichiarato": "256K (teorico)",
                          "rischio_noto_pre_download": "Nessuno - candidato pulito."},
        "gemma3:4b": {"licenza": "Google Gemma Terms of Use (source-available, non Apache - "
                               "Prohibited Use Policy, diritto di Google di revocare l'uso) - "
                               "meno permissiva ma accettabile per uso di ricerca interno",
                    "dimensione": "3.3GB Q4_K_M", "context_dichiarato": "128K (teorico)",
                    "rischio_noto_pre_download": "Licenza meno permissiva di Apache 2.0 - "
                                                "accettato comunque per la valutazione dato "
                                                "l'uso puramente interno/di ricerca."},
    }

    installed_candidates = {
        "qwen3:4b": "2.5GB, installato e testato", "ministral-3:3b": "3.0GB, installato e testato",
        "gemma3:4b": "3.3GB, installato e testato",
        "totale_download_nuovo": "8.8GB (entro budget disco/RAM ampio: 268GB liberi, 20GB RAM "
                                "totale)",
    }

    reliability_metrics = {}
    performance_metrics = {}
    if scorecard:
        for m, d in scorecard["scorecard"].items():
            if d.get("available"):
                metrics = d["metrics"]
                reliability_metrics[m] = {
                    "success_rate": metrics["success_rate"], "timeout_rate": metrics["timeout_rate"],
                    "json_valid_rate": metrics["json_valid_rate"],
                    "schema_compliance_rate": metrics["schema_compliance_rate"],
                    "coding_pass_rate": metrics["coding_pass_rate"],
                    "hallucination_resistance": metrics["hallucination_resistance"],
                    "constraint_compliance": metrics["constraint_compliance"],
                    "consistency": metrics["consistency"],
                }
                performance_metrics[m] = {
                    "avg_wall_seconds": metrics["avg_wall_seconds"],
                    "avg_tokens_per_second": metrics["avg_tokens_per_second"],
                    "tool_use_classification": metrics["tool_use_classification"],
                }

    context_results = {
        "metodologia": "Il bake-off di questa fase ha usato num_ctx=8192 per tutti i task "
                     "(nessun prompt ha superato ~2-3K token effettivi, quindi 4K/8K/16K non "
                     "sono stati differenziati sperimentalmente in questa fase specifica - "
                     "riusa la scoperta gia' fatta e validata nella fase precedente).",
        "riferimento_fase_precedente": "Qwen2.5 3B: ~4K token freschi gestibile ma lento "
                                      "(~300s), 7B: >600s timeout anche a ~4K - MAI premiare "
                                      "context teorico enorme su questo hardware, confermato "
                                      "anche in questa fase dal comportamento di qwen3:4b "
                                      "(dichiara 256K, nella pratica va in timeout anche su "
                                      "prompt di poche centinaia di token per via del thinking "
                                      "mode).",
    }

    tool_use_results = toolcalling["results"] if toolcalling else {}

    selected_local_fast = "ministral-3:3b"
    selected_local_strong = "ministral-3:3b"
    selection_rationale = (
        "ministral-3:3b vince la scorecard pesata (0.9764, il piu' alto) ED e' l'UNICO modello "
        "(insieme a qwen2.5 3B/7B, entrambi inferiori su ogni altra metrica) con tool-calling "
        "nativo funzionante verificato (gemma3:4b: 'does not support tools', confermato dal "
        "runtime stesso). Ha inoltre risolto per la PRIMA volta in questo progetto il pilot "
        "REALE di backfill (0/4 con qwen2.5 3B/7B nella fase precedente, 4/4 in questa fase - "
        "vedi pilot_result sotto). Nessun secondo modello porta un vantaggio dimostrato "
        "sufficiente da giustificare due modelli diversi per i due ruoli su questo hardware - "
        "usato lo stesso modello per LOCAL_FAST e LOCAL_STRONG, esplicitamente permesso dal "
        "task."
    )

    pilot_result = {
        "task": "Backfill REALE temporal_concentration + exit_efficiency per BREAKOUT_ACC e "
               "ORDER_BLOCK (stesso task della fase precedente, fallito 4/4 con qwen2.5 3B/7B)",
        "model_used": "ministral-3:3b", "harness_fixes_applied": [
            "Nessun file di riferimento di stile nel prompt (lezione della fase precedente - "
            "i modelli piccoli copiano identificatori invece di astrarre)",
            "Import/invocazione forniti dall'harness deterministico, non richiesti al modello "
            "(gia' validato nei task E1/E2 del bake-off)",
            "Gestione delle eccezioni di rete in _call_model (un timeout non deve far crashare "
            "l'intero script, deve attivare il retry delimitato previsto dalla Routing Policy - "
            "bug trovato e corretto, ambientale non scientifico)",
            "Confronto di verifica reso tollerante ai float (math.isclose) dopo aver trovato un "
            "falso negativo dovuto a rumore di arrotondamento (~1e-15) da ordine di somma "
            "diverso fra il codice del modello e il riferimento indipendente - NON una "
            "correzione della logica del worker, solo del metodo di confronto.",
        ],
        "outcome": "4/4 sotto-task risolti correttamente (verificati indipendentemente con un "
                 "calcolo di riferimento scritto separatamente da Claude) - il PRIMO successo "
                 "reale del worker locale su questo task in tutto il progetto. 2 retry "
                 "delimitati usati (1 per un timeout di rete genuino, 1 causato dal bug di "
                 "confronto float dell'harness, non da un errore del modello - il primo "
                 "tentativo era gia' corretto).",
        "overall_pilot_passed": pilot_corrected["overall_pilot_passed"] if pilot_corrected else None,
        "claude_did_not_write_worker_logic": True,
    }

    agent_shell_bakeoff = {
        "ollama_diretto": {
            "repo_access": "Si' (via script Python, gia' dimostrato in questa fase)",
            "read_write_diff_test": "Si'", "terminal_tool_calling": "Si' (via API HTTP diretta)",
            "structured_output": "Si' (format:json affidabile)",
            "files_allowed_forbidden": "Rispettabile a livello di prompt/harness (dimostrato "
                                      "nel task F1/F2 del bake-off)",
            "solo_locale": "Si'", "login_richiesto": "No", "crediti_consumati": "No",
            "affidabilita_windows": "Alta (nativo, nessuna dipendenza WSL2)",
            "overhead_ram_cpu": "Minimo (solo il processo Ollama + script Python)",
            "integrazione_futura_orchestrator": "Diretta (stessa API HTTP gia' usata)",
            "headless_automation": "Ottima (API HTTP pura)",
        },
        "opencode": {
            "context_minimo_richiesto": "64K - CONFERMATO dalla documentazione ufficiale Ollama "
                                       "(docs.ollama.com/integrations/opencode): 'OpenCode "
                                       "requires a context length of 64k or higher'",
            "compatibilita_hardware": "INCOMPATIBILE - il tetto pratico di questo hardware e' "
                                     "ben sotto 8K per generazione affidabile in tempi utili "
                                     "(vedi context_results sopra) - 64K e' 8x oltre quel tetto",
            "login_richiesto": "Non specificato per uso locale, ma irrilevante dato il blocco "
                              "sul context",
            "decisione": "OPENCODE_DEFERRED - stesso motivo bloccante di Hermes",
        },
        "hermes_agent": {
            "context_minimo_richiesto": "64K (confermato, ri-verificato in questa fase dalla "
                                       "documentazione ufficiale)",
            "windows_compatibility": "Richiede WSL2 (risolta l'ambiguita' della fase precedente "
                                    "- fonte ufficiale Hermes conferma WSL2 necessario)",
            "problema_sicurezza_aggiuntivo": "La documentazione ufficiale raccomanda di "
                                            "bindare Ollama su 0.0.0.0 (non solo localhost) per "
                                            "l'accesso da WSL2 - CONFLIGGE DIRETTAMENTE con il "
                                            "vincolo di sicurezza gia' stabilito nella fase "
                                            "precedente ('non esporre Ollama pubblicamente') - "
                                            "un motivo IN PIU', non solo il context, per "
                                            "rimandarlo.",
            "bug_noto": "Issue GitHub #25629 ancora aperta (hang Ollama+tool-calling)",
            "decisione": "HERMES_DEFERRED - confermato, con un motivo di sicurezza aggiuntivo "
                        "trovato in questa fase.",
        },
        "claude_code_come_runtime_locale": "Escluso dal confronto per istruzione esplicita "
                                          "dell'utente (non va considerato soluzione gratuita "
                                          "di default se richiede account/quota/provider "
                                          "premium - valutabile solo come eventuale interfaccia "
                                          "di escalation, non come LOCAL_AGENT_RUNTIME).",
        "decisione_finale": "OLLAMA_DIRECT rimane la scelta per LOCAL_AGENT_RUNTIME in questa "
                           "fase - nessuna delle due agent shell valutate (OpenCode, Hermes) e' "
                           "compatibile con questo hardware, per lo stesso vincolo di fondo "
                           "(context minimo 64K) aggravato per Hermes da un problema di "
                           "sicurezza aggiuntivo.",
    }

    storage_cleanup = {
        "modelli_da_tenere": ["ministral-3:3b (selezionato, LOCAL_FAST + LOCAL_STRONG)",
                             "qwen2.5:3b-instruct (baseline di riferimento, gia' validato su 2 "
                             "fasi, 1.9GB - economico da tenere)"],
        "modelli_baseline_opzionali_da_tenere": ["gemma3:4b (secondo miglior punteggio "
                                                "corretto 0.90 - nessun urgente motivo di "
                                                "rimuoverlo, utile come secondo parere futuro "
                                                "nonostante l'allucinazione trovata e "
                                                "l'assenza di tool-calling, 3.3GB)"],
        "modelli_raccomandati_per_rimozione": ["qwen2.5:7b-instruct (4.7GB - superato da "
                                              "ministral-3:3b su OGNI metrica misurata in "
                                              "questo bake-off: piu' lento, meno affidabile, "
                                              "stesso fallimento nel pilot precedente)",
                                              "qwen3:4b (2.5GB - SQUALIFICATO: 88% timeout "
                                              "rate nel bake-off, thinking mode non "
                                              "disattivabile ne' via API ne' via prompt su "
                                              "questa build di Ollama)"],
        "spazio_recuperabile_se_rimossi": "7.2GB (4.7GB + 2.5GB)",
        "nota": "NESSUNA rimozione eseguita automaticamente in questa fase, per istruzione "
              "esplicita del task - solo raccomandazione, in attesa di autorizzazione "
              "dell'utente. Spazio disco attuale comunque abbondante (262GB liberi), quindi "
              "la rimozione non e' urgente, solo consigliata per igiene.",
    }

    if scorecard and scorecard["ranked_by_weighted_score"][0][0] == "ministral-3:3b" and pilot_result["overall_pilot_passed"]:
        decision = "LOCAL_MODEL_SELECTION_VALIDATED"
        decision_reason = ("Il bake-off ha identificato un modello (ministral-3:3b) "
                          "misurabilmente migliore dei baseline Qwen2.5 su OGNI metrica "
                          "testata (schema compliance, coding pass rate, hallucination "
                          "resistance, latenza, tool-calling), E questo modello ha risolto per "
                          "la prima volta il pilot REALE di coding che i baseline avevano "
                          "fallito 4/4 volte nella fase precedente. Selezione validata "
                          "empiricamente, non teoricamente.")
    else:
        decision = "LOCAL_AGENT_CAPABILITY_IMPROVED_BUT_LIMITED"
        decision_reason = "Vedi dettagli sopra."

    payload = {
        "1_push_recovery_report": push_recovery_report,
        "2_baseline_summary_qwen25": baseline_qwen25_summary,
        "3_shortlist": shortlist,
        "4_static_filter": static_filter,
        "5_installed_candidates": installed_candidates,
        "6_benchmark_suite_note": "9 categorie NEXUS-rappresentative (A-H, con A ed E ripetuti "
                                 "2x per misura di consistency) - vedi bakeoff_tasks.py per il "
                                 "dettaglio completo dei prompt.",
        "7_raw_benchmark_results_files": [f"bakeoff_results_{m.replace(':', '-')}_v1.json"
                                        for m in ["qwen2.5:3b-instruct", "qwen2.5:7b-instruct",
                                                 "qwen3:4b", "ministral-3:3b", "gemma3:4b"]],
        "8_reliability_metrics": reliability_metrics,
        "9_performance_metrics": performance_metrics,
        "10_context_results": context_results,
        "11_tool_use_results": tool_use_results,
        "12_scorecard": scorecard["scorecard"] if scorecard else None,
        "12b_scorecard_ranking": scorecard["ranked_by_weighted_score"] if scorecard else None,
        "13_selected_local_fast": selected_local_fast,
        "14_selected_local_strong": selected_local_strong,
        "selection_rationale": selection_rationale,
        "15_quantization": "Q4_K_M per tutti i modelli testati (coerente con la raccomandazione "
                          "della fase precedente per questo hardware CPU-only)",
        "16_context_recommendation": "8192 come tetto operativo pratico (confermato, non "
                                    "esteso in questa fase) - mai forzare context teorico "
                                    "enorme (256K dichiarato da qwen3/ministral e' puramente "
                                    "teorico su questo hardware)",
        "17_routing_updates": "agent_capability_registry_v1.json - 2 agenti (LOCAL_FAST_"
                             "MINISTRAL3B, LOCAL_STRONG_MINISTRAL3B), validato contro "
                             "contracts/agent-capability-registry.schema.json",
        "18_pilot_result": pilot_result,
        "19_agent_shell_bakeoff": agent_shell_bakeoff,
        "20_storage_cleanup_recommendation": storage_cleanup,
        "21_verifier": "server/orchestrator_v1/verify_bakeoff.py",
        "22_tests": "server/tests/test_orchestrator_v1_bakeoff.py",
        "no_deploy": True, "no_strategy_modified": True, "no_backtest_run": True,
        "no_models_secrets_credentials_committed": True,
        "decision": decision, "decision_reason": decision_reason,
    }
    assert payload["decision"] in ALLOWED_DECISIONS
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "bakeoff_final_report_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path}")
    print(f"DECISIONE: {payload['decision']}")


if __name__ == "__main__":
    main()
