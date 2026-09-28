# 18. NEXUS Orchestrator + Local Agent Routing Architecture V1

## 0. Scope e relazione con l'architettura esistente

Questo documento specifica il routing dei **task di ricerca/sviluppo** (research, code, maintenance, backfill) fra esecutori di costo/rischio crescente — **non** l'architettura AI del trading live, che è **già normativa** in `docs/NEXUS_MASTER_PROJECT.md`, Blocco A3.8 ("AI Architecture, Multi-Agent System, Memory, Orchestration and Decision Governance"). I due documenti governano domini distinti e non si sovrappongono:

| | A3.8 (esistente) | Questo documento (nuovo) |
|---|---|---|
| Dominio | Agenti che toccano stato di trading live (Coach, Risk-Advisor, Incident-Assistant) | Agenti che eseguono task di ricerca/sviluppo (Claude, Codex, agenti locali) |
| Scala di rischio | A0-A5 (azioni AI) | Riusa la STESSA scala A0-A5 per `risk_level` nel TASK_MANIFEST — non una scala nuova |
| Confidence | `VERY_LOW/LOW/MEDIUM/HIGH` | `HIGH/MEDIUM/LOW/UNKNOWN` — **divergenza intenzionale**, vedi §8 |
| Invariante "AI non bypassa il Risk Engine" | Sì, invariante #2 | Riaffermato indipendentemente al §18 (Trading boundary) — stessa regola, due punti di enforcement |
| Event ledger | `04_EVENT_LEDGER_SPEC.md` (eventi EA/posizione/ordine/deal) | `NEXUS_EVENT_V1` (§11) — stesso pattern di envelope immutabile, vocabolario di eventi completamente diverso (task/agente/esperimento) — **due ledger separati per disegno**, non uno fuso, per non mischiare stato operativo di trading con stato di processo di ricerca |
| Vault contract | — | Già **implementato** in pratica da `server/research_control_plane.py` + `strategy_census_read_model.py` (letto in sola lettura dai registry Phase 7.26) — questo documento lo **descrive come pattern di riferimento**, non lo ridisegna |
| Jarvis | "Jarvis" citato in `phase7_19/source_of_truth_hierarchy_v1.json` come livello di autorità più basso, mai autoritativo | Formalizzato al §19 — stessa posizione nella gerarchia, ora con un contratto esplicito |

Validazione indipendente: `vault/01-Trading/_phase4_artifacts/agentic_architecture_research.md` (Settembre 2026) sintetizza 6 pattern trasversali osservati in 9 architetture agentic/quant reali (Gordon, OpenAlice, Freqtrade, NautilusTrader, Hummingbot, ecc.) — citati esplicitamente nelle sezioni pertinenti sotto, perché confermano indipendentemente le stesse scelte fatte qui.

Prova empirica già in corso: durante le Phase 7.21-7.27 di questa sessione, ogni commit di ricerca Claude è stato seguito entro ore da un commit "ui: sync/add …" di un secondo autore che integra gli artifact nel Control Plane frontend/backend — **la divisione TIER 3 (Claude) / TIER 4 (Codex) di questo documento descrive un pattern già in atto**, non ipotetico.

---

## 1. Principio fondamentale

**Premium agents are escalation, never default.**

Ordine preferenziale rigido:

```
DETERMINISTIC TOOLING → LOCAL AGENT → LOCAL STRONG AGENT → PREMIUM SPECIALIST
```

Zero LLM quando una soluzione deterministica è sufficiente — confermato dal pattern trasversale #4 di `agentic_architecture_research.md` (leakage/lookahead detection come tooling *nominato*, es. `freqtrade lookahead-analysis`, mai delegato a un LLM).

## 2. Execution tiers

| Tier | Nome | Esempi di task | Rischio tipico |
|---|---|---|---|
| **0** | Deterministic | Python, builder, verifier, pytest, git checks, artifact processing, MT5 run management, metric computation, registry rebuild | A0 |
| **1** | Local cheap agent | summaries, report standard, file classification, trasformazioni di routine, documentazione, log parsing, Vault updates, piccoli fix | A0-A1 |
| **2** | Local strong agent | debugging moderato, sviluppo Python, data analysis, generazione builder, code review, piccoli componenti backend/frontend | A1-A2 |
| **3** | Claude | metodologia scientifica, causal reasoning, experiment design, adjudication, architettura di ricerca, interpretazione scientifica ad alto rischio | A2-A3 |
| **4** | Codex | implementazioni complesse multi-file, major refactor, architettura backend/frontend, integrazione Product Platform, modifiche codebase-wide | A2-A3 |
| Specialist (opzionale) | ChatGPT/altri provider | second opinion / fallback quando Claude e Codex sono entrambi non disponibili o in disaccordo | dipende dal task delegato |

Schema machine-readable dei task type/priority/executor: `contracts/task-manifest.schema.json`.

## 3-4. TASK_MANIFEST_V1 e AGENT_CAPABILITY_REGISTRY_V1

Definiti come JSON Schema draft-07 (stessa convenzione di `contracts/strategy-registry.schema.json`: `additionalProperties:false`, `required` espliciti, enum `SCREAMING_SNAKE`):

- **`contracts/task-manifest.schema.json`** — 26 campi richiesti, incl. `tenant_id`/`account_scope_id` nella stessa forma del dict `TENANT` già usato in `server/research_control_plane.py` (non una forma nuova).
- **`contracts/agent-capability-registry.schema.json`** — provider-agnostic (`provider` è una stringa libera: `"anthropic"`, `"openai"`, `"local-ollama"`, ecc.), un record per agente/runtime.

Esempi validati: `server/orchestrator_v1/example_instances/validated_examples_v1.json` (validati con `nxs_schema_validator.py`, solo stdlib — stessa scelta di `contracts/validate_registry.py`, "niente jsonschema, eseguibile ovunque").

## 5. ROUTING_POLICY_V1

```
IF deterministic workflow exists
    → TIER 0
ELSE IF local capability sufficient AND risk acceptable
    → TIER 1/2 (LOCAL)
ELSE IF scientific reasoning required
    → TIER 3 (CLAUDE)
ELSE IF complex multi-file coding required
    → TIER 4 (CODEX)
ELSE
    → LOCAL + VERIFIER (tentativo economico, poi verifica indipendente)
```

Fattori di routing, in ordine di valutazione:
1. **Capability matching** — `required_capabilities` del task vs `capabilities` dell'agente (AGENT_CAPABILITY_REGISTRY_V1).
2. **Risk gates** — `risk_level`/`scientific_risk`/`code_risk`/`financial_risk` del task vs `trust_level`/`allowed_task_types` dell'agente. Un task `financial_risk=HIGH` non può MAI essere assegnato a un agente con `trust_level=SANDBOXED`.
3. **Quota awareness** — `quota_state` (vedi §21).
4. **Budget** — `cost_class` dell'agente, preferendo sempre il più economico capace.
5. **Availability** — `availability=ONLINE` richiesto.
6. **Retry/escalation** — vedi §7.
7. **Context size** — se il task richiede più contesto di quanto l'agente locale possa gestire in modo affidabile (vedi §32 per la stima pratica su questo hardware), escalation automatica.
8. **Expected information gain** — stesso principio già usato in `RESEARCH_PRIORITY_QUEUE_V1` (Phase 7.26): non instradare un task costoso quando il guadagno atteso è basso.

## 6. Premium gating

Task che **non devono mai** usare un agente premium quando esiste un'alternativa deterministica/locale:

registry rebuild · test execution · artifact collection · metric computation · standard report · git housekeeping · waiting/polling · log parsing · routine backfill · monitoring · file conversion · hash/provenance checks

Premium **solo** quando: (a) richiede giudizio scientifico/causale, (b) richiede un refactor multi-file complesso, (c) un tentativo locale è già fallito e la causa è stata classificata come metodologica o di codice complesso (vedi §7).

## 7. Retry/escalation

```
LOCAL ATTEMPT
  → VERIFY
  → PASS = DONE
  → FAIL
    → 1 retry delimitato (stesso agente, stesso task, nessuna modifica di scope)
    → FAIL
      → classifica causa:
          methodological  → TIER 3 (Claude)
          complex code    → TIER 4 (Codex)
          environment/tool → rimedio deterministico (TIER 0), poi ri-tenta TIER locale
          unknown         → APPROVAL_REQUIRED (revisione umana)
```

Niente loop infiniti: **al massimo 1 retry locale**, mai un secondo retry silenzioso allo stesso tier.

## 8. Confidence model

Stati: `HIGH / MEDIUM / LOW / UNKNOWN` (campo `confidence` di `contracts/result-packet.schema.json`).

**Divergenza intenzionale da A3.8** (che usa `VERY_LOW/LOW/MEDIUM/HIGH`): qui `UNKNOWN` non è "il verificatore ha dato un segnale debole" (quello sarebbe `LOW`) ma **"il verificatore non è stato eseguito affatto"** — una distinzione che A3.8 non necessita nel suo dominio (un'azione di trading ha sempre un verdetto del Risk Engine), ma che è essenziale qui perché un tentativo locale può fallire *prima* di raggiungere la fase di verifica.

La confidence **non è mai l'autovalutazione del modello** — deriva da:
- esito del verifier (booleano, non un'opinione)
- esito dei test (passed/failed, non un'opinione)
- completezza degli artifact attesi (`expected_artifacts` del manifest, tutti presenti?)
- validità dello schema (l'output rispetta `contracts/*.schema.json`?)
- provenance (hash canonico presente e coerente?)
- contradiction detection (il risultato contraddice un artifact canonico già esistente? — stesso principio già applicato in Phase 7.26 `verify_leakage.py`)

`HIGH` richiede TUTTI e 6 questi segnali positivi, non un singolo "sembra corretto" del modello.

## 9-10. CONTEXT_PACKET_V1 e RESULT_PACKET_V1

- **`contracts/context-packet.schema.json`** — pacchetto minimo per un'escalation a premium: obiettivo, finding rilevanti, artifact canonici (stessa forma `source_artifact/canonical_sha256/generated_at/mode` già usata da `research_control_plane.py`), HEAD corrente, file consentiti, domanda esatta, tentativi precedenti, fallimenti, test, vincoli, azioni vietate, output richiesto. **Scopo esplicito**: non far rileggere tutto il repo a Claude/Codex ad ogni escalation.
- **`contracts/result-packet.schema.json`** — ogni esecutore (Tier 0-4) lo restituisce a fine task: `task_id`, `executor`, timing, file letti/modificati, comandi eseguiti, artifact creati, esito test/verifier, commit/push status, decisione, confidence, limitazioni, problemi irrisolti, task successivi suggeriti, necessità di escalation.

## 11. NEXUS_EVENT_V1 ed Event architecture

`contracts/nexus-event.schema.json` — 21 tipi di evento (`TASK_CREATED` … `APPROVAL_DENIED`), envelope minimo (`event_id, event_type, task_id, timestamp, tenant_id, payload`). Controparte di processo del già esistente Event Ledger di trading (`04_EVENT_LEDGER_SPEC.md`) — vedi tabella di riconciliazione al §0.

## 12. Activity Ledger

Append-only, auditabile. Jarvis (§19) e qualunque UI **devono** rispondere a "cosa è successo / chi ha fatto cosa / quando / risultato / prossimo step" leggendo **solo** da qui — mai dalla memoria di un LLM. Pattern validato indipendentemente: `agentic_architecture_research.md` cita il decision log HMAC-chained di Gordon e la convenzione di OpenAlice ("ogni azione è un commit diffabile") come lo stesso principio applicato in due codebase reali distinte.

Implementazione concreta rimandata a **V0** della roadmap (§40) — non decisa in questa fase se JSONL append-only o SQLite locale (dettaglio implementativo, non architetturale).

## 13. Queue architecture

Code: `RESEARCH · CODE · MARKET · MT5_RUNS · MAINTENANCE · DEPLOY · APPROVALS`. Ognuna supporta: dipendenze fra task, priorità, retry, parallelismo, lock, stato bloccato, attesa quota.

## 14. Parallel execution / DAG

```
dataset ready
 ├─ MFE/MAE
 ├─ concentration
 ├─ cost stress
 ├─ temporal analysis
 └─ visual generation
       ↓
      JOIN
       ↓
 interpretation (se richiesta interpretazione scientifica → TIER 3)
```

Pattern già dimostrato in pratica nelle Phase 7.21/7.22/7.25 (baseline economics, concentration, cost stress, temporal robustness, visual audit sono tutti calcolabili indipendentemente da un unico dataset canonico, poi riuniti nella decision card).

## 15. Async MT5

```
agent requests run → orchestrator crea un job → agente termina (non attende)
→ MT5 worker esegue il run → RUN_COMPLETED (evento)
→ estrazione/verifica locale (TIER 0)
→ premium richiamato SOLO se serve interpretazione
```

Un agente premium **non deve mai** attendere sincronamente un run MT5 — pattern già seguito manualmente in questa sessione (Phase 7.23/7.25: lancio → poll leggero in background → notifica → raccolta), qui formalizzato.

## 16. Vault contracts

**Già implementato**, non da ridisegnare: `server/research_control_plane.py` + `strategy_census_read_model.py` + `strategy_pipeline_read_model.py` leggono in **sola lettura** i registry Phase 7.26 (`experiment_registry_v1.json`, `hypothesis_registry_v1.json`, `data_exposure_registry_v1.json`, `cross_strategy_learning_packets_v1.json`, `failure_map_v1.json`, `research_priority_queue_v1.json`, `cross_strategy_synthesis_v1.json`) e li proiettano verso `frontend/src/pages/ResearchControlPlanePage.jsx` — docstring esplicita: *"non deriva mai verdetti scientifici"*. Questo documento formalizza il pattern (`Strategies · Research · Experiments · Hypotheses · Runs · Tasks · Agents · Decisions · Market · Trading · Activity`) come contratto di riferimento per **qualunque** nuovo consumer futuro — **Jarvis non è mai source of truth** (vedi §19).

## 17. Approval model

| Classe | Esempi |
|---|---|
| **AUTO** | lettura, calcoli, test, reporting, registry rebuild |
| **REVIEW_REQUIRED** | modifiche di codice significative, cambi di verdetto scientifico, deploy |
| **EXPLICIT_USER_APPROVAL** | live trading, aumento di rischio, credenziali/config, azioni distruttive, deploy in produzione (se la policy lo richiede) |

Campo `approval_required` in `TASK_MANIFEST_V1`.

## 18. Trading boundary

**Vietato per costruzione**: `LLM → MT5 BUY`.

**Consentito**: `strategy → risk engine → portfolio engine → execution policy → approval → MT5`.

Questa è la **stessa regola** già codificata come invariante AI #2 in A3.8 ("l'AI non può bypassare il Risk Engine") — riaffermata qui indipendentemente perché il dominio di questo documento (task locali/premium) è un secondo punto di enforcement, non un'eccezione a quello esistente.

## 19. Jarvis role

**Jarvis è**: personal assistant · query interface · notification layer · task request interface · approval interface.

**Jarvis NON è**: source of truth · autorità scientifica · risk engine · cervello di trading autonomo.

Precedente diretto già nel repo: `phase7_19/source_of_truth_hierarchy_v1.json` — *"narrative_interpretation: Claude/Jarvis/analista umano — non può MAI modificare i livelli sottostanti, solo commentarli."* Questo documento estende la stessa regola a tutte le interazioni Jarvis, non solo all'interpretazione narrativa.

## 20. Local runtime abstraction

Nessuna dipendenza rigida da un singolo framework. Compatibilità richiesta con: Hermes (family di fine-tune, non un runtime a sé — vedi §29-30), Ollama, llama.cpp, vLLM, endpoint locali OpenAI-compatible. Scelta pratica per **questo** hardware in Parte B (§24-37) — non vincolante per hardware futuri diversi.

## 21. Quota/budget awareness

Stati provider: `AVAILABLE · LOW_QUOTA · EXHAUSTED · OFFLINE · RATE_LIMITED` (campo `quota_state` in `AGENT_CAPABILITY_REGISTRY_V1`). Il routing deve minimizzare l'uso premium per costruzione (§1, §6), non solo quando la quota è bassa.

## 22. Cache / don't recompute

Prima di creare un nuovo task: interrogare il Vault (registry Phase 7.26 / Control Plane), verificare se un artifact canonico già esiste per quella domanda, verificarne la freshness (hash/timestamp). Se esiste già un risultato canonico, riusarlo — stesso principio già applicato per costruzione in tutta questa sessione (es. Phase 7.24 non ha rilanciato un nuovo backtest quando i dati esistenti bastavano).

## 23. Security boundaries

secrets (mai in chiaro nei task manifest/result packet) · sandbox (agenti locali sempre `trust_level≤SANDBOXED` finché non promossi) · file permissions (`files_allowed`/`files_forbidden` per task) · repo write access (solo dopo verifica) · Vault write access (solo builder deterministici, mai scrittura diretta da un LLM) · production access (mai da un agente locale) · MT5 access (solo `RUN_MANAGEMENT` per agenti `FULLY_TRUSTED`) · audit logging (Activity Ledger, §12) · tenant isolation (`tenant_id`/`account_scope_id` in ogni manifest/evento).

---

## Parte B — Environment Discovery (sintesi)

Dettaglio completo e ragionamento in `server/orchestrator_v1/environment_inventory_v1.json` e `model_recommendation_v1.json`. Sintesi:

**Hardware**: Windows 11 Pro, Intel i5-7200U (2 core/4 thread, 2017), 19.85GB RAM (9GB liberi al momento della misura), **nessuna GPU utile** (Intel HD 620 integrata), 279GB disco liberi. Questo hardware esclude modelli grandi (13B+) e context enormi (128K) — non per principio generale, per il budget CPU/RAM realmente osservato.

**Runtime installati**: nessuno fra Ollama/Docker/LM Studio/llama.cpp/vLLM. Python 3.12.10, Node 24, Git 2.55, GitHub CLI 2.96 (autenticato, push funzionante) già pronti.

**Modelli locali esistenti**: nessuno (ricerca su disco negativa, incl. cache HuggingFace/GPT4All/Ollama — tutte assenti).

**Raccomandazione finale**: runtime **Ollama** (unico dei candidati con servizio Windows nativo + API HTTP stabile, senza login); modello primario **`qwen2.5:7b-instruct-q4_K_M`**, modello veloce opzionale **`qwen2.5:3b-instruct-q4_K_M`** (licenza Apache-2.0, nessun account richiesto, affidabilità JSON/tool-calling superiore ai concorrenti della stessa taglia — Llama 3.2 richiede login HF per il repo ufficiale, DeepSeek-R1-distill produce risposte troppo lunghe per CPU lenta, vLLM incompatibile con questo hardware/OS). Context raccomandato: **8192** (16384 se necessario), mai 128K su questa macchina. Nessuna installazione eseguita in questa fase.

## Parte C — Migration & Pilot (sintesi)

Matrice completa in `migration_matrix_v1.json`. Il backfill `temporal_concentration`/`exit_efficiency` per BREAKOUT_ACC/ORDER_BLOCK è classificato **LOCAL_STRONG** ed è il candidato esplicito per il primo pilota (`first_pilot_spec_v1.json`) — **non eseguito** in questa fase perché il runtime locale non è ancora installato.

Roadmap V0-V8 in `roadmap_v1.json`: schemi+ledger → worker deterministico → runtime locale → router+escalation → integrazione Control Plane → Jarvis testo → Jarvis voce → MT5 sola lettura → azioni di approvazione/trading (ultimo stadio per disegno, non per comodità).

## Decisione finale

Vedi `final_decision_card_v1.json`: **`ORCHESTRATOR_ARCHITECTURE_READY`** + **`LOCAL_RUNTIME_NEEDS_SETUP`**.
