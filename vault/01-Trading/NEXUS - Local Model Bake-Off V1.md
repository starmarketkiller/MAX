# NEXUS - Push Recovery + Local Model Bake-Off V1

**Baseline:** `dd6f5a5` (Local Runtime Setup + First NEXUS Pilot, `LOCAL_WORKER_OPERATIONAL_WITH_LIMITATIONS`). Nessuna modifica MQL5/logiche di trading. Nessun deploy. Nessun backtest. Nessuna installazione indiscriminata (max 3 nuovi modelli, rispettato).

**Obiettivo**: (0) sbloccare il push del commit gia' pronto (email GitHub verificata nel frattempo); (1-10) eseguire un bake-off aggiornato dei migliori modelli locali compatibili con questo hardware, misurati su una suite NEXUS reale e ripetibile; (11-13) selezionare al massimo un LOCAL_FAST e un LOCAL_STRONG e validarli con lo stesso pilot REALE fallito 4/4 volte nella fase precedente; (Extra) confrontare Ollama diretto vs OpenCode vs Hermes come possibile LOCAL_AGENT_RUNTIME; (15-16) cleanup storage e deliverable finale.

---

## Fase 0 — Push Recovery

`dd6f5a5` era gia' pronto localmente, bloccato solo da "email non verificata" lato GitHub. Verificato `git status`/HEAD/`origin/main` prima di agire (nessun avanzamento concorrente), eseguito `git push origin main` senza force: **successo**, `origin/main` allineato a `dd6f5a5`.

## Fase 1-4 — Shortlist, static filter, download

Shortlist richiesta (Qwen3 ~4B, Ministral 3 ~3B, Gemma3 ~4B) **tutta realmente disponibile** su Ollama in Q4_K_M, nessun candidato scartato prima del download. Licenze verificate: Qwen3 e Ministral **Apache 2.0** (no login), Gemma3 sotto i **Google Gemma Terms of Use** (meno permissiva - Prohibited Use Policy, diritto di Google di revocare l'uso - accettata comunque per uso di ricerca interno). Scaricati tutti e 3 (8.8GB totali, entro il limite di 3 nuovi candidati), su 268GB liberi e 20GB RAM totale.

## Fase 5-10 — Benchmark NEXUS reale + scorecard

Suite comprehensiva A-H (structured output, artifact reasoning, log analysis, file reasoning, coding sandbox, constraint following, lingua, multi-step), con repeat x2 sui task piu' decisivi (structured output, coding), su **tutti e 5** i modelli (i 2 baseline Qwen2.5 ri-testati con la stessa suite per un confronto equo, non solo richiamati dalla memoria).

**Scoperta empirica maggiore**: `qwen3:4b` ha la modalita' "thinking" **non disattivabile in modo affidabile** su questa build di Ollama (ne' `think:false` via API, ne' `/no_think` nel prompt) - un compito di una parola ha richiesto 94s di ragionamento nascosto; nel bake-off completo ha avuto **timeout sul 88% delle chiamate (15/17)**, consumando ~53 minuti per 2 sole risposte complete. **Squalificato** per inaffidabilita' pratica, indipendentemente da qualunque vantaggio teorico di "intelligenza".

**Bug di ambiente trovato e corretto durante il bake-off**: Ollama teneva in memoria **2 modelli contemporaneamente** fra un'invocazione dello script e la successiva (keep_alive di default 5 minuti), causando un vero esaurimento RAM (arrivata a 1.18GB liberi, un task ucciso dal sistema per low-memory). Corretto scaricando esplicitamente ogni altro modello (`keep_alive:0`) prima di ogni run - rimedio ambientale legittimo, non lavoro scientifico.

**Punteggio finale pesato** (reliability/structured-output/coding/constraint-compliance/hallucination-resistance pesati piu' della sola latenza, per istruzione esplicita del task):

| Modello | Score | Note |
|---|---|---|
| **ministral-3:3b** | **0.9764** | 100% schema compliance, 100% coding pass, tool-calling nativo funzionante, nessuna allucinazione trovata |
| qwen2.5:3b-instruct | 0.911 | baseline solido, gia' noto |
| gemma3:4b | 0.9001 (corretto da 0.975) | vedi allucinazione trovata sotto |
| qwen2.5:7b-instruct | 0.8879 | superato su ogni metrica dal nuovo candidato |
| qwen3:4b | **0.4451** | squalificato, 88% timeout rate |

**Correzione manuale applicata (verifica umana/Claude, non automatica)**: gemma3:4b nel task B (distinguere un campo mancante) ha **inventato/mescolato l'outcome del candidato SBAGLIATO** invece di dichiarare `NOT_AVAILABLE` - una vera allucinazione non rilevata dall'euristica a keyword automatica, trovata leggendo il testo grezzo. Inoltre Ollama riporta esplicitamente `"gemma3:4b does not support tools"` (verificato via chiamata diretta) - nessun tool-calling nativo. Entrambi i fattori corretti manualmente nello score, spostando gemma3:4b dal 1° al 3° posto.

## Fase 11-13 — Selezione, routing update, pilot REALE

**Selezionato `ministral-3:3b` per ENTRAMBI i ruoli** (LOCAL_FAST e LOCAL_STRONG) - primo in classifica su ogni metrica misurata, unico (con i baseline Qwen2.5, entrambi inferiori) con tool-calling nativo verificato. Nessun secondo modello ha dimostrato un vantaggio reale sufficiente da giustificarne due diversi su questo hardware (esplicitamente permesso dal task).

`agent_capability_registry_v1.json` scritto e validato contro `contracts/agent-capability-registry.schema.json` - 2 agenti, capacita' dichiarate SOLO quelle dimostrate nel bake-off.

**Pilot REALE** (stesso task della fase precedente, fallito 4/4 con qwen2.5 3B/7B): backfill `temporal_concentration` + `exit_efficiency` (nuova formula esplicita: frazione della distanza entry→TP catturata all'uscita) per BREAKOUT_ACC e ORDER_BLOCK. Migliorie deliberate rispetto al pilot precedente: **nessun file di riferimento di stile nel prompt** (causa nota di copia letterale di identificatori), harness deterministico per import/invocazione, gestione delle eccezioni di rete (un bug trovato: un timeout crashava l'intero script invece di attivare il retry delimitato - corretto).

**Risultato: 4/4 sotto-task risolti correttamente**, verificati indipendentemente con calcoli di riferimento scritti separatamente da Claude. Trovato e corretto anche un secondo bug, questa volta nel VERIFICATORE di Claude stesso (non nel modello): un confronto `==` troppo rigido su float ha prodotto un falso negativo per rumore di arrotondamento (~1e-15, dovuto a ordine di somma diverso) - corretto con confronto tollerante (`math.isclose`), documentato trasparentemente in un artifact separato (`pilot_run_v2_result_CORRECTED_v1.json`) senza toccare il file grezzo originale. **Primo successo reale del worker locale su questo task in tutto il progetto.**

## Fase Extra — Agent Shell Bake-Off

- **Ollama diretto**: nessun blocco, headless/automation ottima, zero overhead aggiuntivo, gia' dimostrato funzionante in questa fase.
- **OpenCode**: **richiede context minimo 64K** (confermato dalla documentazione ufficiale Ollama) - incompatibile, 8x oltre il tetto pratico di questo hardware.
- **Hermes Agent**: stesso blocco di contesto (64K), **richiede WSL2** su Windows (ambiguita' della fase precedente risolta), e la documentazione ufficiale raccomanda di bindare Ollama su `0.0.0.0` per l'accesso da WSL2 - **motivo di sicurezza aggiuntivo** per rimandarlo, in conflitto diretto col vincolo "non esporre Ollama pubblicamente" gia' stabilito.
- Claude Code escluso dal confronto per istruzione esplicita dell'utente (non e' un LOCAL_AGENT_RUNTIME gratuito di default).

**Decisione**: `OLLAMA_DIRECT` confermato, `HERMES_DEFERRED` e `OPENCODE_DEFERRED` (stesso motivo di fondo, Hermes con un motivo di sicurezza in piu').

## Fase 15 — Storage cleanup (raccomandazione, nessuna cancellazione eseguita)

**Tenere**: `ministral-3:3b` (selezionato), `qwen2.5:3b-instruct` (baseline economico, 1.9GB). **Tenere come opzionale**: `gemma3:4b` (2° miglior punteggio corretto, 3.3GB). **Raccomandato rimuovere** (richiede autorizzazione utente): `qwen2.5:7b-instruct` (4.7GB, superato su ogni metrica) e `qwen3:4b` (2.5GB, squalificato) - 7.2GB recuperabili, non urgente (262GB liberi).

## Decisione finale

**`LOCAL_MODEL_SELECTION_VALIDATED`**

Il bake-off ha identificato un modello misurabilmente migliore dei baseline su ogni metrica testata, E questo modello ha risolto per la prima volta il pilot reale di coding fallito 4/4 volte nella fase precedente. Selezione validata empiricamente.

## Deliverables

`build_bakeoff_benchmark.py`, `bakeoff_tasks.py`, `build_toolcalling_probe.py`, `build_bakeoff_scorecard.py`, `build_agent_capability_registry.py`, `run_pilot_worker_v2.py`, `fix_pilot_v2_float_comparison.py`, `build_bakeoff_final_report.py`, `verify_bakeoff.py`, 5 file di benchmark grezzo, `toolcalling_probe_results_v1.json`, `bakeoff_scorecard_v1.json`, `agent_capability_registry_v1.json`, `pilot_run_v2_result_v1.json` + `_CORRECTED_v1.json`, `bakeoff_final_report_v1.json`, `server/tests/test_orchestrator_v1_bakeoff.py`, questo vault report.

## Vincoli preservati

Nessuna modifica a `MQL5/`, `Product-Platform/`. Nessuna fase Phase 7 tracciata modificata. Nessun modello/cache/segreto/credenziale committato. Nessun deploy. Nessuna optimization. Nessun backtest. Nessuna cancellazione automatica di modelli. Nessuna installazione automatica di Hermes/OpenCode/Claude Code dal launcher Ollama.

## Regressione

`verify_bakeoff.py`: PASSED (ricontrollo indipendente contro i dati grezzi, incluso il ricalcolo del match tollerante del pilot e la riconferma del timeout rate di qwen3 dai file grezzi). Suite `server/orchestrator_v1/` + nuovo test file: **35/35 pass**.

---

```
PUSH RECOVERY: dd6f5a5 pubblicato con successo (email GitHub verificata)

LOCAL MODEL BAKE-OFF V1: COMPLETATO

SHORTLIST: Qwen3 4B, Ministral-3 3B, Gemma3 4B - tutti disponibili,
  scaricati (8.8GB), licenze verificate (Apache 2.0 x2, Gemma Terms
  x1)

SCOPERTA MAGGIORE: qwen3:4b thinking mode NON disattivabile
  (ne' API ne' prompt) - 88% timeout rate nel bake-off completo -
  SQUALIFICATO nonostante potenziale teorico superiore

BUG AMBIENTALE TROVATO E CORRETTO: Ollama teneva 2 modelli in RAM
  insieme fra run consecutivi (keep_alive default) - causato un vero
  OOM (1.18GB liberi, task ucciso) - fix: unload esplicito prima di
  ogni run

SCORECARD PESATA (reliability/coding/hallucination-resistance >
  latenza pura): ministral-3:3b VINCE (0.9764) su tutti i baseline
  Qwen2.5 e su gemma3:4b (0.90 dopo correzione manuale di
  un'allucinazione trovata leggendo il testo grezzo + assenza di
  tool-calling nativo confermata dal runtime)

SELEZIONE: ministral-3:3b per LOCAL_FAST E LOCAL_STRONG (nessun
  secondo modello porta vantaggio reale su questo hardware)

PILOT REALE (stesso task fallito 4/4 nella fase precedente):
  4/4 RISOLTO CORRETTAMENTE con ministral-3:3b - primo successo
  reale del worker locale in tutto il progetto. 2 bug trovati e
  corretti nell'HARNESS di Claude (non nel modello): gestione
  eccezioni di rete, confronto float troppo rigido nel verificatore
  (corretto con documentazione trasparente separata, file grezzo
  originale intatto)

AGENT SHELL: OpenCode e Hermes entrambi bloccati dallo stesso
  vincolo (context minimo 64K, 8x oltre il tetto pratico di questo
  hardware) - Hermes con un motivo di sicurezza aggiuntivo (richiede
  bind 0.0.0.0, non solo localhost) - OLLAMA_DIRECT confermato

STORAGE CLEANUP: raccomandato rimuovere qwen2.5:7b-instruct e
  qwen3:4b (7.2GB, non urgente) - nessuna cancellazione automatica
  eseguita

DECISIONE: LOCAL_MODEL_SELECTION_VALIDATED
```
