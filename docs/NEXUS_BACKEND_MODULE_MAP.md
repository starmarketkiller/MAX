# NEXUS MASTERPLAN V4.1 — Backend Module Map

Fonte: census read-only dedicato di questa sessione. Nessun file toccato, nessun file sotto `server/orchestrator_v1/core/`, `multi_stage_executor.py`, `local_operations.py`, `LocalBridge/` analizzato in profondità (territorio concorrente di Codex).

## Entry point

`server/app.py` — **7.898 righe**, singolo file FastAPI monolitico. `app = FastAPI(...)`, startup/shutdown hook registrati. Entrypoint Docker: `docker-entrypoint.sh` → `uvicorn app:app` (healthcheck su `/api/ready`).

## Inventario route API — 241 route totali, raggruppate per prefisso

| Gruppo | # route | Nota |
|---|---|---|
| `research` | 33 | il più grande |
| `jarvis` | 28 | |
| `backtest` | 23 | |
| `ea` | 17 | |
| `analytics` | 16 | |
| `coach` | 15 | |
| `dashboard` | 11 | |
| `company` | 11 | |
| `local_bridge` | 10 | |
| `strategies` | 9 | |
| `settings`/`license` | 7 ciascuno | |
| `market`/`library`/`downloads`/`auth` | 4 ciascuno | |
| `admin` | 4 | |
| altri (`strategy_chain`, `revenue`, `jobs`, `knowledge`, `command`, `chart`, `calendar`) | minori | |

**Nessun `APIRouter` per sotto-modulo trovato** — tutte le 241 route sono registrate direttamente sull'unico oggetto `app`, nello stesso file.

## Middleware

Un solo middleware esplicito: `CORSMiddleware`, aggiunto solo se `ALLOWED_ORIGINS` è impostata — allow-list esplicita, mai wildcard (commento inline `AUD0-CORS-001`, deliberato, credentials-safe). Nessun middleware di logging globale — l'auth è per-route via funzioni dependency, non un middleware generico.

## Meccanismi di autenticazione (3 distinti, scoped per route)

1. **Sessione cookie + JWT** (`NEXUS_JWT_SECRET`/`NEXUS_JWT_HOURS`) — route dashboard/admin umane.
2. **Bearer `X-Nexus-Token`** (`NEXUS_BRIDGE_TOKEN`) — route EA/worker machine-to-machine (`ea_*`, `local_bridge`).
3. **Secret webhook Telegram** (`JARVIS_TELEGRAM_WEBHOOK_SECRET`) — route Telegram.

**Non è duplicazione** — tre confini di fiducia distinti (umano/macchina/webhook) coesistono per design.

## Pacchetti di primo livello in `server/`

| Pacchetto | Ruolo |
|---|---|
| `jarvis_v1` | Logica Jarvis/Orchestrator-facing |
| `orchestrator_v1` | Queue/Ledger/dispatcher core — fuori scope per questo census |
| `funding_v1` | Revenue (venture, scoring, opportunity) |
| `business_units` | Revenue + AI Fashion Agency |
| `executive_v1` | Executive State |
| `review_pipeline_v1` | Review multi-agente |
| `mt5_data_v1` | Dati canonici MT5 (questa sessione) |
| `research_scripts`/`research_datasets`/`data_cache*` | Artefatti di ricerca trading |
| `static` | Asset frontend |

**Due directory non-codice da non confondere con pacchetti**: `server/jarvis/` e `server/free_coding_worker_v1/` contengono solo file JSON di stato runtime — **nessun import Python le usa come moduli** (verificato: zero hit per `import jarvis`/`from jarvis import` fuori da `jarvis_v1`). Non un rischio di duplicazione, solo nomi che confondono — DEFER, rinominare solo se genera confusione reale.

## Data layer

SQLite, path via `NEXUS_DB_PATH` (`/data/nexus.db` su Render). **23 tabelle**: `trades`, `trade_events`, `trade_reasons`, `shadow_trades`, `strategy_stats` (trading); `ea_commands`, `ea_status`, `ea_status_history`, `bridge_commands`, `bridge_hosts`, `command_events` (EA/bridge); `licenses`, `license_events`; `coach_memory`, `coach_notifications`; `research_certificates`; `notifications`, `operator_audit`, `visual_objects`, `journal_meta`, `kv`, `schema_migrations`, `_readiness_probe`.

## Contratti

**64 file** in `contracts/*.schema.json` — confermato come il vero confine di validazione, attivamente usato (campione: `agency-content-brief-v1`, `agency-event-v1`, `agent-capability-registry`, `ai-fashion-agency-state-v1`, `artifact-reservation-v1`, `business-unit-revenue-v1`, `business-unit-state-v1`, + ~57 altri).

## Classificazione

| Elemento | Classificazione | Motivo |
|---|---|---|
| `app.py` (7.898 righe, 241 route in un file) | **REFACTOR** | Non rotto, ma sovradimensionato — nessuna scomposizione per `APIRouter` di dominio. Rischio reale di conflitto tra agenti concorrenti (rilevante dato il lavoro parallelo di Codex) |
| Auth a 3 meccanismi | **KEEP** | Scoped correttamente per confine di fiducia |
| CORS middleware | **KEEP** | Già difensivo |
| Schema 23 tabelle SQLite | **KEEP** | Split per dominio appropriato, migrazioni tracciate |
| `contracts/` a 64 file | **KEEP** | Il pezzo più solido di questa architettura |
| `server/jarvis/`, `server/free_coding_worker_v1/` | **DEFER** | Innocuo ma confusionario, non urgente |

Nessun import circolare osservato in questa passata (non verificato esaustivamente). Nessuna logica di route duplicata trovata.

## Raccomandazione per l'architecture review

La scomposizione di `app.py` in `APIRouter` per dominio (`research_router.py`, `jarvis_router.py`, `backtest_router.py`, ecc.) è un candidato **STRUCTURAL** — non urgente oggi, ma il rischio di conflitto con lavoro concorrente cresce con la dimensione del file. Vedi [performance/architecture findings](NEXUS_MASTERPLAN_V4_1.md).
