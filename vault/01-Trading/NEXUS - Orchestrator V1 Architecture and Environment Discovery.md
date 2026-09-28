# NEXUS - Orchestrator + Local Agent Architecture & Environment Discovery V1

**Baseline:** `227965b` (Phase 7.27, GOLD BUY-Dominance Benchmark Test). Nessuna modifica MQL5/logiche di trading. Nessuna optimization. Nessun deploy. Nessun nuovo backtest. Nessuna installazione pesante eseguita.

**Obiettivo**: (A) specificare l'architettura canonica di orchestrazione NEXUS per il routing di task di ricerca/sviluppo fra Tier 0-4 (deterministico → locale → locale forte → Claude → Codex); (B) ispezionare l'hardware/runtime/modelli locali già presenti su questa macchina per raccomandare il modello locale più adatto, senza installare nulla a caso; (C) classificare esempi reali di task Phase 7 e definire il primo pilota + roadmap.

---

## Riconciliazione con l'architettura esistente (fatta PRIMA di scrivere qualunque spec)

Prima di progettare qualunque cosa, ho verificato cosa esiste già nel repo per non duplicare o contraddire decisioni prese altrove:

- **`docs/NEXUS_MASTER_PROJECT.md` Blocco A3.8** è già una spec normativa completa per gli agenti AI del **trading live** (COACH_AGENT, RISK_ADVISOR, ecc.), con una scala di rischio A0-A5 e un modello di confidence `VERY_LOW/LOW/MEDIUM/HIGH`, e l'invariante "l'AI non può bypassare il Risk Engine". Questo documento **riusa la stessa scala A0-A5** per `risk_level` e **diverge deliberatamente** sulla confidence (`HIGH/MEDIUM/LOW/UNKNOWN` — `UNKNOWN` qui significa "verifier non eseguito", un caso che A3.8 non necessita nel suo dominio) — divergenza dichiarata esplicitamente, non un errore.
- **`server/research_control_plane.py`** (di un secondo autore, "Codex") **implementa già** un Vault contract in sola lettura sui registry di Phase 7.26 — questo documento lo **descrive come pattern di riferimento**, non lo ridisegna. Riusato letteralmente il dict `TENANT` (`tenant_id`/`ea_instance_id`/`account_scope_id`) e la forma `provenance` (`source_artifact`/`canonical_sha256`/`generated_at`/`mode`) già in uso lì.
- **`phase7_19/source_of_truth_hierarchy_v1.json`** già cita "Jarvis" come livello di autorità più basso, mai autoritativo — coerente con (non contraddetto da) il ruolo di Jarvis definito qui.
- **`vault/01-Trading/_phase4_artifacts/agentic_architecture_research.md`** (survey di 9 architetture agentic/quant reali) valida indipendentemente 6 pattern usati in questa spec (stage decisione/rischio/esecuzione separati, approvazione umana come cittadino di prima classe, audit trail immutabile come primitiva di design, ecc.).
- **Prova empirica**: ogni commit Claude di Phase 7.2x in questa sessione è stato seguito entro ore da un commit "ui: sync/add" dell'altro autore — la divisione TIER 3 (Claude)/TIER 4 (Codex) descritta qui **è già in atto in pratica**, non ipotetica.

Nessuna collisione di nomi trovata per i termini nuovi (TASK_MANIFEST, AGENT_CAPABILITY_REGISTRY, ROUTING_POLICY, Hermes, Ollama).

## Parte A — Architettura (23 punti)

Documento narrativo completo: `docs/architecture/18_ORCHESTRATOR_AGENT_ROUTING_V1.md`. Punti chiave:

- **Principio**: premium sempre come escalation, mai default — `DETERMINISTIC → LOCAL → LOCAL_STRONG → PREMIUM`.
- **5 Tier** (0 deterministico, 1 locale economico, 2 locale forte, 3 Claude, 4 Codex + specialist opzionale).
- **6 schemi JSON machine-readable** in `contracts/` (stile draft-07 già usato da `strategy-registry.schema.json`): `task-manifest`, `agent-capability-registry`, `context-packet`, `result-packet`, `nexus-event` — validati con un validatore JSON Schema scritto ad hoc (**solo stdlib**, stessa scelta già fatta da `contracts/validate_registry.py`: "niente jsonschema, eseguibile ovunque").
- **Routing policy** con capability matching, risk gate, quota awareness, retry delimitato (**1 solo retry locale**, poi classificazione della causa ed escalation — mai loop infiniti).
- **Confidence model** derivato da verifier/test/provenance, mai dall'autovalutazione del modello.
- **Event architecture** (`NEXUS_EVENT_V1`, 21 tipi) esplicitamente **separata** dall'Event Ledger di trading già esistente (`04_EVENT_LEDGER_SPEC.md`) — stesso pattern di envelope, domini diversi, per non mischiare stato operativo e stato di processo.
- **Trading boundary**: `LLM → MT5 BUY` vietato per costruzione; consentito solo `strategy → risk engine → portfolio engine → execution policy → approval → MT5` — stessa regola di A3.8, riaffermata indipendentemente.
- **Jarvis**: mai source of truth, mai risk engine, mai cervello di trading autonomo — solo assistente/interfaccia di query/notifica/approvazione.

## Parte B — Environment Discovery (hardware reale, non stimato)

Misurato **direttamente** in questa sessione (CIM/WMI, `command -v`, ricerca su disco, `gh auth status`) — non assunto:

| | Valore osservato |
|---|---|
| OS | Windows 11 Pro, build 26100 |
| CPU | Intel i5-7200U (2 core / 4 thread, 2017) |
| RAM | 19,85GB totale, 9,01GB liberi al momento della misura |
| GPU | Intel HD 620 integrata — **nessuna accelerazione utile per LLM** |
| Disco libero | 279,63GB |
| Runtime locali installati | **Nessuno** (Ollama/Docker/LM Studio/llama.cpp/vLLM tutti assenti) |
| Modelli locali esistenti | **Nessuno** (ricerca su disco negativa, incl. cache HF/GPT4All) |
| Python/Node/Git/gh | Presenti e funzionanti (gh autenticato, push confermato) |

**Questo hardware esclude modelli grandi (13B+) e context enormi (128K)** — non per principio generale, per il budget CPU/RAM realmente osservato (dual-core mobile del 2017, nessuna GPU).

### Raccomandazione finale

- **Runtime**: **Ollama** — unico fra i candidati con servizio Windows nativo + API HTTP OpenAI-compatible stabile, zero login. `llama.cpp` diretto = stesso motore sotto Ollama con più lavoro manuale; `LM Studio` = pensato per uso interattivo via GUI, non per un worker headless; `vLLM` = **escluso**, incompatibile con Windows/CPU-only.
- **Modello primario**: `qwen2.5:7b-instruct-q4_K_M` — **modello veloce opzionale**: `qwen2.5:3b-instruct-q4_K_M`.
- **Perché Qwen2.5 e non Llama/Mistral/DeepSeek**: licenza Apache-2.0 **senza login** (Llama 3.2 richiede account HF con licenza community per il repo ufficiale); affidabilità JSON/tool-calling documentata come punto di forza specifico della famiglia per la sua taglia; multilingue italiano/inglese esplicito; DeepSeek-R1-distill scartato perché il reasoning esteso produce risposte troppo lunghe per una CPU lenta; **"Hermes"** interpretato come famiglia di fine-tune NousResearch (non un runtime a sé, nessun riferimento trovato nel repo/macchina) — candidato valido ma non testato, da chiarire con l'utente se si intendeva altro.
- **Context**: 8192 default, 16384 se necessario, **mai** 128K su questa macchina.
- **Nessuna installazione eseguita** in questa fase (per istruzione esplicita del task).

## Parte C — Migration & Pilot

- **Matrice di classificazione** (`migration_matrix_v1.json`) su 8 esempi REALI di questa sessione: ricostruire registry → DETERMINISTIC; riassumere un log → LOCAL_FAST; **backfill temporal_concentration/exit_efficiency BREAKOUT_ACC+ORDER_BLOCK → LOCAL_STRONG**; decidere se la dominanza BUY riflette il regime → CLAUDE_REQUIRED; integrare i registry nel Control Plane frontend → CODEX_REQUIRED.
- **Primo pilota** (`first_pilot_spec_v1.json`): il backfill temporal/exit-efficiency, con TASK_MANIFEST completo, passi deterministici vs passi per il modello locale, regola di verifica e di escalation — **non eseguito**, bloccato dal runtime locale non ancora installato.
- **Roadmap V0-V8** (`roadmap_v1.json`): schemi+ledger → worker deterministico → runtime locale → router+escalation → Control Plane → Jarvis testo → Jarvis voce → MT5 sola lettura → azioni di approvazione/trading (ultimo stadio per disegno, coerente con la gerarchia di autorità di A3.8).

## Decisione finale

**`ORCHESTRATOR_ARCHITECTURE_READY`** + **`LOCAL_RUNTIME_NEEDS_SETUP`**

L'architettura è specificata e riconciliata con quanto già esiste; il runtime locale richiede un'installazione (~6,9GB, nessun login, stimata) prima che il primo pilota possa essere eseguito realmente.

## Deliverables

`contracts/task-manifest.schema.json`, `contracts/agent-capability-registry.schema.json`, `contracts/context-packet.schema.json`, `contracts/result-packet.schema.json`, `contracts/nexus-event.schema.json`, `docs/architecture/18_ORCHESTRATOR_AGENT_ROUTING_V1.md`, `server/orchestrator_v1/` (10 builder Python + `nxs_schema_validator.py` + `example_instances/` + 7 artifact JSON + verificatore + test), questo vault report.

## Vincoli preservati

Nessuna modifica a `MQL5/`, `Product-Platform/`. Nessun file `contracts/` pre-esistente modificato (solo 5 nuovi schemi aggiunti). Nessun file `docs/architecture/01-17` toccato. Nessuna fase Phase 7 tracciata modificata. Nessuna installazione pesante. Nessun deploy. Nessuna optimization. Nessun nuovo backtest.

## Regressione

Suite `server/orchestrator_v1/`: 27/27 pass. Suite Phase 7 completa: invariata rispetto a Phase 7.27 (nessun file Phase 7 tracciato toccato da questa fase). `contracts/validate_registry.py`: OK (83 strategie, nessuna regressione).

**Nota per l'altro workstream (Codex/Control Plane) — NON corretta in questa fase, fuori perimetro**: `server/tests/test_research_control_plane_v2.py::test_safety_net_registries_are_projected_without_reinterpretation` fallisce ora (`assert 9 == 8`) perché contiene un conteggio hardcoded (`experiment_count == 8`, `hypothesis_count == 8`) — Phase 7.27 ha aggiunto legittimamente una 9ª hypothesis e un 9° experiment al registry (esattamente lo scopo dichiarato della Safety Net: crescere nel tempo). Questo è un effetto collaterale ATTESO di un aggiornamento autorizzato ai registry viventi, non un bug introdotto da questa fase — segnalato esplicitamente perché il fix (rendere l'asserzione un limite inferiore, non un valore esatto) appartiene al codice/test di quell'altro autore, non toccato qui. Riscontrato anche un secondo problema, puramente ambientale e pre-esistente: 68 errori `PermissionError: [WinError 5] Accesso negato` sulla pulizia della directory temp di pytest su Windows — non correlato a nessuna modifica di questa sessione.

---

```
7.27: GOLD BUY-DOMINANCE BENCHMARK TEST - COMPLETATO
ORCHESTRATOR V1: ARCHITETTURA + ENVIRONMENT DISCOVERY - COMPLETATO

RICONCILIAZIONE (prima di scrivere): A3.8 (docs/NEXUS_MASTER_PROJECT.md)
  gia' normativo per AI di trading live - questo documento e' la
  controparte per task di ricerca/sviluppo, riusa risk-scale A0-A5,
  diverge deliberatamente sulla confidence (UNKNOWN = verifier non
  eseguito). Vault contract GIA' implementato da Codex
  (research_control_plane.py) - descritto, non ridisegnato.

ARCHITETTURA: 5 tier, 6 schemi JSON (contracts/, draft-07, validati
  con validatore custom solo-stdlib), routing policy con retry
  delimitato (1 solo tentativo locale), confidence da verifier/test/
  provenance (mai autovalutazione), trading boundary riaffermato
  (LLM non puo' mai ordinare direttamente a MT5), Jarvis mai source
  of truth

HARDWARE REALE (misurato, non stimato): i5-7200U 2017 (2 core/4
  thread), 20GB RAM (9GB liberi), NESSUNA GPU utile, NESSUN runtime
  locale installato, NESSUN modello locale gia' presente

RACCOMANDAZIONE: Ollama (unico compatibile con Windows headless
  automation) + qwen2.5:7b-instruct-q4_K_M (primario, licenza senza
  login) + qwen2.5:3b-instruct-q4_K_M (veloce, opzionale) - context
  8K/16K, MAI 128K su questo hardware - nessuna installazione
  eseguita

PILOTA: backfill temporal_concentration/exit_efficiency BREAKOUT_ACC
  + ORDER_BLOCK (gia' in cima alla Research Priority Queue) - spec
  completa, NON eseguito (runtime non pronto)

DECISIONE: ORCHESTRATOR_ARCHITECTURE_READY + LOCAL_RUNTIME_NEEDS_SETUP

PROSSIMO: revisione umana della raccomandazione -> installazione
  Ollama+Qwen2.5 -> primo pilota locale -> se supera verifier/test,
  V1 del worker deterministico
```
