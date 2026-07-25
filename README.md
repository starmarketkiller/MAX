# NEXUS — Trading System (self-hosted)

Sistema completo NEXUS migrato **fuori da Emergent**: il core di trading è
self-hostabile e non richiede Emergent.

> **AUD0-DOC-003 — precisazione.** Il README dichiarava "nessuna dipendenza da
> servizi esterni", contraddicendosi poi con Telegram, Anthropic e il deploy su
> cloud pubblico. La formulazione corretta è: il **core** gira in autonomia;
> alcune funzionalità **opzionali** dipendono da servizi esterni (Telegram per
> le notifiche, Anthropic per l'AI Coach, il provider cloud se non self-hosti).

---

## ⚠️ Stato del progetto: NO-GO per la produzione

Un audit completo del repository è in `docs/NEXUS_MASTER_PROJECT.md`; lo stato
di chiusura dei finding è in [`docs/REMEDIATION_STATUS.md`](docs/REMEDIATION_STATUS.md).

**Consentito:** sviluppo, simulazione, backtest controllato, conti demo.
**Bloccato:** trading con capitale reale, deploy remoto in produzione,
uso multi-account sullo stesso backend, modalità istituzionale dell'EA,
Virtual SL in modalità EXECUTE, azioni live dell'AI Coach.

Il backend **rifiuta di avviarsi** con `NEXUS_ENV` diverso da
DEVELOPMENT/SIMULATION finché restano credenziali di default o segreti
segnaposto. È voluto.

---

Il progetto ha **componenti principali** che parlano tra loro:

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
| `server/`      | Backend FastAPI + dashboard statica di fallback |
| `frontend/`    | Sorgente della dashboard React "cockpit" servita sotto `/app` |
| `contracts/`   | Contratti canonici (strategy registry, settings, comandi) e generatori |
| `deploy/`      | Manifest di deployment versionato |
| `docs/`        | Audit master, specifiche architetturali, stato della remediazione |

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
| `NEXUS_ADMIN_USER` / `NEXUS_ADMIN_PASSWORD` | Credenziali dashboard. La dashboard React (`/app`) usa un campo **email**: imposta `NEXUS_ADMIN_USER` come indirizzo email reale. Password di almeno 12 caratteri. |
| `NEXUS_JWT_SECRET` | Stringa lunga e casuale per firmare le sessioni. Se assente, il backend ne genererebbe una effimera e ogni riavvio invaliderebbe le sessioni: fuori dallo sviluppo l'avvio viene rifiutato. |
| `NEXUS_ENV` | `DEVELOPMENT` \| `SIMULATION` \| `DEMO` \| `PAPER` \| `LIVE`. Da `DEMO` in su i controlli fail-closed sono bloccanti. Un valore sconosciuto è trattato come `LIVE`. |
| `NEXUS_JWT_HOURS` | Durata sessione (default 12h, massimo 24h in ambiente hardened). |
| `NEXUS_ALLOWED_ORIGINS` | Origin ammesse per le mutazioni via cookie (anti-CSRF). |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | (Opzionale) per ricevere le notifiche su Telegram. |
| `NEXUS_LICENSE_MODE` | `strict` = valida solo le chiavi in tabella. `open` accetta **qualunque** chiave: è utile solo in sviluppo e viene rifiutato in ambiente hardened. |
| `NEXUS_COACH_ALLOW_ACTIONS` | L'AI Coach non ha autorità di esecuzione: produce proposte. Abilitabile solo in sviluppo. |
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
# modifica nexus_worker.config.json: backend_url (HTTPS) + bridge_token + path MT5
python LocalBridge\nexus_local_worker.py
```

> ⚠️ **Il worker scrive ed esegue codice sulla macchina di trading.**
> Eseguilo con un account Windows dedicato, con permessi limitati alla cartella
> MQL5. Prima di eseguirlo, verifica il digest dell'artefatto contro
> `GET /api/downloads/local_worker/checksum`. Il worker rifiuta di avviarsi con
> valori di esempio, token corto o `backend_url` non HTTPS. L'azione `shell`
> generica è stata rimossa (era esecuzione di comandi arbitrari).

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

Tutti gli endpoint EA/worker richiedono l'header `X-Nexus-Token`.

Gli endpoint dashboard usano un **cookie di sessione httpOnly** emesso da
`POST /api/auth/login` (il client React invia `withCredentials`). Le richieste
che modificano stato devono inoltre presentare l'header `X-Nexus-Csrf` con il
valore del cookie `nexus_csrf` (double-submit). Il vecchio `Authorization:
Bearer <jwt>` resta solo per la dashboard statica legacy ed è **rifiutato**
negli ambienti hardened (finding AUD0-DOC-005 / AUD0-SEC-007).

**EA → backend**
`POST /api/ea/push` · `GET /api/ea/command` (richiede `account_id` e `symbol`) ·
`POST /api/ea/command/ack` · `GET /api/ea/settings` ·
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
`GET/PUT /api/strategy_chain/config` · `GET /api/local_bridge/status` · `POST /api/local_bridge/enqueue` ·
`GET /api/ea/command_contract` · `GET /api/risk/policy` · `GET /api/audit/operator`

**Salute del servizio**
`GET /api/health` — liveness: prova solo che il processo risponde.
`GET /api/ready` — readiness: database scrivibile, migrazioni applicate,
preflight di sicurezza superato. Restituisce 503 con l'elenco dei problemi.

---

## ☁️ Deploy su cloud (URL pubblico per MT5)

Il backend è una singola app FastAPI con SQLite: gira su qualsiasi host che accetta un
container (Railway, Render, Fly.io, un VPS, ecc.). Punta `InpWebURL` (EA) e `backend_url`
(worker) all'URL pubblico HTTPS e ricordati di whitelistare quell'URL in MT5.

Guida completa in [`DEPLOY.md`](DEPLOY.md).

**Il build context dell'immagine è la root del repository**, non `server/`: il
backend serve anche il worker LocalBridge e il deployment manifest, che vivono
fuori da `server/`.

```bash
docker build -f server/Dockerfile -t nexus-backend .
```

I dati persistono nel volume Docker `nexus-data` (file `nexus.db`).
**Il volume non è un backup**: protegge dalla sostituzione del container, non
dalla corruzione né dalla cancellazione. Copia periodicamente `/data/nexus.db`
fuori dall'host e verifica il ripristino.

---

*Migrato da Emergent — progetto ora interamente self-hosted e indipendente.*
