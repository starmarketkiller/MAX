---
type: note
domain: trading
status: active
tags: [trading, backtest-lab, infra, render]
created: 2026-07-12
updated: 2026-07-12
---

# Backtest Lab (sito) — note tecniche

## Stack
- **Backend**: FastAPI (`server/app.py`), motore di backtest in `server/backtest.py`
  (dict `STRATEGIES`, funzioni `sig_*` che ritornano -1/0/1).
- **Frontend**: React (craco/CRA), in `frontend/src/`, servito su `/app` con
  `basename="/app"`.
- **Deploy**: Render.com, un solo servizio Docker (`render.yaml`), contesto di build
  `./server`.
- **Dati**: Yahoo (via `_fetch_real`), cache in `_REAL_CACHE`.

## ⚠️ La trappola di deploy (risolta il 12/07/2026)
Il Dockerfile fa `COPY static ./static` — **non ricompila `frontend/src`**. Il sito
servito su Render è il build React **già compilato e committato** in
`server/static/app/` (route `/app` in FastAPI, `APP_DIR = STATIC_DIR / "app"`).

**Conseguenza pratica**: modificare `frontend/src/*.jsx` e pushare **non basta**.
Serve sempre:
```bash
cd frontend && npm run build
rm -rf ../server/static/app && cp -r build ../server/static/app
git add server/static/app && git commit && git push
```
Il commit deve toccare `server/` per essere un cambiamento "reale" agli occhi del
build Docker.

## Root del dominio vs app React
- `/` → serve `server/static/index.html` (vecchio sito statico multi-pagina:
  index/login/dashboard/performance/prezzi/faq/strategia).
- `/app` → React SPA (dashboard, backtest lab, landing 3D).
- Dal 12/07/2026: `/` fa `RedirectResponse` verso `/app/landing` (vedi commit
  `b0815d8`), quindi la landing 3D è diventata la vera front-door del dominio.

## Marcatore di verifica deploy
`app.py` espone `/api/health` con un campo `version` sul `FastAPI(...)`. Utile per
confermare *da fuori* se un deploy è realmente avvenuto (bump la versione prima di
un deploy critico, poi confronta `/api/health` prima/dopo).

## Perché il sito e MT5 possono dare risultati opposti
Stessa strategia, stesso simbolo, ma:
- dati diversi (Yahoo daily vs feed del broker, spesso intraday),
- timeframe di esecuzione diversi,
- gestione posizione diversa (SL/TP/trailing tarati separatamente).
Un edge trovato sul sito è quindi sempre un'**ipotesi da validare su MT5**, mai una
certezza diretta — vedi [[NEXUS EA - Screening Strategie (sito 10y)]].

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Panoramica]]
