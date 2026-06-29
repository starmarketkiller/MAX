# NEXUS — Trading System (self-hosted)

Sistema completo NEXUS migrato **fuori da Emergent**: ora tutto il progetto vive qui ed è
self-hosted. Nessuna dipendenza da servizi esterni.

Il progetto ha **3 componenti** che parlano tra loro:

```
┌────────────────┐   push stato + poll comandi   ┌──────────────────────┐
│  EA MetaTrader │ ───────────────────────────►  │  Backend + Dashboard │
│  (MQL5)        │ ◄───────────────────────────  │  (server/ — FastAPI) │
└────────────────┘     X-Nexus-Token (HTTP)       └──────────┬───────────┘
                                                              │ JWT login
┌────────────────┐   poll comandi / heartbeat                ▼
│ LocalBridge    │ ◄──────────────────────────────  Dashboard web (browser)
│ worker (PC)    │ ──────────────────────────────►  compila/riavvia MT5
└────────────────┘
```

| Cartella       | Cosa contiene |
|----------------|---------------|
| `MQL5/`        | L'Expert Advisor `NEXUS_EA_v2.mq5` + tutti gli include `NXS_*.mqh` |
| `LocalBridge/` | Il worker Python che gira sul PC con MT5 (compila EA, riavvia, deploy file) |
| `server/`      | **NUOVO** — backend FastAPI + dashboard web che sostituisce Emergent |

---

## 🚀 Avvio rapido del backend (1 comando con Docker)

```bash
cd server
cp .env.example .env        # poi MODIFICA i valori (vedi sotto)
cd ..
docker compose up -d --build
```

Apri il browser su **http://localhost:8001** → fai login con le credenziali che hai messo
nel `.env`. Fatto: il sito è online.

### Senza Docker (serve Python 3.10+)

```bash
cd server
python -m venv .venv && source .venv/bin/activate   # su Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # modifica i valori
set -a; source .env; set +a # carica le variabili (Linux/Mac)
uvicorn app:app --host 0.0.0.0 --port 8001
```

---

## ⚙️ Configurazione (`server/.env`)

Apri `server/.env` e imposta **almeno** questi valori:

| Variabile | A cosa serve |
|-----------|--------------|
| `NEXUS_BRIDGE_TOKEN` | Token condiviso EA ↔ Backend ↔ Worker. **Deve essere identico** ovunque. |
| `NEXUS_ADMIN_USER` / `NEXUS_ADMIN_PASSWORD` | Credenziali dashboard. ⚠️ La dashboard React (`/app`) usa un campo **email**: imposta `NEXUS_ADMIN_USER` come email (es. `admin@nexus.local`). |
| `NEXUS_JWT_SECRET` | Stringa lunga e casuale per firmare le sessioni. |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | (Opzionale) per ricevere le notifiche su Telegram. |
| `NEXUS_LICENSE_MODE` | `open` = ogni chiave è valida (consigliato self-hosted). |
| `ANTHROPIC_API_KEY` | (Opzionale) chiave API Claude per l'**AI Coach** (`/api/coach/chat`). Senza, il Coach risponde "non disponibile". |
| `NEXUS_COACH_MODEL` | Modello del Coach (default `claude-opus-4-8`). |

---

## 🔌 Collegare l'EA al tuo nuovo backend (addio Emergent)

Nelle proprietà dell'EA in MetaTrader 5 cambia **un solo parametro**:

| Input EA | Valore |
|----------|--------|
| `InpWebURL` | l'indirizzo del tuo backend, es. `http://192.168.1.50:8001` (PC in rete) o `http://localhost:8001` (stesso PC) o l'URL del tuo VPS |
| `InpWebToken` | **lo stesso** valore di `NEXUS_BRIDGE_TOKEN` nel `.env` |
| `InpEnableWebSync` | `true` |

Poi in MT5: **Strumenti → Opzioni → Expert Advisors → Consenti WebRequest** e aggiungi
l'URL del backend alla whitelist. Riavvia l'EA. Vedrai l'EA comparire "ONLINE" nella
dashboard entro pochi secondi.

> ⚠️ MT5 permette WebRequest solo verso `http`/`https` espliciti. Se il backend è su un
> altro PC usa l'IP della macchina (non `127.0.0.1`).

---

## 🖥️ Collegare il LocalBridge worker (controllo MT5 da remoto)

Sul PC Windows dove gira MT5:

```powershell
pip install requests
copy LocalBridge\nexus_worker.config.example.json nexus_worker.config.json
# modifica nexus_worker.config.json: backend_url + bridge_token + i path MT5
python LocalBridge\nexus_local_worker.py
```

Dettagli completi in [`LocalBridge/README_LOCAL_WORKER_IT.md`](LocalBridge/README_LOCAL_WORKER_IT.md).
Il worker comparirà nella dashboard sotto **Local Bridge**.

---

## 🖥️ Due dashboard

- **`/app`** — la **dashboard React "cockpit"** completa (Overview, Live Chart, Strategie, Analytics, Journal, **AI Coach**, Backtest, Risk, MT5 Bridge, Calendar, Licenze, Settings). È il frontend principale. Login con email/password (cookie httpOnly).
- **`/login.html`** — una dashboard statica leggera di fallback (stesso backend).

Il sorgente React è in `frontend/`; la build è servita da FastAPI sotto `/app`.
Per ricostruirla: `cd frontend && npm install --legacy-peer-deps && npm run build`,
poi copia `frontend/build/` in `server/static/app/`.

## 🌐 Dashboard statica — cosa puoi fare

- **Panoramica** — stato live di ogni EA (balance, equity, P&L, drawdown, HTF/velocity, sessione) + posizioni aperte, con pulsanti **Pausa / Riprendi / Chiudi tutto / Chiudi posizione**.
- **Journal** — storico trade sincronizzato dall'EA con riepilogo P&L e win rate.
- **Strategie** — statistiche per strategia (called/signals/executed/win/loss/health).
- **Strategy Chain** — configura Smart Continuation & Smart Reverse (v2.0.13).
- **Settings** — override runtime live (rischio, soglie score, filtri) senza ricompilare l'EA, + locked profiles per symbol.
- **Local Bridge** — stato worker e invio comandi (compile/restart/ping).

---

## 📡 API (contratto con EA e worker)

Tutti gli endpoint EA/worker richiedono l'header `X-Nexus-Token`. Gli endpoint dashboard
richiedono `Authorization: Bearer <jwt>` ottenuto da `POST /api/auth/login`.

**EA → backend**
`POST /api/ea/push` · `GET /api/ea/command` · `GET /api/ea/settings` ·
`GET /api/ea/locked_profile` · `POST /api/ea/strategy_stats` ·
`POST /api/ea/trade_history_sync` · `POST /api/ea/trade_reason` ·
`POST /api/ea/shadow_trades` · `POST /api/ea/visual_objects` ·
`POST /api/license/verify` · `POST /api/notify/telegram` ·
`GET /api/strategy_chain/config_for_ea`

**Worker ↔ backend**
`POST /api/local_bridge/heartbeat` · `GET /api/local_bridge/poll` · `POST /api/local_bridge/ack`

**Dashboard**
`POST /api/auth/login` · `GET /api/dashboard/overview` · `POST /api/dashboard/command` ·
`GET /api/dashboard/journal` · `GET /api/dashboard/strategy_stats` ·
`GET/PUT /api/dashboard/settings` · `GET/PUT /api/dashboard/locked_profiles` ·
`GET/PUT /api/strategy_chain/config` · `GET /api/local_bridge/status` · `POST /api/local_bridge/enqueue`

---

## ☁️ Deploy su cloud (URL pubblico per MT5)

Il backend è una singola app FastAPI con SQLite: gira su qualsiasi host che accetta un
container (Railway, Render, Fly.io, un VPS, ecc.). Punta `InpWebURL` (EA) e `backend_url`
(worker) all'URL pubblico HTTPS e ricordati di whitelistare quell'URL in MT5.

I dati persistono nel volume Docker `nexus-data` (file `nexus.db`).

---

*Migrato da Emergent — progetto ora interamente self-hosted e indipendente.*
