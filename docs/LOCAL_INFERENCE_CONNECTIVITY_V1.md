# LOCAL_INFERENCE_CONNECTIVITY_V1

**Stato:** path locale (PC → tunnel → gateway → Ollama) **verificato end-to-end e funzionante**. Il path Render → Telegram richiede **un'unica azione manuale residua** dell'utente (impostare 2 variabili d'ambiente su Render — non eseguibile da qui, nessuna credenziale Render API disponibile in questo ambiente).

---

## Root cause (due problemi distinti, non uno)

1. **Il Local Inference Gateway non era in esecuzione.** `curl http://127.0.0.1:8765/v1/jarvis/health` falliva perché nessun processo ascoltava su quella porta — non un bug, semplicemente non era stato avviato in questa sessione del PC.
2. **Nessun tunnel autenticato esisteva.** `LocalBridge/start_gateway.ps1` e `ministral_router.py` presumono un "tunnel autenticato (Cloudflare Tunnel / Tailscale Funnel)" ma **nessuno dei due era mai stato installato o configurato** su questa macchina — architettura descritta nei commenti, mai implementata.

**Scoperta aggiuntiva, non ipotizzata nel task originale, trovata misurando i tempi reali**: una chiamata a freddo a `ministral-3:3b` (modello non ancora residente in Ollama — es. subito dopo l'avvio del gateway, o dopo che il `keep_alive` di default di Ollama scade) impiega **~49 secondi**; a caldo, **~6 secondi**. Il timeout di default del gateway era **8 secondi** — quasi garantito di fallire la prima richiesta reale con `MODEL_CALL_FAILED`/502. Stesso problema lato Render (`ministral_chat.py`, default 20s) e lato chiamata diretta di `/mistral` in `service.py` (45s, insufficiente col margine osservato).

---

## Cosa esisteva già (riusato, non duplicato)

- `LocalBridge/nexus_local_inference_gateway.py` — gateway completo, sicuro (auth Bearer, rate limit, size limit, bind 127.0.0.1), con le due route `/v1/jarvis/interpret` e `/v1/jarvis/chat` (quest'ultima aggiunta nella sessione precedente, TELEGRAM_MISTRAL_DIRECT_MODE_V1).
- `LocalBridge/start_gateway.ps1` — già corretto, carica `.env`, verifica il token, avvia il gateway. Non modificato.
- `LocalBridge/.env` — già conteneva `NEXUS_LOCAL_INFERENCE_GATEWAY_TOKEN` valido (64 caratteri).
- `server/jarvis_v1/ministral_chat.py` — client Render-side già pronto (sessione precedente), mai testato contro un gateway reale raggiungibile.
- Ollama — già installato, già con `ministral-3:3b` scaricato, già in autostart (`Startup\Ollama.lnk`).
- **Nessun secondo gateway/tunnel/orchestrator creato** — solo la parte mancante (tunnel) è stata aggiunta.

## Cosa ho modificato

1. **`LocalBridge/nexus_local_inference_gateway.py`**: `DEFAULT_TIMEOUT_SECONDS` 8→60s; aggiunto `_warmup_model()` (chiamata di riscaldamento in background thread all'avvio, non blocca l'accettazione di connessioni — così la primissima richiesta reale di un utente trova il modello già caldo, non pagando i 49s a freddo).
2. **`server/jarvis_v1/ministral_chat.py`**: `DEFAULT_TIMEOUT_SECONDS` 20→60s.
3. **`server/jarvis_v1/service.py`**: le due chiamate dirette a `call_local_model()` (`/mistral` e `query()`) 45→60s.
4. **`LocalBridge/cloudflared.exe`** (nuovo, gitignored, non committato — binario scaricato direttamente da GitHub Releases, non via winget: il tentativo winget non ha lasciato traccia verificabile su disco in questo ambiente sandboxato, il download diretto ha funzionato ed è più semplice da riprodurre).
5. **`LocalBridge/start_local_inference.ps1`** (nuovo) — lo script unico richiesto: verifica Ollama, avvia (o rileva già attivo, idempotente) il gateway, avvia (o rileva già attivo) il tunnel Cloudflare, **verifica la salute end-to-end attraverso il tunnel stesso** (non solo in locale), scrive l'URL pubblico corrente in `current_gateway_url.txt` (gitignored). Non stampa mai il token.
6. **`LocalBridge/register_startup_task.ps1`** (nuovo, non eseguito — vedi limiti) — registra `start_local_inference.ps1` come Scheduled Task a logon, finestra nascosta.
7. **`.gitignore`**: aggiunte `LocalBridge/cloudflared.exe`, `LocalBridge/*.log`, `LocalBridge/current_gateway_url.txt`.
8. **6 nuovi test** (`test_nexus_local_inference_gateway_v1.py` +4, `test_ministral_chat_v1.py` +1) sui nuovi default di timeout e sul warmup.

---

## Come si avvia (oggi, un comando)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "LocalBridge\start_local_inference.ps1"
```

Idempotente: se gateway/tunnel sono già attivi non li duplica, verifica solo che siano sani. Output tipico:

```
=== LOCAL_INFERENCE_CONNECTIVITY_V1 ===
[1/4] Verifica Ollama...          Ollama OK.
[2/4] Gateway locale...           Gateway OK (sano in locale).
[3/4] Tunnel Cloudflare...        Tunnel OK - URL pubblico: https://<random>.trycloudflare.com
[4/4] Health check end-to-end...  OK - raggiungibile pubblicamente tramite il tunnel.
```

## Come persiste dopo reboot

Ollama: già autostart (`Startup\Ollama.lnk`, preesistente). Gateway+tunnel: **script pronto ma non ancora registrato** — `register_startup_task.ps1` ha richiesto un permesso di sistema (`Register-ScheduledTask`) che l'ambiente sandboxato di questa sessione ha negato (accesso negato, non un errore di sintassi). Esegui tu stesso, una volta, da una PowerShell normale (non serve amministratore per un task scope-utente):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "LocalBridge\register_startup_task.ps1"
```

Da quel momento, ad ogni logon Windows la catena si avvia da sola, finestra nascosta. Per testarlo subito senza rifare il logon: `Start-ScheduledTask -TaskName "NEXUS Local Inference"`. Per rimuoverlo: `Unregister-ScheduledTask -TaskName "NEXUS Local Inference" -Confirm:$false`.

---

## Health check — risultati reali di questa sessione

| Check | Risultato |
|---|---|
| Ollama locale (`127.0.0.1:11434/api/version`) | ✅ raggiungibile |
| Gateway locale (`127.0.0.1:8765/v1/jarvis/health`) | ✅ `{"ok": true, "ollama_reachable": true}` |
| Ollama NON esposto attraverso il gateway (`/api/tags` via tunnel) | ✅ 404 (confermato, non solo presunto) |
| Tunnel pubblico, health attraverso il tunnel | ✅ `{"ok": true, "ollama_reachable": true}` (dopo fix retry DNS, vedi limiti) |
| Chat end-to-end attraverso il tunnel (`/v1/jarvis/chat`) | ✅ risposta reale di Ministral ricevuta, testato due volte (a freddo e a caldo) |
| Render → Telegram `/mistral` | ⏸️ **non verificabile da qui** — richiede l'azione manuale sotto |

---

## L'unica azione manuale residua (Render)

Non ho credenziali API Render in questo ambiente (nessun `RENDER_API_KEY`, nessun meccanismo esistente nel repo per impostare env var Render via API — i deploy avvengono tramite deploy hook URL, non la management API). Questa parte richiede te:

1. Vai sulla dashboard Render del servizio `nexus-backend`.
2. Imposta (Environment → Add Environment Variable):
   - `JARVIS_MINISTRAL_GATEWAY_URL` = il valore attuale in `LocalBridge\current_gateway_url.txt` sul PC (lo stampa anche `start_local_inference.ps1` ad ogni avvio).
   - `JARVIS_MINISTRAL_GATEWAY_TOKEN` = il valore di `NEXUS_LOCAL_INFERENCE_GATEWAY_TOKEN` in `LocalBridge\.env` (**non l'ho stampato qui** — apri tu il file).
3. Salva — Render riavvia il servizio con le nuove env var.
4. Testa da Telegram: `/mistral ciao, dimmi in una frase chi sei e attraverso quale sistema mi stai rispondendo`.

`render.yaml` non dichiara questi due nomi (non è un blueprint-level `sync: false` — vanno impostati a mano una volta, Render li persiste).

---

## Limiti residui (dichiarati, non nascosti)

- **L'URL del quick tunnel Cloudflare cambia ad ogni riavvio del processo `cloudflared`** (non ad ogni riavvio del PC se il processo resta vivo — ma sì dopo un riavvio del PC, o se il tunnel crasha). Dopo un riavvio, `JARVIS_MINISTRAL_GATEWAY_URL` su Render va aggiornato a mano con il nuovo valore da `current_gateway_url.txt`. Nessuna soluzione gratuita e stabile esiste senza un passo interattivo one-time che non posso eseguire io stesso (login browser Cloudflare/Tailscale) — percorso di upgrade descritto sotto, non implementato ora.
- **Registrazione dello Scheduled Task non eseguita da me** (permesso negato dal sandbox di questa sessione, probabilmente intenzionale per una modifica di configurazione persistente di sistema) — script pronto, un comando dell'utente.
- **Hostname trycloudflare.com nuovo**: la primissima risoluzione DNS di un hostname mai visto prima ha richiesto fino a ~20s in questa sessione (non istantanea) — lo script tiene conto di questo con un retry di ~80s, non è un bug se i primissimi tentativi falliscono.
- **`JARVIS_MINISTRAL_ROUTER_TIMEOUT_SECONDS`** (router cognitivo via gateway, non la chat diretta) ha ancora il default di 4s, stesso tipo di rischio trovato qui — non toccato perché il router è esplicitamente dormiente/OFF di default e fuori dallo scope esplicito di questo task; segnalato per una futura attivazione.
- Render → Telegram `/mistral` end-to-end **non testato da questa sessione** (richiede l'azione manuale sopra prima di poterlo verificare).

## Upgrade opzionale (non fatto ora): URL stabile

Per un hostname che non cambia mai (zero manutenzione dopo reboot), serve UNA delle due (richiede login browser una tantum, non eseguibile da qui):
- **Cloudflare Tunnel con nome** (`cloudflared tunnel login` + `cloudflared tunnel create`) — richiede un dominio su Cloudflare.
- **Tailscale Funnel** (`tailscale up` + `tailscale funnel 8765`) — hostname stabile `https://<device>.<tailnet>.ts.net`, non richiede un dominio proprio.

---

**Non dichiaro il marker finale `LOCAL_INFERENCE_CONNECTIVITY_V1_CANONICAL` in questo momento**: la parte locale (Ollama → Gateway → Tunnel, inclusa la chiamata `/v1/jarvis/chat` reale attraverso il tunnel pubblico) è verificata end-to-end e funzionante, ma il path completo richiesto dal task (Telegram → Render → tunnel → Gateway) non è stato testato perché richiede l'azione manuale su Render descritta sopra, che non posso eseguire io. Dopo che imposti le 2 env var su Render e confermi `/mistral` da Telegram, il marker è:

LOCAL_INFERENCE_CONNECTIVITY_V1_CANONICAL

Se preferisci chiudere comunque qui dato che la parte "mia" è finita: **LOCAL_INFERENCE_CONNECTIVITY_V1_PARTIAL_RENDER_ENV_PENDING**.
