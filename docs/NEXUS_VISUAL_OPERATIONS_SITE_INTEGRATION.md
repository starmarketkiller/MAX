# NEXUS MASTERPLAN V4.1 — Visual Operations Center: integrazione nel sito esistente

**AGGIORNAMENTO CRITICO (stesso giorno, scoperto dopo aver scritto la proposta sotto)**: mentre scrivevo questo documento, un agente concorrente (Codex) ha mergiato su `origin/main` (commit `d2c7eed`, PR "command-floor"/"visual-floor-v2"/"nexus-floor-board"/"floor-live-diagnostics"/"floor-capability-map") un sistema **già reale** che realizza gran parte di quanto proposto qui sotto, con nomi diversi. **Non è stato costruito un secondo sistema** — questo documento va letto come confronto/formalizzazione di ciò che esiste, non come piano da costruire da zero. Dettaglio completo della riconciliazione: [NEXUS_ARCHITECTURE_GAP_ANALYSIS_V4_1.md §Riconciliazione con Command Floor](NEXUS_ARCHITECTURE_GAP_ANALYSIS_V4_1.md#riconciliazione-con-command-floor-di-codex-scoperta-a-fine-sessione). Sintesi: `frontend/src/command/stations.js` definisce già 119 "stazioni" sulle stesse 7 room (+ una room "Council") con gate/verifier/skill per stazione — concettualmente la stessa cosa dei miei "nodi" di `NEXUS_WORKFLOW_DEFINITION_V1`; `frontend/src/command/live.js` legge già 9 endpoint reali con classificazione fail-closed (`LIVE_VERIFIED` solo con validator esplicito, 2/9 oggi); `server/jarvis_v1/floor_workflow.py` esegue già un workflow reale (fashion handoff) attraverso l'Orchestrator esistente, fermandosi a `WAITING_APPROVAL` — esattamente il principio "mai un'azione autorizzata dalla sola animazione" che proponevo sotto. **La Council room esiste solo come label nella UI di Codex, zero backend — stesso identico gap che la mia proposta per il Global Improvement Council (V4) indirizza, confermato indipendentemente da due sistemi diversi.** La parte di questo documento sui contratti JSON Schema resta utile come proposta di *formalizzazione* di `stations.js` (oggi JS ad hoc, non uno schema versionato) — non come sostituzione.

---

**Stato originale di questa sezione: PROPOSTA di design, scritta prima della scoperta sopra.** Le immagini pixel-art inviate dall'utente (6 bot Grok) sono dichiarate esplicitamente "solo a scopo dimostrativo" — riferimento di STILE per la Modalità B, non un prodotto da copiare. Questo documento integra nel sito NEXUS **già esistente**, non ne crea uno nuovo.

## Vincolo architetturale di partenza (verificato, non presunto)

Il census frontend di questa sessione ha trovato che NEXUS ha già un sito maturo:
- **SPA React 18** reale (CRA/CRACO), non un prototipo — `react-router-dom`, `@tanstack/react-query`, Radix UI + Tailwind, `@react-three/fiber` (già una landing 3D), `lightweight-charts`+`recharts` (grafici trading già presenti).
- **40+ pagine reali** in `frontend/src/pages/` (Dashboard, Backtest, Coach, Research, Market, Journal, **SystemStatusPage**, **LocalBridgePage**, ecc.).
- **Auth**: cookie httpOnly + doppio invio CSRF (`src/lib/api.js`) — mai token in `localStorage`.
- **`frontend/src/lib/useVisiblePolling.js`**: hook di polling che si ferma quando il tab non è visibile, nessuna richiesta in overlap — **esattamente il pattern giusto per aggiornamenti quasi-live, già scritto e testato**.
- CI: job `frontend-build` reale, lockfile fissato.

**Conseguenza diretta**: il Visual Operations Center **non è un nuovo progetto** — è un nuovo gruppo di route sotto lo stesso router React, con la stessa auth, lo stesso hook di polling, build dallo stesso job CI. Zero nuova infrastruttura frontend.

## Punto di estensione, non di creazione

`frontend/src/pages/SystemStatusPage.jsx` (oggi 10 righe, delega a `SystemObservabilityPanel`+`HealthScoreCard`, mostra solo telemetria EA/research) è il punto di estensione naturale — **estendere questa pagina con le nuove viste, non crearne una isolata**. `LocalBridgePage.jsx` (264 righe) è il precedente reale più vicino per una "pagina operativa ricca" da cui riusare pattern UI (non copiare codice specifico al bridge, riusare la struttura).

---

## Modalità A — Engineering View (priorità iniziale)

Vista tecnica, leggibile da `NEXUS_VISUAL_WORKFLOW_STATE_V1` (contratto proposto in questa sessione):

```
Department → Workflow → Run → Step → Event → Artifact → Evidence → Verifier
```

Ogni livello è un drill-down cliccabile. Contenuto per livello:
- **Department**: le 7 card di reparto, stato aggregato (riusa `executive_v1`'s 9 domini già reali).
- **Workflow**: lista dei `NEXUS_WORKFLOW_DEFINITION_V1` noti per quel reparto, con l'ultimo run.
- **Run**: il grafo nodi/archi di `NEXUS_VISUAL_WORKFLOW_STATE_V1` per quel run specifico — nodi colorati per `visual_state` (IDLE/READY/RUNNING/VERIFYING/WAITING_CONTEXT/WAITING_APPROVAL/BLOCKED/FAILED/COMPLETED).
- **Step**: dettaglio di un singolo nodo — ruolo, capability richiesta, timing.
- **Event**: eventi `EventLedger` collegati (`event_refs`).
- **Artifact**: link ai file/risultati prodotti (`artifact_refs`).
- **Evidence/Verifier**: esito di `NEXUS_INDEPENDENT_REVIEW_V1` per quel nodo.

**Componenti React riusabili**: `lightweight-charts`/`recharts` già presenti per qualunque grafico; Radix UI per tabelle/drill-down; nessuna nuova libreria necessaria.

## Modalità B — Visual Room (dopo la A, stile ispirato alle immagini di riferimento)

Rappresentazione grafica delle Business Unit come ambienti/postazioni. Stati animabili = esattamente gli stessi 9 `visual_state` della Modalità A (stesso dato, resa diversa — **mai un secondo stato parallelo**).

**Vincoli non negoziabili**:
- Una postazione non risulta mai attiva se non esiste lavoro in esecuzione — l'animazione è una funzione pura di `NEXUS_VISUAL_WORKFLOW_STATE_V1.nodes[].visual_state`, mai uno stato finto per "sembrare vivo".
- Le animazioni non consumano risorse LLM — rendering client-side puro (CSS/Canvas/SVG), nessuna chiamata a Ollama/Claude/Codex per disegnare un frame.

## Pagine del sito proposte (sezione 12 della task) — verificate contro quelle esistenti

| Pagina proposta | Esiste già? | Azione |
|---|---|---|
| Executive Command Center | Parzialmente (`Dashboard/Home`) | ESTENDI con dati `executive_v1` a 9 domini |
| Departments Overview | No | NUOVA route, dentro `SystemStatusPage` o affine |
| Trading Operations Room | Parzialmente (`Backtest/*`, `Market/LiveChart`) | ESTENDI, non duplicare i grafici trading già presenti |
| Revenue Operations Room | No | NUOVA route |
| Fashion Agency Studio | No | NUOVA route |
| Social Content Studio | No (assorbito nell'Agency, vedi [Social/Content](NEXUS_MASTERPLAN_V4_SOCIAL_CONTENT.md)) | DEFER — non creare una pagina per un reparto che non esiste come modulo a sé |
| Engineering Operations | Parzialmente (`LocalBridgePage`) | ESTENDI |
| Finance Control Center | No | NUOVA route, ma dipende dall'aggregatore Finance (ancora PLANNED) — DEFER fino a quello |
| Jarvis Operations | Parzialmente (`SystemStatusPage`) | ESTENDI — punto di estensione primario |
| Workflow Engineering Viewer | No (è la Modalità A stessa) | NUOVA route, massima priorità |
| Self-Improvement Laboratory | No | NUOVA route, dipende da [Self-Improvement V1](NEXUS_DISTRIBUTED_SELF_IMPROVEMENT_V1.md) implementato |
| Independent Review & Approvals | Parzialmente (`unified_approvals()` già esiste, nessuna UI dedicata) | NUOVA route, riusa dati già reali |

## Aggiornamenti live — architettura event-driven valutata

```
EventLedger (già reale) → Projection (nuova, leggera) → API autenticata (stesso schema auth cookie+CSRF già reale) → useVisiblePolling.js (già reale, riusato) → Frontend
```

**Scelta raccomandata: riusare `useVisiblePolling.js`, non introdurre WebSocket/SSE ora.** Motivazione reuse-first: il pattern esiste già, è già parsimonioso (si ferma su tab non visibile, guard anti-overlap), e il volume di eventi di un sistema a 7 reparti con un solo operatore non giustifica la complessità aggiuntiva di un canale persistente. Se il volume di eventi crescerà, SSE è l'upgrade naturale (richiede meno infrastruttura di WebSocket, FastAPI lo supporta nativamente) — non deciso ora, nessuna azione.

**Requisiti da rispettare nell'endpoint di proiezione** (nuovo, leggero): deduplica, idempotenza, timestamp coerenti, nessun flooding di notifiche — la UI non deve autorizzare nulla da sola, ogni azione (approvazione, retry) passa dagli endpoint canonici già esistenti.

## Cosa questo documento NON propone

Non propone di costruire il Visual Operations Center ora. Propone il contratto (`NEXUS_VISUAL_WORKFLOW_STATE_V1`), il punto di estensione (`SystemStatusPage.jsx`), e la sequenza (Modalità A prima, Modalità B dopo) — l'implementazione vive nella roadmap ([NEXUS_IMPLEMENTATION_ROADMAP_V4_1.md](NEXUS_IMPLEMENTATION_ROADMAP_V4_1.md), Milestone 2 e 8).
