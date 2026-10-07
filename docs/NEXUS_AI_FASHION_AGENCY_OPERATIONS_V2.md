# NEXUS AI Fashion Agency Operations V2

Marker: `NEXUS_AI_FASHION_AGENCY_OPERATIONS_V2_CANONICAL` (operativa in dry-run completo)

Branch: `agency-operations-v2` (da `05985ad`). Dettaglio: `server/business_units/ai_fashion_agency/README.md`.

## Cosa cambia rispetto alla V1

| Area | V2 |
|---|---|
| Revenue | `BUSINESS_UNIT_REVENUE_V1` per BU con costi propri, in Jarvis `/revenue`; revenue event con lordo/costi/netto/source/timestamp; registro venture a 4 intatto |
| Scouting | `SCOUT_RESULT_V1` con provenance + dedupe; collector attivo = web tool di sessione supervisionata; SearXNG/Crawl4AI/Playwright candidati non installati |
| Store | adapter link esterno/affiliato, availability check, listing candidate → approval → STORE_READY |
| Social | adapter Postiz (dry-run) + export manuale; stati DRAFT…FAILED; publish hard-disabled |
| Account | 15 slot `NOT_CREATED` (5 modelle × 3 piattaforme), nessun handle inventato |
| Content | brief card completa; content package dopo generazione + review |
| Higgsfield | seed pack V2 Elena/Nova; preventivo 2.25 crediti riverificato, non speso |
| Jarvis | risposte naturali alle domande esecutive; approvazioni Agency nella lista "quali devo approvare"; projection `business_units()` per l'Executive State |
| Eventi | 13 `AGENCY_*` nel ledger canonico (enum NEXUS_EVENT_V1 estesa in modo additivo), push solo per eventi di attenzione |
| KPI | agency/model/campaign; `UNAVAILABLE` dove mancano dati |
| Policy | `AGENCY_AUTOMATION_POLICY_V1` fail-closed |
| Capability scout | 4 gap registrati (social, scouting, analytics, store), 0 installazioni |

Nessun nuovo orchestratore, coda, CRM, Revenue store, stato Jarvis o modello BU.
CI/MT5/MACD non toccati.

## Dry run realistico (`examples/dry_run_v2_result.json`)

Evidenze reali catturate verbatim (New Engen, "October 2026 TikTok Trends", aggiornato
2026-10-05): format **Fan Transition**, capo **giacca in suede** (segnale debole, 0.35).

1. 2 scout result ingeriti con provenance → 1 trend, 1 prodotto.
2. Store gate: prodotto bloccato in `EVALUATING` (nessun fornitore/prezzo) → brief commerciale `REJECTED`.
3. Viral analysis inviata all'Orchestrator canonico → worker locale irraggiungibile da questo
   container → `ESCALATION_REQUIRED` (premium non consentito); struttura fornita dalla sessione
   supervisore e passata dal verifier canonico.
4. Brief originale non commerciale → Elena (fit "quiet luxury") → pack Higgsfield
   `WAITING_APPROVAL` 2.25 crediti; step video `WAITING_QUOTE`.
5. Jarvis: "AI Fashion Agency: 0 campagne pronte, 1 contenuti in lavorazione, 0 prodotti
   store-ready, 5 modelle in roster (0 attive); generazione Higgsfield in attesa di
   approvazione (2.25 crediti)…".

Garanzie: `credits_spent=0`, `published_content=0`, `external_outreach=0`, nessuno store aperto.

## Blocker (decisioni umane / esterne)

1. Approvare il primo character sheet (Elena o Nova, 2.25 crediti).
2. Preventivo per gli step video (oggi nessun preventivo non-spending disponibile).
3. Fornitore/prezzo o link affiliato per un prodotto → listing → approvazione STORE_READY.
4. Creare gli account social (azione umana) e decidere se ospitare Postiz.
5. Mistral locale raggiungibile per eseguire le skill Agency senza escalation.
6. Collector di scouting automatico (SearXNG/Crawl4AI) da vettare in sandbox.
7. Merge del branch `agency-operations-v2` su `main` dopo review.
