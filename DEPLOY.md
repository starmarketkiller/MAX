# Deploy del backend NEXUS su cloud (con URL pubblico)

Guida passo-passo, niente comandi sul tuo PC. Alla fine avrai un indirizzo tipo
`https://nexus-backend-xxxx.onrender.com` che userai nell'EA e nella dashboard.

## Opzione consigliata: Render.com (gratis per partire)

1. Vai su **https://render.com** e registrati (puoi usare "Sign up with GitHub").
2. Collega il tuo account GitHub e autorizza l'accesso al repository **`starmarketkiller/MAX`**.
3. In alto a destra: **New ▸ Blueprint**.
4. Seleziona il repo **MAX** e il branch **`claude/export-advisor-nexus-migrate-htnz34`**
   (o `main` dopo che avremo unito le modifiche). Render legge il file `render.yaml`
   da solo e prepara il servizio "nexus-backend".
5. Render ti chiederà di compilare i valori segnati come "sync: false":
   - **NEXUS_BRIDGE_TOKEN** → scrivi un token a tua scelta, es. `NEXUS_BRIDGE_TOKEN_2026`
     (lo stesso che metterai nell'EA e nel worker).
   - **NEXUS_ADMIN_PASSWORD** → la password con cui entrerai nella dashboard.
   - **TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID** → lasciali vuoti se non usi Telegram.
6. Clicca **Apply / Create**. Render costruisce e avvia (2-3 minuti).
7. Quando è verde ("Live"), copia l'**URL pubblico** in cima alla pagina del servizio.
   Quello è il tuo backend.

> 💡 Il piano **Free** si "addormenta" dopo ~15 min di inattività: la prima richiesta dopo
> la pausa è lenta e l'EA potrebbe vedere qualche errore finché si risveglia. Per un bot
> sempre attivo passa al piano **Starter** (pochi $/mese): nel `render.yaml` è già impostato
> `plan: starter`.

### Verifica che funzioni
Apri nel browser: `https://IL-TUO-URL/api/health` → deve rispondere `{"ok": true, ...}`.
Poi apri `https://IL-TUO-URL/` → vedi la pagina di login della dashboard.

---

## Dopo il deploy: collega l'EA

In MetaTrader 5, proprietà dell'EA NEXUS:
- `InpWebURL` = `https://IL-TUO-URL`  (l'indirizzo Render, **senza** slash finale)
- `InpWebToken` = lo stesso `NEXUS_BRIDGE_TOKEN` messo su Render
- `InpEnableWebSync` = `true`

In MT5: **Strumenti ▸ Opzioni ▸ Expert Advisors ▸ Consenti WebRequest** → aggiungi
`https://IL-TUO-URL`. Riattacca l'EA al grafico.

In pochi secondi l'EA comparirà **ONLINE** nella dashboard.

---

## Alternativa: Railway.app

1. Vai su **https://railway.app** → **New Project ▸ Deploy from GitHub repo** → scegli `MAX`.
2. Nelle impostazioni del servizio: **Root Directory = `server`** (così usa il Dockerfile).
3. Sezione **Variables**: aggiungi `NEXUS_BRIDGE_TOKEN`, `NEXUS_ADMIN_PASSWORD`,
   `NEXUS_JWT_SECRET`, `NEXUS_DB_PATH=/data/nexus.db`, `NEXUS_LICENSE_MODE=open`.
4. Sezione **Settings ▸ Volumes**: monta un volume su `/data` (per il database).
5. **Settings ▸ Networking ▸ Generate Domain** per ottenere l'URL pubblico.

Railway resta sempre acceso (consumo a credito).
