# ENDPOINT_MAP — Frontend React ⇄ Backend NEXUS

Mappa degli endpoint richiesti dal frontend React di Emergent (lista da
`ISTRUZIONI_CLAUDE_CODE.md`) e stato nel backend `server/app.py`.

> ⚠️ Il sorgente React non è ancora nel repo (`frontend/` assente): i nomi-campo
> sono allineati al **contratto EA/WebBridge** (noto e affidabile). Da riconciliare
> sul codice React quando arriva, specialmente il formato delle azioni che
> `parseCoachActions` si aspetta in `/coach/chat`.

Auth: tutto sotto `/api`. JWT Bearer per la dashboard; `X-Nexus-Token` per EA/worker.
`base path` del frontend = `/api`, quindi `api.get('/ea/status')` → `/api/ea/status`.

| Endpoint (`/api…`) | Metodo | Stato | Note / campi |
|---|---|---|---|
| `/auth/login` | POST | ✅ esistente | ritorna `{token,user}` |
| `/auth/me` | GET | ✅ esistente | |
| `/ea/status` | GET | 🆕 aggiunto | EA primario + lista `eas[]` con `_online` |
| `/ea/health` | GET | 🆕 aggiunto | online, version, account, balance, equity |
| `/ea/command` | POST | 🆕 aggiunto | JWT; accoda comando (`action`) per l'EA |
| `/ea/command` | GET | ✅ esistente | usato dall'EA (X-Nexus-Token) |
| `/ea/settings` | GET | ✅ esistente | letto dall'EA |
| `/settings` | GET/PUT/POST | 🆕 aggiunto | runtime settings (JWT) |
| `/strategies` | GET/POST/PUT | 🆕 aggiunto | enabled + stats; `demo:true` se nessun dato |
| `/analytics/trades` | GET | 🆕 aggiunto | campi `side,pnl,openPrice,closeTime,journal_tags,journal_rating` |
| `/analytics/summary` | GET | 🆕 aggiunto | net_pnl, win_rate, profit_factor |
| `/analytics/by_reason` | GET | 🆕 aggiunto | raggruppa per `reason` |
| `/analytics/whatif` | POST | 🆕 aggiunto | esclude strategie/reason e ricalcola P&L |
| `/journal/tags` | GET | 🆕 aggiunto | preset + tag usati |
| `/trades/{ticket}/tag` | POST | 🆕 aggiunto | salva `tags,rating,note` |
| `/license/list` | GET | 🆕 aggiunto | |
| `/license/create` | POST | 🆕 aggiunto | |
| `/license/{key}` | PATCH/DELETE | 🆕 aggiunto | |
| `/license/verify` | POST | ✅ esistente | usato dall'EA |
| `/strategy_chain/config` | GET/PUT | ✅ esistente | |
| `/local_bridge/status` | GET | ✅ esistente | |
| `/local_bridge/enqueue` | POST | ✅ esistente | |
| `/backtest/run` | POST | 🆕 aggiunto | `demo:true` (motore reale = step futuro) |
| `/backtest/optimize` | POST | 🆕 aggiunto | `demo:true` |
| `/backtest/management_report` | GET | 🆕 aggiunto | `demo:true` |
| `/backtest/multi_tf_report` | GET | 🆕 aggiunto | `demo:true` |
| `/backtest/locked_profile/all` | GET | 🆕 aggiunto | da `locked_profiles` reali |
| `/coach/chat` | POST | 🆕 aggiunto | API Claude (`ANTHROPIC_API_KEY`) |
| `/coach/proactive_alerts` | GET | 🆕 aggiunto | regole deterministiche su stato EA |
| `/coach/apply_action` | POST | 🆕 aggiunto | accoda comando EA |
| `/coach/memory` | GET/POST/DELETE | 🆕 aggiunto | note persistenti iniettate nel context |
| `/coach/notifications` | GET | 🆕 aggiunto | contatore non letti (+ `/read` POST) |
| `/dashboard/overview` | GET | ✅ esistente | |
| `/dashboard/journal` | GET | ✅ esistente | |
| `/dashboard/strategy_stats` | GET | ✅ esistente | |
| `/calendar` | GET | 🆕 aggiunto | `demo:true` (feed news reale = futuro) |
| `/downloads/local_worker` | GET | 🆕 aggiunto | scarica `nexus_local_worker.py` |

## AI Coach — come funziona
- `POST /api/coach/chat`: riceve `{messages:[{role,content}], context:{}}`, costruisce un
  system prompt con stato EA live + memoria persistente, chiama l'API Claude
  (`NEXUS_COACH_MODEL`, default `claude-opus-4-8`) e ritorna `{reply, demo, model}`.
- Senza `ANTHROPIC_API_KEY` ritorna `{demo:true, reply:"⚠️ Coach non disponibile…"}`.
- `proactive_alerts` non usa l'AI (regole su drawdown / anti-revenge / news / offline).

## Dati DEMO
Gli endpoint senza dati reali ritornano `"demo": true` nel JSON (backtest, calendar, e
strategie/analytics quando non è ancora arrivato nulla dall'EA), così il frontend può
mostrare il badge "DEMO DATA".

## Da fare quando arriva il frontend React
1. Verificare i nomi-campo esatti letti dai componenti e allinearli 1:1.
2. Definire il formato azione di `parseCoachActions` e farlo emettere dal system prompt.
3. Sostituire i `demo:true` di backtest con il motore reale (FASE 2 — step separato).
