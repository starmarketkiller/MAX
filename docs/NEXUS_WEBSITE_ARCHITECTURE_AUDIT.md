# NEXUS MASTERPLAN V4.1 — Website Architecture Audit

Fonte: census read-only dedicato di questa sessione. Nessun file toccato.

## Stack reale

SPA **React 18** (CRACO/CRA, non Vite). Dipendenze chiave: `react-router-dom` (routing), `@tanstack/react-query` (data fetching/cache), Radix UI + Tailwind (`tailwind-merge`, `class-variance-authority`), `@react-three/fiber`+`three` (landing 3D reale in `src/pages/Landing3D/`), `lightweight-charts`+`recharts` (grafici trading), `framer-motion`.

## Inventario pagine (40+ file reali in `frontend/src/pages/`)

Dashboard (Home/Analytics/Optimizer/Strategies/StrategyAnalytics/WhatIf), Backtest (Charts/Creator/Form/ManagementReport/Metrics/Optimizer/RealAnalysis/StrategyLibrary/ResearchIntegrityLab), Coach (chat + pannello memoria), Research/ResearchControlPlane, Market/LiveChart, Journal, Calendar, Knowledge/Library, Execution, StrategyChain, SequenceExplorer, RiskCalc, **SystemStatusPage** (telemetria EA/research), **LocalBridgePage** (264 righe, UI reale per il bridge locale), Workspace/Company/Licenses/Login/Prezzi/FAQ.

## `server/static/` — due superfici coesistenti, non in conflitto

- `dashboard.html`/`login.html`/`faq.html`/`prezzi.html`/`strategia.html`/`performance.html` — pagine statiche separate (marketing/legacy).
- `server/static/app/index.html` + `asset-manifest.json` — output buildato della SPA React (pattern CRA standard). `app.py` monta questo bundle via `fastapi.staticfiles.StaticFiles`.

**Classificazione**: REFACTOR (non urgente) — tenere a mente la doppia superficie, non un blocco per questo lavoro.

## Autenticazione

Cookie httpOnly (`/auth/login` → cookie di sessione, **mai** token in `localStorage`, commento esplicito anti-XSS nel codice) + CSRF a doppio invio (`nexus_csrf` leggibile da JS, header `X-Nexus-Csrf` su ogni mutazione — `src/lib/api.js`). Pattern solido, non improvvisato — **KEEP**.

## Pattern di aggiornamento live già esistente e riusabile

`frontend/src/lib/useVisiblePolling.js` — polling solo quando il tab è visibile, si ferma su `visibilitychange`, guard anti-overlap (`inFlight`). **Questo è il pattern da riusare per il Visual Operations Center** (vedi [NEXUS_VISUAL_OPERATIONS_SITE_INTEGRATION.md](NEXUS_VISUAL_OPERATIONS_SITE_INTEGRATION.md)) — nessun WebSocket/SSE esiste oggi, non necessario per il volume attuale.

## CI

Job `frontend-build` reale in `.github/workflows/ci.yml:155` — `npm ci` con lockfile fisso (commento `AUD0-FE-SUPPLY-001`: versioni `"latest"` causavano build non riproducibili, già corretto in passato).

## Test

Coverage reale ma parziale: test trovati per CompanyPage, ExecutionPage, KnowledgePage, LibraryPage, MarketPage, ResearchControlPlanePage, SequenceExplorerPage, `lib/api.test.js`, `lib/workspaces.test.jsx`. **Mancanti**: Dashboard, Backtest, Coach, SystemStatusPage.

## Classificazione per modulo

| Modulo | Classificazione | Motivo |
|---|---|---|
| Stack React/Router/Query/Radix/Tailwind | **KEEP** | Solido, maturo, nessun motivo di sostituire |
| Auth cookie+CSRF | **KEEP** | Già difensivo (anti-XSS, anti-CSRF) |
| `useVisiblePolling.js` | **KEEP, riusare** | Esattamente il pattern giusto per il Visual Operations Center |
| CI `frontend-build` | **KEEP** | Lockfile fisso, riproducibile |
| `SystemStatusPage.jsx` | **EXTEND** | Punto di estensione naturale per Modalità A del Visual Operations Center |
| `LocalBridgePage.jsx` | **EXTEND** (come riferimento di pattern) | Precedente reale di "pagina operativa ricca" |
| Doppia superficie `server/static/*.html` + `app/` | **REFACTOR** (non urgente) | Funziona, ma due superfici da tenere a mente |
| Test mancanti (Dashboard/Backtest/Coach) | **DEFER** | Non urgente per questo task |
| Qualunque area | **REPLACE** | Nessuna trovata — nessuna parte del frontend richiede riscrittura |

## Conclusione

Il sito attuale è **ben strutturato** per lo scopo di questo task: aggiungere il Visual Operations Center significa aggiungere route React nuove sotto lo stesso router, stessa auth, stesso hook di polling, stesso job CI — **zero nuova infrastruttura frontend necessaria**.
