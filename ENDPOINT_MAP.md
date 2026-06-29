# ENDPOINT_MAP — Frontend React ⇄ Backend NEXUS

Mappa **reale** estratta dal sorgente React (`frontend/src`, Create-React-App) vs
backend `server/app.py`. Tutti gli endpoint sono sotto `/api` (in `lib/api.js`
`API = ${REACT_APP_BACKEND_URL}/api`). ✅ = implementato e testato.

## 🔐 Autenticazione — cookie httpOnly (allineato al React)
`lib/api.js` usa `withCredentials:true` (niente Bearer in JS). Il backend ora:
- `POST /api/auth/login` `{email,password}` → setta cookie httpOnly `nexus_session` + ritorna `{ok,user,token}`
- `POST /api/auth/logout` → cancella il cookie
- `GET /api/auth/me` → oggetto utente `{email,name,role}`
- `require_user` accetta **cookie OPPURE** `Authorization: Bearer` (retrocompat sito statico)
- Env: `NEXUS_COOKIE_SECURE` (default `true`; su Render https va bene)

## Mappa endpoint

| Endpoint (`/api…`) | Metodo | Stato |
|---|---|---|
| `/auth/login` `/auth/logout` `/auth/me` | POST/POST/GET | ✅ (cookie) |
| `/ea/status` `/ea/health` `/ea/history` | GET | ✅ |
| `/command` | POST | ✅ |
| `/settings` `/settings/history` | GET/POST | ✅ |
| `/analytics/trades` `/summary` `/by_reason` | GET | ✅ reali |
| `/analytics/whatif` | POST | ✅ reale |
| `/analytics/calendar` `/heatmap` | GET | ✅ derivati dai trade |
| `/analytics/correlation` | GET | ✅ `demo:true` |
| `/analytics/shadow` | GET | ✅ |
| `/analytics/strategy_meta` | GET | ✅ |
| `/analytics/strategy_stats/latest` `/symbols` `/markdown` | GET | ✅ |
| `/analytics/strategy_stats/upload` | POST | ✅ |
| `/journal/tags` · `/trades/{ticket}/tag` | GET/POST | ✅ |
| `/license/list` `/summary` `/create` | GET/GET/POST | ✅ |
| `/license/{id}` | PATCH/DELETE | ✅ (`id`=key) |
| `/strategy_chain/config` | GET/PUT | ✅ |
| `/local_bridge/status` `/enqueue` | GET/POST | ✅ |
| `/backtest/run` `/optimize` `/management_report` `/multi_tf_report` | POST | ✅ `demo:true` |
| `/backtest/optimize/{jobId}` | GET | ✅ `demo:true` |
| `/backtest/presets` `/strategies` `/symbols` | GET | ✅ |
| `/backtest/locked_profile` (POST) `/locked_profile/all` (GET) | | ✅ |
| `/backtest/strategy_library` `?symbol` `/{jobId}` `/build` | GET/GET/POST | ✅ `demo:true` |
| `/calendar/upcoming` | GET | ✅ `demo:true` |
| `/chart/ohlc` `/chart/markers` | GET | ✅ (ohlc demo, markers dai trade) |
| `/coach/chat` | POST | ✅ API Claude |
| `/coach/proactive_alerts` `/quick_insights` `/daily_brief` | GET | ✅ deterministici |
| `/coach/apply_action` | POST | ✅ |
| `/coach/memory` (GET/POST) `/memory/{id}` (DELETE) | | ✅ |
| `/coach/notifications` (GET) `/notifications/{id}/read` (POST) | | ✅ |
| `/coach/history` | GET | ✅ (vuoto finché non si salva la chat) |
| `/coach/session/{id}` | DELETE | ✅ no-op |
| `/dashboard/overview` `/journal` `/strategy_stats` | GET | ✅ (usati dal sito statico) |
| `/downloads/list` `/downloads/local_worker` | GET | ✅ |

## Dati DEMO
Endpoint senza dati reali ritornano `"demo": true` (backtest, correlation, chart ohlc,
calendar, e analytics/strategie finché non arriva nulla dall'EA) → il frontend mostra
il badge "DEMO DATA".

## Da completare con il frontend React
1. **Build & serving** (FASE 3): ricostruire tooling CRA (package.json, craco/`@`-alias,
   tailwind+shadcn, `public/index.html`), `yarn build`, servire `build/` da FastAPI
   con SPA fallback. `REACT_APP_BACKEND_URL=""` (same-origin → `/api`).
2. **Motore di backtest reale** al posto dei `demo:true` (step separato).
3. **`parseCoachActions`** (`pages/coach/parseActions.js`): allineare il formato azione
   che il system prompt del Coach deve emettere.
