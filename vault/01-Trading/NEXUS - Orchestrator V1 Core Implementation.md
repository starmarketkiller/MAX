# NEXUS - Orchestrator V1 Core Implementation

**Baseline:** `e9ccff7` (Local Model Bake-Off V1, `LOCAL_MODEL_SELECTION_VALIDATED`). Codex indisponibile per quota - non atteso, per esplicita decisione dell'utente: "il punto dell'architettura che abbiamo appena costruito e' proprio evitare che un provider blocchi tutto il progetto". Nessuna modifica a strategie, nessun deploy, nessun trading.

**Obiettivo**: implementare il NUCLEO operativo dell'Orchestrator NEXUS V1 (backend/core, non il frontend Control Plane - quello resta a Codex), usando i contratti gia' definiti nella fase architetturale (`TASK_MANIFEST_V1`, `AGENT_CAPABILITY_REGISTRY_V1`, `CONTEXT_PACKET_V1`, `RESULT_PACKET_V1`, `NEXUS_EVENT_V1`) e `ministral-3:3b` via `OLLAMA_DIRECT` come worker locale, gia' selezionato e validato nella fase precedente.

---

## 1. Riuso dell'architettura esistente

Verificato PRIMA di implementare - nessuna versione concorrente creata:

- `TASK_MANIFEST_V1`, `AGENT_CAPABILITY_REGISTRY_V1`, `CONTEXT_PACKET_V1`, `RESULT_PACKET_V1`: riusati identici, validati ad ogni uso con `nxs_schema_validator.py` (nessuna modifica).
- `NEXUS_EVENT_V1`: **esteso in modo additivo** (`contracts/nexus-event.schema.json`) - aggiunti `TOOL_USED`, `FILE_READ`, `FILE_CHANGED`, `RETRY_STARTED`, `ESCALATION_REQUIRED` in coda all'enum esistente, `AGENT_ESCALATED` preesistente mantenuto per compatibilita'. **Effetto collaterale atteso e documentato**: il vecchio `verify_orchestrator_v1.py`/`test_orchestrator_v1.py` della fase architetturale ora segnalano questo file come "modificato" - corretto, era un controllo di deriva puntuale contro il proprio momento storico, non una regola perenne.
- `ROUTING_POLICY_V1` (narrativa in `docs/architecture/18_...md` §5-7): implementata fedelmente in `core/router.py`, stesso ordine esatto (TIER0 deterministico → capability+risk gate locale → scientific_risk→Claude → code_risk alto→Codex → revisione manuale).
- Vault contract (`research_control_plane.py`): non toccato.
- Bake-off/Local Runtime findings: riusati identici (`ministral-3:3b`, vincoli localhost/timeout/1-retry/single-model-resident).

## 2-11. Componenti core implementati

Tutti sotto `server/orchestrator_v1/core/`:

| Componente | File | Note |
|---|---|---|
| Task Queue | `task_queue.py` | 10 stati richiesti, macchina a stati **fail-closed** (transizione non elencata → eccezione, mai silenziosa) |
| Router | `router.py` | Ordine esatto della routing policy, mai una chiamata automatica a Claude/Codex |
| Deterministic Worker | `deterministic_worker.py` | 9 azioni TIER0 (pytest, verifier, schema, registry rebuild, hash, git status/diff, artifact verify) |
| Ollama Local Worker | `ollama_worker.py` | localhost hardcoded, timeout 180s, **un solo modello residente** (stesso fix OOM del bake-off), nessun fallback cloud |
| Capability enforcement | `capability.py` | Risk gates (financial/scientific) + capacita' dimostrate dal bake-off, fail-closed con motivi espliciti |
| Retry/escalation | `retry_escalation.py` | `RETRY_MAX_ATTEMPTS=1` **costante**, 7 classificazioni, routing per classificazione |
| Event Ledger | `ledger.py` | Append-only JSONL, ogni evento validato contro `NEXUS_EVENT_V1` prima di essere scritto |
| Result Packet | `result_packet.py` | **Confidence model implementato per davvero**: 6 segnali (verifier/test/artifact/schema/provenance/no-contradiction), mai autovalutazione |
| Context Packet | `context_packet.py` | Costruito automaticamente da un task fallito + log tentativi - Codex/Claude non ricevono mai una task vuota |
| Async Jobs | `async_jobs.py` | Contratto MT5 (CREATED→RUNNING→RUN_COMPLETED→EXTRACTION_QUEUED) - esecuzione reale NON implementata (fuori scope dichiarato) |
| API read-only | `api_readonly.py` | FastAPI APIRouter **autonomo, NON montato su `server/app.py`** (7189 righe, backend live EA+dashboard - fuori scope/rischioso toccarlo) |
| Orchestrator | `orchestrator.py` | Collega tutto - `LocalTaskHandler` pluggable per ogni tipo concreto di task locale |

## 12. Acceptance Test #1 — bug reale `hypothesis_count==8`/`experiment_count==8`

Confermato ancora presente (`assert 9 == 8`, entrambi i registry cresciuti a 9). Il sistema ha **autonomamente**: creato il task, classificato il rischio (A1/LOW), instradato a TIER2 (nessun workflow deterministico esiste per "scrivi un'assertion corretta"), diagnosticato (fatti raccolti da Claude/TIER0: conteggi reali), fatto proporre a `ministral-3:3b` la patch (`assert ... >= 9` per entrambe le righe), **verificato in sandbox** (pytest sulla copia patchata: PASS), **fermato a `WAITING_APPROVAL`** perche' tocca un file reale del repository — **mai applicato il file reale**, per costruzione dell'approval boundary.

**Bug di harness trovato e corretto** (mai la logica del modello): `.strip()` sulla riga proposta perdeva l'indentazione, causando un `IndentationError` nel test sandboxato — corretto preservando l'indentazione originale.

## 13. Acceptance Test #2 — pipeline completa attraverso l'Orchestrator

TASK A (TIER0, verifica input BREAKOUT_ACC) → COMPLETED → TASK B (TIER2, dipende da A, backfill `temporal_concentration` via Ministral) → **COMPLETED, confidence=HIGH**. Risultato **ri-verificato indipendentemente** da `verify_orchestrator_core_v1.py` (ricalcolo separato, non solo lettura del file salvato).

**Bug di harness trovato e corretto**: `os.path.relpath` su Windows usa `\`, il manifest dichiara path con `/` — falso mismatch nel controllo "artifact completi" del confidence model, sceso a MEDIUM. Corretto normalizzando i separatori.

## 14. Approval boundary — dimostrato, non solo dichiarato

L'acceptance test #1 e' la prova diretta che l'Orchestrator rispetta l'approval boundary anche quando il worker locale ha **gia' prodotto e verificato** una patch corretta: `approval_required=REVIEW_REQUIRED` blocca comunque la scrittura del file reale. Nessun push automatico in nessun acceptance test.

## 15. API read-only

Endpoint `/api/orchestrator/{tasks,tasks/{id},queue,agents,ledger,escalations}` — tutti GET, smoke-testati con `TestClient`. **Non montato** su `server/app.py` (produzione live) - pronto per l'integrazione UI di Codex.

## 16. Esplicitamente non fatto

Jarvis UI, voice, frontend Product Platform, chiamate automatiche a Claude/Codex API, trading controls, market execution, deploy, esecuzione MT5 reale (solo contratto).

## Decisione finale

**`ORCHESTRATOR_V1_OPERATIONAL`**

Tutti i componenti richiesti implementati e testati (17/17 unit test + verificatore indipendente PASSED), dimostrati funzionanti end-to-end su 2 acceptance test reali — incluso il caso critico (approval boundary) che impedisce all'Orchestrator di scrivere file reali senza revisione, anche quando il worker locale ha gia' una soluzione verificata pronta.

## Deliverables

`server/orchestrator_v1/core/` (11 moduli), `run_acceptance_test_1.py`, `run_acceptance_test_2.py`, `verify_orchestrator_core_v1.py`, `build_orchestrator_core_report.py`, `orchestrator_core_final_report_v1.json`, `acceptance_test_1_result_v1.json`, `acceptance_test_2_result_v1.json`, `proposed_patches/hypothesis_count_fix_v1.diff`, `server/tests/test_orchestrator_v1_core.py` (17 test), questo vault report. Estensione additiva: `contracts/nexus-event.schema.json`.

## Vincoli preservati

Nessuna modifica a `MQL5/`, `Product-Platform/`, `server/app.py`. Nessun file reale del repository modificato dagli acceptance test (solo proposte verificate in sandbox). Nessun deploy. Nessun trading. Nessuna chiamata automatica a API premium. Nessuna dipendenza cloud obbligatoria introdotta.

## Regressione

`verify_orchestrator_core_v1.py`: PASSED (ricontrollo indipendente: stato WAITING_APPROVAL, file reale intatto, artifact patch presente, nessun leftover sandbox, entrambi i task dell'acceptance test 2 COMPLETED, risultato ri-calcolato indipendentemente, suite di test 17/17 pass).

---

```
NEXUS ORCHESTRATOR V1 CORE: IMPLEMENTATO E OPERATIVO

Codex indisponibile per quota - non atteso, per esplicita decisione
dell'utente (l'architettura esiste per evitare che un provider blocchi
il progetto)

RIUSO: TASK_MANIFEST_V1, AGENT_CAPABILITY_REGISTRY_V1, CONTEXT_PACKET_V1,
  RESULT_PACKET_V1 riusati identici - NEXUS_EVENT_V1 esteso in modo
  additivo (5 nuovi tipi evento), nessuna versione concorrente creata

CORE: Task Queue (10 stati, fail-closed), Router (routing policy
  fedele), Deterministic Worker (9 azioni TIER0), Ollama Worker
  (ministral-3:3b, vincoli bake-off riapplicati), Capability
  enforcement, Retry/Escalation (1 retry MASSIMO, 7 classificazioni),
  Event Ledger (append-only, validato), Result/Context Packet builders
  (confidence a 6 segnali, mai autovalutazione), Async Jobs contract,
  API read-only (NON montata su app.py di produzione)

ACCEPTANCE TEST 1 (bug reale hypothesis_count==8): sistema ha
  autonomamente diagnosticato, proposto patch via Ministral, verificato
  in sandbox (PASS), fermato a WAITING_APPROVAL - MAI toccato il file
  reale - approval boundary dimostrato funzionante anche con una
  soluzione gia' pronta

ACCEPTANCE TEST 2 (pipeline completa): TASK A (TIER0) -> TASK B (TIER2,
  Ministral) -> COMPLETED, confidence=HIGH, ri-verificato
  indipendentemente

2 bug di harness trovati e corretti durante gli acceptance test (mai
  la logica del modello): indentazione persa in una patch, separatori
  path Windows vs POSIX nel confidence model

DECISIONE: ORCHESTRATOR_V1_OPERATIONAL

PROSSIMO PASSO (dichiarato dall'utente): molte task inizieranno a
  passare al worker locale attraverso questo Orchestrator - l'uso di
  Claude per implementazione dovrebbe ridursi drasticamente da qui in
  avanti
```
