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

> **AUD0-DOC-006 — questa non è una pipeline di rilascio.** Copiare a mano gli
> artefatti significa che l'immagine può contenere un frontend costruito da un
> commit diverso da quello del backend, senza che nulla lo segnali. La CI
> costruisce il frontend (`frontend-build`) ma non ne pubblica l'artefatto
> versionato: finché è così, **verifica a ogni rilascio** che
> `server/static/app/` provenga dallo stesso commit del backend. È un difetto
> aperto, non una procedura approvata.

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

---

## Precisazioni dell'audit su questo documento

Punti in cui il README diceva meno di quanto serviva, o lo diceva in modo
ambiguo. Sono qui invece che sparsi nel testo, così restano leggibili insieme.

### Autenticazione — chi usa cosa (AUD0-DOC-002)

Il documento descriveva la dashboard React come autenticata via cookie httpOnly
e, poche righe dopo, dichiarava genericamente che le rotte della dashboard
richiedono un Bearer JWT. Sono due meccanismi diversi e la distinzione conta:

| Client | Autenticazione | Protezione CSRF |
|---|---|---|
| Dashboard React (`/app`) | Cookie di sessione `httpOnly` | **Sì** — double-submit: header `X-Nexus-Csrf` + cookie `nexus_csrf`, legati al `jti` del token |
| Script / integrazioni | `Authorization: Bearer <JWT>` | Non applicabile: un client Bearer non invia cookie automaticamente |
| EA MetaTrader e worker LocalBridge | Header `X-Nexus-Token` | Non applicabile |

In DEMO/PAPER/LIVE il Bearer è **rifiutato** sulle rotte di dashboard: in
ambiente indurito l'unico canale umano è il cookie di sessione, che è
revocabile lato server.

### LocalBridge — cosa comporta davvero (AUD0-DOC-004)

Il worker era presentato come una comoda funzione di controllo remoto. Va detto
per intero, perché il rischio non è teorico:

- il worker **esegue comandi sul PC** dove gira MT5 (compilazione, deploy di
  file, riavvio del terminale);
- l'esecuzione di shell arbitraria **è stata rimossa**: restano solo azioni
  tipizzate con percorsi e digest verificati;
- il deploy richiede **SHA-256 per ogni file**, mette in staging, attiva in modo
  atomico e fa rollback se qualcosa non torna;
- il riavvio termina **solo** l'eseguibile configurato, non processi arbitrari;
- fuori da Windows il riavvio è un errore permanente, non un tentativo;
- l'host deve essere **arruolato esplicitamente** prima che i suoi heartbeat
  vengano accettati.

Resta un fatto da tenere presente: il token del bridge è **condiviso** fra le
istanze. Chi lo possiede può impersonare qualunque EA o worker. Vedi
`docs/NORMATIVE_CONFORMANCE.md` (NEXUS-ID-004) per lo stato di questa lacuna.

### Il sito statico e `/app` sono pubblici — di proposito (AUD0-API-006)

Le rotte statiche e l'applicazione React non richiedono autenticazione: sono
l'involucro, non i dati. Ogni chiamata API che espone dati operativi passa da
`require_user` o `require_mutation`. La conseguenza pratica: il bundle React
**non deve contenere segreti** — non li contiene, e la CI ha uno scanner che lo
verifica ad ogni push.

### I grafici a candele sono sintetici (AUD0-DATA-003)

L'endpoint dei grafici genera candele matematiche e dichiara la provenienza
`SYNTHETIC_DATA`. Non sono dati di mercato reali. La dashboard deve mostrare
quella provenienza in modo visibile e **non** mescolare candele sintetiche con
marcatori di trade reali senza avvertimento: due dati con affidabilità diverse
nello stesso grafico si leggono come se fossero la stessa cosa.

### Evidenza di esecuzione MT5 — assente (AUD0-TEST-001)

Nessuna delle modifiche a `MQL5/` è stata compilata in MetaEditor né eseguita in
Strategy Tester in questo ambiente: gli strumenti non ci sono. La verifica fatta
qui è statica (bilanciamento dei blocchi, unicità delle definizioni, ordine di
dichiarazione fra moduli, coerenza con il registro canonico). **Prima di usare
capitale reale**, l'EA va compilato e fatto girare in Strategy Tester e su conto
demo: è un passo obbligatorio, non una formalità.

### Identificatori dei finding, non numeri di PR (AUD0-GOV-001)

Le etichette `PR6`/`PR7`/`PR8` nella storia del repository non corrispondono
sempre al numero della pull request su GitHub. Per riferirsi a un lavoro, usa
gli **identificatori dei finding** (`AUD0-*`, `NXS-*`, `NEXUS-*`): sono
immutabili e tracciabili in `docs/REMEDIATION_STATUS.md`.

### Inventario dei file (AUD0-INV-001)

L'inventario originale della migrazione non copre più il repository: dopo la
migrazione sono arrivati `NXS_InstManage.mqh`, `NXS_PositionCoordinator.mqh`,
`NXS_TradeLedger.mqh`, `NXS_StrategyRegistry.mqh`, `NXS_Intent.mqh`,
`NXS_Outbox.mqh`, il sorgente React, i contratti canonici, i test e i documenti
di architettura. La tabella delle cartelle più in alto in questo README è
l'inventario corrente; `deploy/deployment-manifest.json` è quello **verificabile
per digest** degli artefatti che vengono distribuiti.
