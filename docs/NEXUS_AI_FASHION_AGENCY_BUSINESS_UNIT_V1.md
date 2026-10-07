# NEXUS AI Fashion Agency Business Unit V1

Marker: `NEXUS_AI_FASHION_AGENCY_BUSINESS_UNIT_V1_FOUNDATION_CANONICAL`

Nuova Business Unit canonica `AI_FASHION_AGENCY`, al pari di Trading / Revenue / Social.
Dettaglio operativo: `server/business_units/ai_fashion_agency/README.md`.

## Cosa aggiunge

- `BUSINESS_UNIT_STATE_V1` (`server/business_units/__init__.py`): contratto comune per tutte
  le future business unit, proiettabile in `NEXUS_EXECUTIVE_STATE_V1`.
- Agency: store di dominio, roster di 5 archetipi, input bus, gate PRODUCT → STORE FIRST,
  viral adapter, compliance, assegnazione modella, Higgsfield Generation Pack con gate
  crediti, contabilità costi/ricavi con attribuzione, proiezione Jarvis (`/agency`).
- 8 contratti JSON Schema in `contracts/`.

## Cosa NON aggiunge (per design)

Nessun orchestratore, coda, memoria, CRM o sistema Revenue nuovo; nessun agent nuovo;
nessuna installazione OSS; nessuna pubblicazione, store live, outreach o campagna;
nessuna spesa di crediti. CI/MT5/MACD e lavoro Codex non toccati.

## Evidenza

- `server/tests/test_ai_fashion_agency_business_unit_v1.py`: 14 test (contratti, gate,
  compliance, assegnazione, gate crediti, attribuzione ricavi, routing Orchestrator,
  simulazione E2E, comando Jarvis).
- Simulazione E2E (`examples/e2e_simulation_v1.json`): Product Scout → STORE_READY →
  trend video → Viral Adapter (Orchestrator, executor `LOCAL_FAST_MINISTRAL3B`, modello
  stub) → brief → Elena assegnata → Generation Pack `WAITING_APPROVAL` (2.25 crediti,
  preventivo reale non-spending del 2026-10-07) → Jarvis:
  "AI Fashion Agency: 1 campagna pronta, 1 prodotto store-ready, 5 modelle in roster
  (0 attive); generazione Higgsfield in attesa di approvazione (2.25 crediti)…".
- `credits_spent = 0`.

## Blocker / gate successivi

1. Approvazione umana del primo character sheet (2.25 crediti per 2 varianti).
2. Preventivo per gli step video (oggi `WAITING_QUOTE`).
3. Store reale o link affiliati per il primo prodotto (STORE_READY con approvazione).
4. Social subsystem (account, pubblicazione, analytics) — candidato Postiz.
5. Registrazione dell'Agency nel Revenue Portfolio (richiede modifica schema venture).
6. Skill scout reali con evidenze da fonti (Crawl4AI/SearXNG da valutare).
