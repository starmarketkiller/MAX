# NEXUS Business Unit — AI_FASHION_AGENCY (V2 operations, dry-run)

Azienda interna di NEXUS che coordina un roster di modelle/creator AI dichiarati, trasforma
le opportunità trovate dalle automazioni NEXUS (trend, prodotti, offerte) in contenuti
originali e li porta verso ricavi attribuibili. **Non** è un sistema parallelo: non ha
orchestratore, coda, memoria, CRM o sistema Revenue propri.

```
User ⇄ Jarvis (/agency, "come va l'agenzia?")
          │  read-only: AI_FASHION_AGENCY_STATE_V1 / BUSINESS_UNIT_STATE_V1
          ▼
   Global Orchestrator ── action "agency_bounded_task" (skills.py) ── Ministral locale
          │                 verifier deterministico per skill, P2 background
          ▼
   TaskQueue + EventLedger (canonici)        AgencyStore (stato di dominio)
                                             models · inputs · products · briefs ·
                                             assignments · generation_packs · costs ·
                                             revenue_events
```

## File

| File | Ruolo |
|---|---|
| `../__init__.py` | `BUSINESS_UNIT_STATE_V1`: modello comune per tutte le BU (Mission, State, Inputs, Workers, Capabilities, KPIs, Costs, Revenue, Risks, Tasks, Evidence, Next Gate, Decision) |
| `store.py` | `AgencyStore` — stato di dominio persistente (JSON atomico, revision, indice di idempotenza; stesso idioma di `RevenueVentureRegistry`) |
| `roster.py` | 5 archetipi iniziali (`CASTING_DRAFT`, nessuna generazione) |
| `pipeline.py` | regole deterministiche: input bus, **STORE GATE**, compliance, viral adapter, brief, assegnazione modella, Generation Pack + gate crediti, costi, ricavi |
| `skills.py` | skill bounded instradate dall'Orchestrator canonico + verifier |
| `projection.py` | proiezioni per Jarvis e per il futuro `NEXUS_EXECUTIVE_STATE_V1` |
| `simulation.py` | simulazione end-to-end a costo zero → `examples/e2e_simulation_v1.json` |
| `playbooks/VIRAL_PLAYBOOK.md` | know-how creativo (migrato da `marketing/ai-creator/`) |
| `scouting.py` | V2: `SCOUT_RESULT_V1` provenance-safe (source, url, observed_at, evidence, confidence, dedup_key) → input bus |
| `store_integration.py` | V2: viability → adapter `EXTERNAL_STORE_LINK`/`AFFILIATE_LINK` → availability → listing candidate → approvazione → STORE_READY |
| `social.py` | V2: adapter Postiz (dry-run) / manual export, ciclo post `DRAFT→READY_FOR_REVIEW→APPROVED→SCHEDULED→PUBLISHED/FAILED`; publish disabilitato |
| `content_engine.py` | V2: brief card (hook, format, model, product, platform, objective, CTA, compliance, store gate, costo, approval) + content package |
| `policy.py` | V2: `AGENCY_AUTOMATION_POLICY_V1` (autonomo / approvazione / hard-disabled), fail-closed |
| `events.py` | V2: 13 eventi `AGENCY_*` → EventLedger canonico + push Jarvis solo per eventi di attenzione |
| `kpis.py` | V2: KPI agency/model/campaign; `UNAVAILABLE` quando il dato non esiste |
| `capability_scout.py` | V2: `CAPABILITY_SCOUT_V1` (registry → candidato → vet → sandbox → eval → register), nulla installato |
| `dry_run_v2.py` | V2: dry run su evidenze pubbliche reali → `examples/dry_run_v2_result.json` |
| `../revenue.py` | V2: `BUSINESS_UNIT_REVENUE_V1`, mostrato da Jarvis `/revenue` accanto alle venture |

Contratti: `contracts/business-unit-state-v1`, `ai-fashion-agency-state-v1`,
`agency-model-profile-v1`, `agency-input-v1`, `agency-product-v1`,
`agency-content-brief-v1`, `agency-generation-pack-v1`, `agency-revenue-event-v1`.

## Workflow

**Input bus** (`receive_input`): `TREND_VIDEO|TREND_AUDIO|TREND_FORMAT → VIRAL_ADAPTER`,
`PRODUCT|FASHION_ITEM|AFFILIATE_OFFER → STORE_GATE`, `CONTENT_IDEA|SEASON_EVENT →
CONTENT_BRIEF`, `CAMPAIGN|BRAND_REQUEST|SERVICE → CAMPAIGN_MANAGER` (revisione umana).
Idempotente per chiave sorgente.

**PRODUCT → STORE FIRST (gate canonico)**
`DISCOVERED → EVALUATING → STORE_PENDING → STORE_READY → CONTENT_READY → PUBLISHED →
MONETIZING → RETIRED`.
- `STORE_PENDING` richiede una valutazione `viable` (margine ≥ 30% per own store,
  fornitore, evidenza trend).
- `STORE_READY` richiede listing reale (`OWN_STORE` o `AFFILIATE_LINK` con URL) **e**
  approvazione umana.
- Un brief commerciale su un prodotto non store-ready viene `REJECTED` dalla compliance;
  un revenue event su un prodotto mai passato dal gate viene rifiutato.

**Viral flow**: `VIRAL_REFERENCE → VIRAL_FORMAT_ANALYSIS (skill) → compliance → struttura
→ CONTENT_BRIEF → MODEL_ASSIGNMENT → nuova versione originale`. Si conserva solo la
struttura (`media_retained: false`); `REPOST_ORIGINAL`, `OVERLAY_ON_ORIGINAL`,
`REUSE_ORIGINAL_FOOTAGE` sono rifiutati; audio solo da libreria piattaforma, originale o
licenziato.

**Higgsfield Generation Pack** (`build_generation_pack`): pianifica le chiamate a
pagamento (character sheet se la modella non ne ha uno, poi video/motion transfer).
Uno step è approvabile solo con un **preventivo fresco non-spending** (≤ 7 giorni);
altrimenti `WAITING_QUOTE`. `approve_generation_pack` richiede `approved_by` e
`expected_credits == quoted_credits`. NEXUS **non** esegue Higgsfield: l'esecuzione
avviene in una sessione Claude approvata e si registra con `record_generation_result`
(rifiuta step non approvati o spesa oltre il preventivo) → costo `generation_credits`.

## Mappa capability (census → riuso)

| Capability | Esistente? | Scelta | Verifier | Permessi |
|---|---|---|---|---|
| Routing/retry/escalation | Orchestrator + Router | **riuso** (`agency_bounded_task`) | per-skill | P2, `premium_allowed=False` |
| Multi-step | `MultiStageExecutor` | **riuso** per task Jarvis multi-step | final verifier | invariato |
| Skill pack/dataclass | `RevenueSkill` | **riuso** | — | — |
| Persistenza output skill | `encode_bounded_output` | **riuso** | — | — |
| FashionTrendScout / ViralContentAnalyst | no | **skill** `VIRAL_FORMAT_ANALYSIS` | evidenza, audio, beat, durata | read-only |
| ProductOpportunityScout | no | **skill** `PRODUCT_OPPORTUNITY_SCOUT` | evidenza | read-only |
| StoreGatekeeper | no | **tool deterministico** `pipeline.transition_product/store_gate` | gate | approvazione umana per STORE_READY |
| ModelCastingDirector / FashionStylist | no | **dati + tool** (`roster.py`, `score_models`) | compliance | approvazione sheet |
| ContentBriefBuilder / CreativeDirector | no | **skill** `CONTENT_BRIEF_DRAFT` + `build_content_brief` | hook ≤ 8 parole, claim vietati | — |
| ComplianceReviewer | no | **tool deterministico** `compliance_check` + skill `CONTENT_REVIEW` | — | — |
| CampaignManager | no | input `CAMPAIGN_MANAGER` → revisione umana (V1) | — | umano |
| RevenueAnalyst / SocialPerformanceAnalyst | parziale (Revenue metrics) | **skill** `PERFORMANCE_SUMMARY` + `projection.py` | liste | read-only |
| Generazione immagini/video | Higgsfield MCP (sessione Claude) | **riuso esterno** via Generation Pack | gate crediti | approvazione esplicita |
| Pubblicazione social | Postiz (skill presente nella sessione), Higgsfield TikTok | **futuro**, non attivo | — | approvazione |

**Agent creati: 0.** Ogni ruolo sopra è coperto da una skill, da un tool deterministico o
dalla revisione umana. Un agent dedicato verrà proposto solo se un ruolo richiederà
stato/loop propri che skill + tool + verifier non coprono.

**OSS (SEARCH → REUSE → VET → TEST → WRAP → REGISTER → VERIFY)**: nessuna installazione
in V1. Candidati valutati per fasi successive: Postiz (pubblicazione/analytics social —
già disponibile come skill nella sessione, primo candidato per il Social subsystem),
Crawl4AI / SearXNG (trend & product scouting con evidenze), Playwright MCP (verifica
listing store), Twenty (CRM: **non** adottare finché il Lead store Revenue basta),
Activepieces (non necessario: il bus input + scheduler esistenti coprono V1).

## Integrazioni

- **Jarvis**: `/agency` o frasi con "agenzia"/"modelle" → `OperationsProjection.agency()`
  → `AI_FASHION_AGENCY_STATE_V1` + frase italiana (`jarvis_summary`). Risponde a modelle
  totali/attive, contenuti in coda, prodotti bloccati dallo store gate, approvazioni,
  top model/campagna, ricavi/costi/profitto, crediti spesi/in attesa, next actions.
- **Executive State**: `business_unit_state()` produce `BUSINESS_UNIT_STATE_V1`, pronto per
  essere incluso come `ai_fashion_agency` in `NEXUS_EXECUTIVE_STATE_V1` (non creato qui).
  `business_units.REGISTERED_UNITS` è il punto d'aggancio.
- **Revenue**: `AGENCY_REVENUE_EVENT_V1` attribuisce ogni ricavo a model / campaign /
  product / content / channel con riferimento esterno osservato; `revenue_v1_id` collega
  un eventuale `REVENUE_V1` (pagamento Revolut registrato da `FirstRevenueStore`).
  L'Agency **non** è registrata nel `REVENUE_VENTURE_REGISTRY_V1` (schema fisso a 4
  venture zero-budget; l'Agency ha costi in crediti): la registrazione è un gate futuro
  che richiede modifica di schema + approvazione.
- **Social**: `models[].social_accounts` e `performance_metrics` sono i punti di ingresso;
  oggi vuoti (alert "nessun account social collegato"). Pubblicazione disattivata
  (`publishing_enabled: false`).

## KPI

Agency: `models_active, content_queue, published, views, engagement, followers, leads,
sales, revenue_eur, costs_eur, profit_eur, credits_spent` (ROI = profit/costs quando
costi > 0). Model: `performance_metrics` per modella (views, engagement, followers,
content_published, sales, revenue). Product: stato gate + revenue events per prodotto
(CTR/conversion quando il Social subsystem fornirà i dati).

## Compliance (vincolante, `pipeline.compliance_check`)

Etichetta AI obbligatoria (Instagram "AI-generated profile" 2026, TikTok AIGC, EU AI Act
art. 50); disclosure pubblicitaria/affiliazione (AGCOM); nessun riuso di footage altrui;
audio lecito; nessun claim assoluto/ingannevole (guadagni, salute, "guaranteed");
modelle solo adulte 21+; nessun contenuto esplicito; nessuna somiglianza con persone reali
senza consenso; categoria di contenuto ammessa per la modella.

## V2 — Operations (dry-run)

**Revenue**: invece di forzare l'Agency nel registro venture a 4 elementi (zero-budget), le
business unit con costi propri pubblicano `BUSINESS_UNIT_REVENUE_V1` (`business_units/revenue.py`),
incluso in `OperationsProjection.revenue()["business_units"]`. Ogni revenue event ha
`business_unit_id, model_id, campaign_id, product_id, content_id, channel,
gross_revenue_eur, costs_eur, net_revenue_eur, source, external_reference, timestamp`
(+ link opzionale a `REVENUE_V1`). Nessun ricavo stimato.

**Scouting**: census → NEXUS non ha web search/crawl propri (Market Scout lavora su evidenze
fornite). Collector attivi: `SUPPLIED_SESSION_TOOL` (web search/fetch di una sessione
supervisionata) e `MANUAL`. SearXNG / Crawl4AI / Playwright MCP restano candidati
`NOT_INSTALLED`. Nessuno scraping da NEXUS.

**Store**: nessuno store live. Adapter link esterno/affiliato; `available=None` →
`UNVERIFIED_NEEDS_HUMAN_CHECK` (nessun fetcher incluso), link irraggiungibile → non
approvabile. STORE_READY = approvazione umana di un listing già esistente.

**Social — decisione**: Postiz come adapter target (OSS self-hosted, multi-piattaforma,
analytics, già skill nel workspace). Activepieces scartato (duplica Orchestrator). API
native rinviate. In V2 `SCHEDULED` è un piano interno con payload `dry_run: true`:
consegnarlo a Postiz significherebbe pubblicare → `PUBLISH` hard-disabled.

**Account modelle**: 3 slot per modella (tiktok, instagram, youtube_shorts) `NOT_CREATED`,
`handle: null` finché un umano non crea l'account (`CREATE_SOCIAL_ACCOUNT` richiede approval).

**Seed pack V2**: Elena e Nova hanno identity sheet, prompt seed, consistency rules,
wardrobe, lighting/camera, 3 archetipi, 3 adattamenti virali, 2 formati product placement;
preventivo reale 2.25 crediti / 2 varianti (riverificato 2026-10-07, `submitted: false`).

**Policy**: autonomo = scout, dedupe, classify, brief, assign, generation pack, compliance,
report, bozze social, proposta listing. Approval = spendere crediti, asset a pagamento,
prodotto online, programmare post, creare account. Hard-disabled in V2 (anche con
approval) = publish, sponsor, contatto brand, accordi, pagamenti.

**Jarvis**: `/agency` + domande naturali ("come va l'agenzia?", "quali modelle stanno
lavorando?", "abbiamo prodotti pronti?", "quale campagna è più promettente?", "quanto sta
guadagnando l'agenzia?", "quali modelle hanno account?") via `agency_answer` (selettore
deterministico, nessun secondo motore). "quali devo approvare" aggiunge le decisioni
dell'Agency (crediti, listing, post). `OperationsProjection.business_units()` = hook per
`NEXUS_EXECUTIVE_STATE_V1`. Le parole chiave Agency sono classificate *dopo* le richieste
di task, così "crea una task per la campagna…" crea ancora una task.

## Runbook

```bash
cd server
python -m business_units.ai_fashion_agency.simulation   # simulazione V1, 0 crediti
python -m business_units.ai_fashion_agency.dry_run_v2   # dry run V2 su evidenze reali
python -m pytest tests/test_ai_fashion_agency_business_unit_v1.py tests/test_ai_fashion_agency_operations_v2.py -q
```
Stato persistente in produzione: `$JARVIS_STATE_DIR/ai_fashion_agency_registry_v1.json`.
