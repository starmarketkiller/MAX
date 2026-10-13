---
type: system-state
domain: system
status: active
tags: [jarvis, nexus, stato]
created: 2026-10-05
updated: 2026-10-13
---

# CURRENT_STATE — dove siamo (aggiornato 2026-10-13)

> Obiettivo di questa nota: capire in meno di 2 minuti dove siamo, cosa è
> chiuso, cosa è attivo, cosa è bloccato, qual è il prossimo P0. Per lo stato
> trading-specifico dettagliato restano canonici **[[NEXUS EA - MASTER ROADMAP v3]]**
> e la cartella `vault/01-Trading/Decisions/` — questa nota non li duplica,
> copre il quadro generale del progetto NEXUS (Jarvis + Trading + Business).

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
- **NEXUS MASTERPLAN V4 + V4.1** — architettura canonica a 7 reparti,
  riconciliata con il "Command Floor" reale di Codex scoperto a fine
  sessione. Branch `docs/nexus-masterplan-v4.1`, **non mergiato su main**.
- **RRA-01 — Research Recovery & Cross-Engine Architecture** — censimento
  storico completo (phase2→phase7_28, vault/01-Trading 309 note, detector
  MQL5, parità cross-engine, Fast Research Engine). Branch
  `docs/nexus-rra-01-research-recovery`, **non mergiato su main**. Deliverable:
  historical evidence ledger, strategy/variant map, untested-experiment
  registry, shortlist + Top 20 domande, roadmap RECOVER/REPAIR/EXPLORE.
- **RRA-02 — Trading Fidelity & Risk Addendum, su `main` (mergiate, verificate nel codice reale)**:
  - **PR #36** `NXS_AccountGuard.mqh` + gate `ACCOUNT_MODE` dentro
    `NXS_CommonExposurePreflight` — nuova esposizione su REAL/CONTEST
    richiede autorizzazione LIVE esplicita legata al login; DEMO/Tester
    aprono liberamente.
  - **PR #47** Max Total DD ora persistita su riavvio (snapshot schema v7,
    cursore di riconciliazione flussi di capitale, replay-safe). Chiude
    il gap trovato in RRA-01 (`g_maxDDPeakEquity` non persistita). **Limite
    dichiarato dalla PR stessa**: il ciclo reale "salva→shutdown→ripristina"
    non è mai stato eseguito in un Tester con account configurato — verificato
    solo a livello di test unitari.
  - **PR #49** (Safety P0) PipSequence ora compone `NXS_CheckProtections` +
    `NXS_CommonExposurePreflight` prima di `SafeBuy/SafeSell` — chiude il
    bypass di re-entry. Verificato riga per riga. DataCollection e NXR
    disabilitato restano findings separati, non chiusi da questa PR.
  - **PR #50** Execution contract di fedeltà scientifica (opt-in,
    `strict_execution_contract=False` di default) — non tocca MQL5/risk live.
  - **Gap trovato, non dichiarato da nessuna PR**: `server/trading_v1/`
    (supervisione EA + telemetria, PR #45) non è mai arrivato su `main` —
    vive solo su `feature/trading-execution-v1`, diverge da `main` dal
    commit `8d74193`, mai riconciliato con le PR di sicurezza successive.
- **RI-02 / RI-03** (`claude/research-loop-ri02`, `feature/ri03-research-control-center`)
  confermati reali come branch — la ricerca di RRA-01 non li aveva trovati
  solo perché non erano ancora su `main` al momento del censimento.
- **Dukascopy Discovery Inventory v2** — 547/547 partizioni discovery
  verificate (`INVENTORY_VERIFIED`, contratto `CONTRATTO_OK`, HEAD
  `454e3dd`), 61.404.484 tick, 434 MiB. 16 ore classificate
  `HOURLY_GAPS_FOUND` (non spiegate, non corrette — tutte a cavallo di 4
  festività dichiarate). Output e handoff in
  `C:\Users\User\NEXUS_discovery_inventory_output\`. Nessun tick trasferito.

## Attivo ora

- **[[NEXUS TASK 0011 - First Revenue Manual Experiment (Lead Research Service)]]**
  — primo test di mercato reale. PNT Solutions contattato manualmente
  (2026-10-05 19:48), in attesa di risposta. Orto Creativo ed Eccolo
  Marketing in coda, un prospect alla volta, nessun follow-up automatico.
- **NEXUS FULL SYSTEM FORENSIC AUDIT** (Claude, revisore indipendente reparto
  Trading) — Batch 1 in corso: inventario file, verifica diretta nel codice
  delle 4 PR RRA-02, grafo delle dipendenze. 7 batch totali pianificati
  (strategie MQL5, risk/confluenze, Python/parity, vault/ResearchMemory,
  backend/infrastruttura, riconciliazione claim degli altri agenti).
- **NEXUS — Claude Local Scientific Replication** (replica Dukascopy del
  protocollo trailing M15 di Scalper/Grok, `NXLAB-C-DUKA-REPLICA-001`) — al
  checkpoint obbligatorio pre-run economico. Presente solo
  `NEXUS_checkpoint_C2.tar.gz` (55/55 test propri passati); richiesti ma non
  ancora ricevuti `NEXUS_checkpoint_B3.tar.gz`, `NEXUS_B3_repro.tar.gz`,
  `NEXUS_dukascopy_and_protocol.tar.gz`, `NEXUS_checkpoint_C.tar.gz`. Nessun
  run economico avviato.

## Bloccato

- **VOLBRK Serious 3Y** (trading) — **non più bloccato, CHIUSO con esito
  negativo**: la run è stata eseguita (3 tentativi, 2 falliti per bug
  infrastrutturali, 1 valido con n=183 trade). Verdetto finale `FAIL` →
  `ARCHIVE_CURRENT_DESIGN` (2026-09-22). La voce precedente di questa nota
  ("PARTIALLY_BLOCKED su 3 soglie umane") era obsoleta — corretta qui dopo
  verifica diretta sugli artifact in RRA-01. Dettaglio:
  **[[NEXUS - Phase 7.8B VOLATILITY_BREAKOUT Serious 3Y Preregistration]]**
  (nota storica, da intendere superata dal risultato reale).
- **Render/Telegram "Jarvis" deploy** (NEXUS TASK #0008, review pipeline) —
  `WAITING_APPROVAL`, bloccato in attesa di accesso/secrets Render
  dell'utente.
- `JARVIS_MINISTRAL_ROUTER_V1` in modalità ACTIVE — non bloccato da codice,
  ma sospeso per decisione (hardware troppo lento: 45.7s medi per risposta
  su questa macchina, non adatto a conversazione in tempo reale).
- **Max Total DD — condizioni d'uso/licenza dati Dukascopy** non dichiarate
  nel repository (nessuna policy di redistribuzione trovata) — da
  verificare con la fonte prima di qualunque trasferimento di tick a terzi.
- **Replica Scalper B3/Dukascopy** — in attesa dei 4 pacchetti mancanti
  (vedi "Attivo ora") prima di poter completare la verifica indipendente del
  protocollo e presentare il piano esperimenti per approvazione.

## Path canonico (confermato 2026-10-05)

**`C:\Users\User\ClaudeWork\MAX`** è l'unico repository/vault canonico.
`C:\Users\User\Downloads\MAX-main\MAX-main` è una copia ZIP non più
aggiornata (Obsidian puntava lì per errore) — **non va più usata**, ma non è
stata cancellata. Vedi verifica in **[[CHAT_MIGRATION_LEDGER_V1]]**.

## Prossimo P0

**Due fronti paralleli sul reparto Trading** (avviati 2026-10-13, entrambi
in corso): il Full System Forensic Audit (Claude come revisore indipendente)
e la replica scientifica locale del protocollo trailing M15 di Scalper
(checkpoint pre-run in attesa dei pacchetti mancanti). Nessun run economico
o backtest avviato finché l'utente non approva il piano esperimenti.
L'outreach PNT Solutions (NEXUS TASK #0011) resta in attesa separata, non
bloccante per questi due fronti.

## Regola standing (introdotta 2026-10-05)

Una milestone non è chiusa finché non ha: codice + test + commit + nota
vault/docs aggiornata. Questa nota va aggiornata ad ogni milestone che cambia
lo stato "chiuso/attivo/bloccato/P0" sopra — mai lasciata a decadere come era
successo a `Home.md` prima di oggi.
