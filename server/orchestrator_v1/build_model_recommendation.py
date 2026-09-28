#!/usr/bin/env python3
"""Orchestrator V1 - Parte B, punti 29-37: valutazione candidati e
raccomandazione finale, basata SOLO sull'inventario hardware reale di
build_environment_inventory.py (non su popolarita' generica del
modello). Nessuna installazione eseguita da questo script."""
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def build():
    inv = load_json(os.path.join(ORCH_DIR, "environment_inventory_v1.json"))["payload"]

    hardware_ceiling = {
        "realistic_max_params_dense_cpu_only": "7B a Q4_K_M (~4-5GB su disco) - oltre questo la "
            "velocita' di generazione su un i5-7200U (2 core/4 thread) scende a livelli non "
            "pratici per un worker che deve rispondere in tempi ragionevoli.",
        "comfortable_params_given_free_ram": "3B-4B a Q4_K_M (~2GB) - lascia margine nei ~9GB RAM "
            "liberi osservati, anche con altri programmi aperti.",
        "context_ceiling_practical": "8K-16K raccomandato come default operativo; 32K "
            "raggiungibile ma con rallentamento apprezzabile nel prompt-processing su CPU; 128K "
            "SCONSIGLIATO su questo hardware (tempo di processing del prompt e RAM richiesta "
            "crescono in modo non lineare, non giustificato per i task TIER 1/2 previsti).",
    }

    candidates = {
        "Qwen2.5-Instruct (3B e 7B)": {
            "license": "Apache-2.0 - NESSUN account/login richiesto su HuggingFace per il "
                      "download (ne' per l'originale ne' per le versioni GGUF di terze parti).",
            "tool_calling_json_reliability": "Fra le migliori della sua classe dimensionale - "
                "affidabilita' JSON/structured-output e tool-calling documentata come punto di "
                "forza specifico della famiglia Qwen2.5, non solo benchmark grezzi.",
            "multilingual_it_en": "Solido, la famiglia Qwen2.5 e' esplicitamente multilingue "
                                 "(29+ lingue incl. italiano) - non solo EN/ZH.",
            "coding": "Qwen2.5-Coder (variante dedicata, 3B/7B) e' fra i migliori modelli di "
                     "coding open-weight della sua taglia - utile specificamente per TIER 2.",
            "fit_for_this_hardware": "OTTIMO - sia il 3B che il 7B rientrano nel ceiling CPU-only "
                                    "sopra, licenza senza frizioni, ecosistema GGUF maturo.",
        },
        "Llama-3.2-Instruct (3B)": {
            "license": "Licenza community Meta - il repo UFFICIALE su HuggingFace richiede "
                      "accettazione licenza + account HF (gating); le versioni GGUF di terze "
                      "parti (es. bartowski) aggirano il login ma restano soggette alla licenza.",
            "tool_calling_json_reliability": "Buono ma storicamente un gradino sotto Qwen2.5 sulla "
                "stessa taglia per affidabilita' di structured-output nei benchmark pubblici.",
            "multilingual_it_en": "Supporto italiano dichiarato ma meno enfatizzato di Qwen.",
            "fit_for_this_hardware": "BUONO come alternativa - 3B compatibile con l'hardware, ma "
                                    "frizione di licenza/login in piu' rispetto a Qwen a parita' "
                                    "di prestazioni attese.",
        },
        "Mistral-7B-Instruct-v0.3": {
            "license": "Apache-2.0 - nessun login richiesto.",
            "tool_calling_json_reliability": "Supporto tool-calling nativo aggiunto da v0.3, "
                "ragionevole ma meno specializzato su JSON stretto rispetto a Qwen2.5.",
            "fit_for_this_hardware": "ACCETTABILE - 7B al limite superiore del ceiling CPU, nessun "
                                    "vantaggio chiaro su Qwen2.5-7B per questo caso d'uso.",
        },
        "DeepSeek-R1-Distill (Qwen/Llama, 7B-8B)": {
            "license": "Apache-2.0 (i modelli distillati) - nessun login.",
            "reasoning": "Ottimo per reasoning esplicito (catena di pensiero lunga) - MA questo "
                        "produce risposte molto piu' lunghe/lente, controproducente su CPU lenta "
                        "per task TIER 1 (riassunti/log/registry) che devono essere rapidi.",
            "fit_for_this_hardware": "SCONSIGLIATO come modello primario - il reasoning esteso "
                                    "amplifica proprio il collo di bottiglia (velocita' CPU) di "
                                    "questa macchina; candidato secondario SOLO per singoli task "
                                    "di debug complesso, non come worker di routine.",
        },
        "Hermes (fine-tune NousResearch, su base Llama/Qwen)": {
            "note_ambiguita": "Non ho trovato alcun riferimento a 'Hermes' nel repo o sulla "
                             "macchina - interpretato come la famiglia di fine-tune NousResearch "
                             "specializzata in tool-use/agentic (es. Hermes-3), distribuita come "
                             "GGUF eseguibile via Ollama - NON un runtime a se stante. Se "
                             "l'utente intendeva un prodotto diverso con lo stesso nome, va "
                             "chiarito prima di procedere.",
            "fit_for_this_hardware": "Le varianti Hermes su base Qwen2.5-7B sarebbero "
                "tecnicamente compatibili con l'hardware (stesso footprint del Qwen2.5-7B "
                "sottostante) - candidato VALIDO come alternativa/complemento a Qwen2.5-Instruct "
                "puro se l'obiettivo e' massimizzare l'affidabilita' di tool-calling agentic - "
                "non testato in questa fase (nessun download eseguito).",
        },
    }

    runtime_comparison = {
        "Ollama": {
            "windows_support": "Nativo, installer .exe, gira come servizio in background - "
                              "espone un endpoint HTTP locale OpenAI-compatible di serie.",
            "login_required": False,
            "automation_fit": "OTTIMO - un orchestratore puo' chiamare l'endpoint HTTP senza "
                             "gestire processi manualmente; `ollama pull`/`ollama run` scriptabili.",
            "verdict": "SCELTA CONSIGLIATA per questo caso - il servizio in background e "
                      "l'API HTTP stabile sono esattamente cio' che serve a un worker "
                      "automatizzato, con zero frizione su Windows.",
        },
        "llama.cpp (server diretto)": {
            "windows_support": "Richiede build/binari separati, nessuna gestione servizio nativa "
                              "su Windows (va gestito manualmente o con un wrapper).",
            "login_required": False,
            "automation_fit": "BUONO ma piu' lavoro manuale di setup rispetto a Ollama per lo "
                             "stesso identico modello sottostante (Ollama USA llama.cpp "
                             "internamente) - nessun vantaggio pratico qui.",
            "verdict": "Alternativa valida solo se servisse un controllo a basso livello che "
                      "Ollama non espone - non il caso per i task TIER 1/2 di questa fase.",
        },
        "LM Studio": {
            "windows_support": "Ottimo, GUI nativa Windows.",
            "login_required": False,
            "automation_fit": "MEDIOCRE per un worker headless/background - pensato per uso "
                             "interattivo via GUI, l'API server e' presente ma meno pensata per "
                             "automazione non presidiata rispetto al servizio Ollama.",
            "verdict": "Utile per ispezione/test manuale dei modelli, non come runtime di "
                      "produzione del worker.",
        },
        "vLLM": {
            "windows_support": "Nativamente Linux/GPU-oriented - supporto Windows/CPU-only "
                              "limitato o assente in pratica.",
            "automation_fit": "NON APPLICABILE a questo hardware (nessuna GPU, Windows) - escluso "
                             "per incompatibilita' diretta, non per preferenza.",
            "verdict": "ESCLUSO per questo caso specifico.",
        },
    }

    recommendation = {
        "local_runtime_chosen": "Ollama",
        "primary_local_model": "qwen2.5:7b-instruct-q4_K_M",
        "optional_fast_model": "qwen2.5:3b-instruct-q4_K_M",
        "single_vs_dual_model_decision": "DUE modelli separati raccomandati (non uno solo): il 3B "
            "per TIER 1 (riassunti, log, registry, azioni di routine - deve essere veloce), il 7B "
            "solo quando serve piu' capacita' (TIER 2 leggero: piccoli fix, classificazione piu' "
            "sfumata) - accettando che sia piu' lento. Se la macchina si rivela troppo lenta anche "
            "per il 3B durante il pilota, ripiegare su un SOLO modello (il 3B) e instradare TUTTO "
            "il resto a Claude/Codex.",
        "quantization": "Q4_K_M per entrambi - miglior compromesso dimensione/qualita' per CPU-only "
                       "inference, standard consolidato nell'ecosistema GGUF.",
        "context_size_recommendation": "8192 token di default (16384 se un task specifico lo "
            "richiede esplicitamente) - MAI 128K su questo hardware.",
        "expected_ram_footprint": "~2GB (3B) / ~4.5-5GB (7B) a runtime - entrambi compatibili coi "
            "~9GB liberi osservati, ma NON contemporaneamente sotto carico pesante insieme ad "
            "altre applicazioni pesanti (IDE, browser con molte tab, MT5 terminal).",
        "expected_speed": "Stimata (non misurata - nessun modello ancora scaricato in questa "
            "fase): dell'ordine di pochi token/secondo su questa CPU per il 7B, "
            "moderatamente piu' veloce per il 3B - adeguato per task in BACKGROUND "
            "(non interattivi in tempo reale), coerente con l'uso TIER 1/2 previsto "
            "dall'architettura (mai un utente in attesa sincrona).",
        "tool_use_mode": "Function-calling nativo Qwen2.5 via l'API OpenAI-compatible di Ollama "
                        "(/api/chat con tools) - stesso pattern che l'orchestratore usera' per "
                        "gli agenti premium, nessuna astrazione diversa da mantenere.",
        "repo_access_policy": "READ_WRITE sulla working copy locale gia' presente e autenticata "
                             "(gh CLI, account starmarketkiller) - nessun nuovo account da creare.",
        "vault_access_policy": "READ_WRITE sui file JSON locali (stesso pattern gia' in uso da "
                               "tutti i builder Phase 7) - nessun servizio esterno nuovo.",
        "sandbox_policy": "Il worker locale opera SEMPRE dentro TIER 1/2 (vedi ROUTING_POLICY_V1) "
                         "- file_access READ_WRITE limitato a repo_scope dichiarato nel "
                         "TASK_MANIFEST, MAI credenziali/produzione/trading (vedi security model).",
        "escalation_policy": "Qualunque fallimento verificato (verifier=False dopo il retry "
                            "delimitato) esce dal TIER locale - MAI un secondo retry locale "
                            "silenzioso.",
        "why_this_choice_for_this_hardware_not_in_general": (
            "Non e' 'il modello migliore in assoluto' - e' il modello che rientra nel budget "
            "RAM/CPU REALMENTE osservato su QUESTA macchina (dual-core 2017, nessuna GPU, ~9GB "
            "liberi), con licenza che non introduce frizione di login (obiettivo esplicito del "
            "task), e con l'affidabilita' di JSON/tool-calling che l'intera architettura "
            "TASK_MANIFEST/RESULT_PACKET richiede per essere automatizzabile senza supervisione "
            "costante. Un modello piu' grande (13B+) o un runtime GPU-oriented (vLLM) sarebbero "
            "scelte MIGLIORI su un hardware diverso - qui sarebbero semplicemente troppo lenti o "
            "incompatibili."
        ),
    }

    payload = {
        "hardware_ceiling": hardware_ceiling, "candidates_evaluated": candidates,
        "runtime_comparison": runtime_comparison, "final_recommendation": recommendation,
        "no_heavy_install_performed_this_phase": True,
        "hardware_source": "environment_inventory_v1.json",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "model_recommendation_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  runtime: {payload['final_recommendation']['local_runtime_chosen']} | "
         f"primary: {payload['final_recommendation']['primary_local_model']}")


if __name__ == "__main__":
    main()
