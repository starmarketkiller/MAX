# Deploy del backend NEXUS su cloud (con URL pubblico)

Guida passo-passo. Alla fine avrai un indirizzo tipo
`https://nexus-backend-xxxx.onrender.com` che userai nell'EA e nella dashboard.

---

## ⚠️ Leggere prima di procedere

L'audit del progetto (`docs/NEXUS_MASTER_PROJECT.md`) classifica lo stato
corrente come **NO-GO per la produzione**. Un deployment pubblico raggiungibile
va usato **solo** per sviluppo, simulazione e conti demo.

Restano bloccati, come indicato in `docs/REMEDIATION_STATUS.md`:

- trading con capitale reale;
- operazione multi-account sullo stesso backend;
- modalità istituzionale dell'EA;
- Virtual SL in modalità EXECUTE;
- azioni live dell'AI Coach.

Il backend **rifiuta di avviarsi** con `NEXUS_ENV=LIVE` finché restano
credenziali di default o segreti segnaposto: è un comportamento voluto.

---

## Generare i segreti (da fare per primo)

Ogni valore va generato, mai copiato da questa guida:

```bash
# token del bridge (EA + backend + worker)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# segreto di firma delle sessioni
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Nota di sicurezza (finding AUD0-SEC-003): oggi **un solo token** autentica EA,
backend e worker LocalBridge. Chi lo ottiene può impersonare tutti e tre. È un
limite architetturale noto, in attesa di credenziali per-principale: trattalo
come un segreto di massimo valore e ruotalo se sospetti una compromissione.

---

## Opzione consigliata: Render.com

1. Vai su **https://render.com** e registrati (puoi usare "Sign up with GitHub").
2. Collega il tuo account GitHub e autorizza l'accesso al repository **`starmarketkiller/MAX`**.
3. In alto a destra: **New ▸ Blueprint**.
4. Seleziona il repo **MAX** e il branch **`main`**. Render legge `render.yaml`
   e prepara il servizio "nexus-backend".
5. Render chiederà i valori marcati `sync: false`:

   | Variabile | Valore |
   |---|---|
   | `NEXUS_BRIDGE_TOKEN` | il token generato sopra (lo stesso di EA e worker) |
   | `NEXUS_ADMIN_USER` | il tuo indirizzo email — la dashboard React presenta il campo come email |
   | `NEXUS_ADMIN_PASSWORD` | minimo 12 caratteri, non riutilizzata altrove |
   | `NEXUS_ALLOWED_ORIGINS` | l'URL pubblico del servizio, es. `https://nexus-backend-xxxx.onrender.com` (protezione CSRF) |
   | `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | vuoti se non usi Telegram |
   | `ANTHROPIC_API_KEY` | vuoto se non usi l'AI Coach |

   `NEXUS_JWT_SECRET` viene generato da Render. `NEXUS_ENV=LIVE`,
   `NEXUS_LICENSE_MODE=strict` e `NEXUS_JWT_HOURS=12` sono già nel blueprint.

6. Clicca **Apply / Create**. Render costruisce e avvia (2-3 minuti).
7. Quando è verde ("Live"), copia l'**URL pubblico**: è il tuo backend.

> **Deploy automatico disattivato.** `autoDeploy: false` è intenzionale
> (finding AUD0-DEPLOY-RENDER-002): prima ogni commit sul branch di default
> finiva direttamente in produzione, senza gate di CI. Ora la promozione è
> manuale, dopo che la CI è verde.

> 💡 Il piano **Free** si "addormenta" dopo ~15 min di inattività: la prima
> richiesta dopo la pausa è lenta e l'EA potrebbe vedere qualche errore finché
> si risveglia. Nel `render.yaml` è impostato `plan: starter`.

### Verificare che funzioni

Due endpoint distinti, con significati diversi:

| Endpoint | Cosa prova |
|---|---|
| `https://IL-TUO-URL/api/health` | **Solo** che il processo risponde (liveness) |
| `https://IL-TUO-URL/api/ready` | Database scrivibile, migrazioni applicate, preflight di sicurezza superato |

Usa `/api/ready` per giudicare se il servizio è realmente utilizzabile. Se
restituisce 503, il corpo della risposta elenca esattamente cosa manca.

Poi apri `https://IL-TUO-URL/` → vedi la pagina di login della dashboard.
Il form **non** è precompilato: usa le credenziali che hai impostato tu.

---

## Dopo il deploy: collega l'EA

In MetaTrader 5, proprietà dell'EA NEXUS:

- `InpWebURL` = `https://IL-TUO-URL` (l'indirizzo Render, **senza** slash finale)
- `InpWebToken` = lo stesso `NEXUS_BRIDGE_TOKEN` messo su Render
- `InpEnableWebSync` = `true`

In MT5: **Strumenti ▸ Opzioni ▸ Expert Advisors ▸ Consenti WebRequest** →
aggiungi `https://IL-TUO-URL`. Riattacca l'EA al grafico.

In pochi secondi l'EA comparirà **ONLINE** nella dashboard.

> L'EA dichiara account e simbolo a ogni polling dei comandi: il backend
> consegna solo i comandi indirizzati a quella specifica istanza
> (finding AUD0-CMD-002). Un comando emesso per un altro account/simbolo non
> viene mai eseguito.

---

## LocalBridge worker (compile/restart/deploy remoto)

Il worker **scrive ed esegue codice** sulla tua macchina di trading. Prima di
installarlo:

1. Scarica il worker dalla dashboard (rotta autenticata) e **verifica il
   digest** contro `GET /api/downloads/local_worker/checksum`.
2. Eseguilo con un account Windows dedicato, con permessi limitati alla sola
   cartella MQL5.
3. Compila `nexus_worker.config.json`: il worker rifiuta di avviarsi con valori
   di esempio, token corto o `backend_url` non HTTPS.

L'azione `shell` generica è stata **rimossa** dal worker (finding
AUD0-WORKER-SHELL-001): permetteva esecuzione di comandi arbitrari.

---

## Alternativa: Railway.app

1. Vai su **https://railway.app** → **New Project ▸ Deploy from GitHub repo** → scegli `MAX`.
2. Nelle impostazioni del servizio: **Root Directory = `.`** e
   **Dockerfile Path = `server/Dockerfile`**. Il context deve essere la root
   del repository, altrimenti worker e deployment manifest non finiscono
   nell'immagine (finding AUD0-DEP-010 / AUD0-DEP-011).
3. Sezione **Variables**: aggiungi `NEXUS_ENV=LIVE`, `NEXUS_BRIDGE_TOKEN`,
   `NEXUS_ADMIN_USER`, `NEXUS_ADMIN_PASSWORD`, `NEXUS_JWT_SECRET`,
   `NEXUS_JWT_HOURS=12`, `NEXUS_DB_PATH=/data/nexus.db`,
   `NEXUS_LICENSE_MODE=strict`, `NEXUS_ALLOWED_ORIGINS=<url pubblico>`.
4. Sezione **Settings ▸ Volumes**: monta un volume su `/data` (per il database).
5. **Settings ▸ Networking ▸ Generate Domain** per ottenere l'URL pubblico.

Railway resta sempre acceso (consumo a credito).

---

## Backup del database

Il volume persistente **non è un backup**: protegge dalla sostituzione del
container, non dalla corruzione né dalla cancellazione. Nessuna procedura di
backup automatico è ancora implementata (finding AUD0-DB-014). Finché non
esiste, copia periodicamente `/data/nexus.db` fuori dall'host e **verifica il
ripristino**: un backup mai testato non è un backup.
