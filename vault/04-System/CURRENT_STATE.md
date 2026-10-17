---
type: note
subtype: system-state
domain: system
status: active
tags: [jarvis, nexus, stato]
created: 2026-10-05
updated: 2026-10-17
---

# CURRENT_STATE — dove siamo (2026-10-05)

> Obiettivo di questa nota: capire in meno di 2 minuti dove siamo, cosa è
> chiuso, cosa è attivo, cosa è bloccato, qual è il prossimo P0. Per lo stato
> trading-specifico dettagliato restano canonici **[[NEXUS EA - MASTER ROADMAP v3]]**
> e la cartella `vault/01-Trading/Decisions/` — questa nota non li duplica,
> copre il quadro generale del progetto NEXUS (Jarvis + Trading + Business).

## Aggiornamento 2026-10-17 — lavoro 06→15 ottobre (ricostruito dal repo)

> Aggiunto dall'audit link/aggiornamento vault del 2026-10-17. Fonte: commit su
> `main` e documenti in `docs/`; il dettaglio resta lì, qui solo lo stato.
> Lo stato dell'outreach PNT Solutions (#0011) **non è verificabile dal repo**:
> va confermato a mano.

**Chiuso**
- **Contextual MACD Phase 1** (06/10) — `CLOSED_WEAK`, evidenza E1,
  `supported=false`: nessuna delle 60 celle congelate ha superato il criterio
  preregistrato (effetto appaiato positivo + BH q≤0.10). Una sola osservazione
  post-hoc (`MACD__LOW_VOL__SELL__T1_0_ATR`, p grezzo 0.022, q=1.0) **non va
  promossa né ritestata sullo stesso dataset**. Artifact:
  `server/research_scripts/contextual_edge_phase1/macd_decision_card_v1.json`.
- **RRA-01 — Research Recovery & Cross-Engine Architecture** (12/10, PR #48) —
  sintesi di 7 censimenti in sola lettura. Docs: `docs/NEXUS_RRA_01_*.md`.
- **RRA-02 — Final Research Architecture** (12-13/10) — decisione
  "Scenario B, evoluzione controllata": un unico Research Event/Feature Layer
  condiviso da tre viste (strategy-first, event-first, outcome-first), nessun
  motore nuovo. Stato `ROADMAP_READY_FOR_REVIEW`, nessun pilot eseguito.
  Docs: `docs/NEXUS_RRA_02_*.md`.
- **Fix di sicurezza EA** (13/10, solo codice + test, nessun deploy live):
  - Max Total DD (PR #47): latch permanente sull'equity rettificata dai flussi
    di capitale, persistito su snapshot, sopravvive a rollover e riavvio;
    reset solo via `reset_protections` autenticato. Spec:
    `docs/RRA_02_MAX_TOTAL_DD_SAFETY_SPEC.md`, report:
    `docs/RRA_02_CHECKPOINT_A_SAFETY_REPORT.md`.
  - Gate economico sul rientro PipSequence (PR #49).
  - Gate economici anche in modalità data collection (PR #51).
  - Contratti versionati di execution fidelity / effective risk cap (PR #50,
    `docs/NEXUS_RRA_02_TRADING_FIDELITY_RISK_ADDENDUM_V1.md`).
- **NXL2-CP2-PILOT-A-001 — preregistrazione** (14-15/10, PR #53/#54) — 12
  ipotesi `PREREGISTERED` aggiunte a ResearchMemory (checkpoint 136,
  autorizzazione `NXL2-CP2-A-20261014-01`) + resolver deterministico degli
  alias ID ipotesi (fail-closed). Manifest:
  `server/research_scripts/research_intelligence_v1/manifests/nxl2_cp2_pilot_a_001_v1.json`.
  **Solo preregistrazione: il pilot non risulta eseguito.**

**Correzione a "Bloccato" sotto:** secondo RRA-01 (§1.1) e la nota
[[NEXUS - Phase 7.8I Recompile + Research Mode - Primo Risultato Scientifico (FAIL)]],
VOLBRK Serious 3Y **è stato eseguito** (run valido n=183, PF 0.867, CI95 che
attraversa zero) con verdetto **FAIL → ARCHIVE_CURRENT_DESIGN** (22/09). La
voce "bloccato" sotto è quindi superata.

**Discrepanze ancora aperte (da RRA-01 §1, non risolte):** stato del difetto
TSI nel registry (`DEFECT_BLOCKED`) contro `FIX_CAUSALLY_VALIDATED` negli
artifact 7.17/7.18; conteggio strategie live 53 contro 55.

## Chiuso (in produzione, verificato)

- **Jarvis V1 / Orchestrator V1** — Task Queue/Router/Ledger, Dynamic
  Specialist Review, bot Telegram, live su Render. Ultime 3 milestone UX
  chiuse e verificate in produzione via smoke test reale: `STATE_QUERY_V1`,
  `JARVIS_CONTEXTUAL_ACTIONS_V1`, `JARVIS_CONTEXTUAL_MUTATION_RESOLUTION_V1`.
- **[[NEXUS - Jarvis Ministral Router V1]]** (`ced3d59`) — router cognitivo
  locale dietro gateway, `ENABLED=false` di default, zero impatto produzione.
- **[[NEXUS - Ministral Task Compiler V1]]** (`682c276`) — delega bounded a
  Ministral, template `repo_inspection_v1`, output persistito nel
  `RESULT_PACKET_V1` esistente.
- **Funding Priority & Opportunity Framework** (NEXUS TASK #0005-#0007,
  `FUNDING_FRAMEWORK_V1_ADOPTED`) — canone per qualunque opportunity di
  business, vedi **[[MOC - Opportunity and Funding]]**.
- **[[NEXUS TASK 0010 - First Revenue Execution V1 (Codex)]]** (`01e6180`) —
  bookkeeping Offer/Lead/Payment/Revenue, nessuna automazione autonoma.
- Audit di conoscenza: `NEXUS_KNOWLEDGE_CONSOLIDATION_AUDIT_V1` +
  `HEAVY_SESSION_SPOT_CHECK_V1` — 9/9 milestone campionate su 3 sessioni
  pesanti risultano `FULLY_CAPTURED` nel vault, nessun buco sistemico
  trovato. Dettagli: **[[CHAT_MIGRATION_LEDGER_V1]]**.

## Attivo ora

- **[[NEXUS TASK 0011 - First Revenue Manual Experiment (Lead Research Service)]]**
  — primo test di mercato reale. PNT Solutions contattato manualmente
  (2026-10-05 19:48), in attesa di risposta. Orto Creativo ed Eccolo
  Marketing in coda, un prospect alla volta, nessun follow-up automatico.
- Questa stessa consolidazione di conoscenza (`NEXUS_KNOWLEDGE_CONSOLIDATION_V1`).

## Bloccato

- ~~**VOLBRK Serious 3Y**~~ (superato, vedi aggiornamento 2026-10-17 sopra: eseguito, FAIL) — preregistrato ma `PARTIALLY_BLOCKED` su 3
  soglie che richiedono decisione umana. Non va eseguito/simulato finché non
  sono risolte. Dettaglio: **[[NEXUS - Phase 7.8B VOLATILITY_BREAKOUT Serious 3Y Preregistration]]**.
- **Render/Telegram "Jarvis" deploy** (NEXUS TASK #0008, review pipeline) —
  `WAITING_APPROVAL`, bloccato in attesa di accesso/secrets Render
  dell'utente.
- `JARVIS_MINISTRAL_ROUTER_V1` in modalità ACTIVE — non bloccato da codice,
  ma sospeso per decisione (hardware troppo lento: 45.7s medi per risposta
  su questa macchina, non adatto a conversazione in tempo reale).

## Path canonico (confermato 2026-10-05)

**`C:\Users\User\ClaudeWork\MAX`** è l'unico repository/vault canonico.
`C:\Users\User\Downloads\MAX-main\MAX-main` è una copia ZIP non più
aggiornata (Obsidian puntava lì per errore) — **non va più usata**, ma non è
stata cancellata. Vedi verifica in **[[CHAT_MIGRATION_LEDGER_V1]]**.

## Prossimo P0

**Aspettare l'esito dell'outreach PNT Solutions** (NEXUS TASK #0011) — nessuna
nuova infrastruttura Jarvis finché non arriva un segnale di mercato reale.
Subito dopo la chiusura di questa consolidazione (`CANONICAL_VAULT_READY`),
il prossimo grande milestone è l'**audit storico completo delle decisioni di
trading con contesto unificato** — deliberatamente non iniziato prima d'ora.

## Regola standing (introdotta 2026-10-05)

Una milestone non è chiusa finché non ha: codice + test + commit + nota
vault/docs aggiornata. Questa nota va aggiornata ad ogni milestone che cambia
lo stato "chiuso/attivo/bloccato/P0" sopra — mai lasciata a decadere come era
successo a `Home.md` prima di oggi.
