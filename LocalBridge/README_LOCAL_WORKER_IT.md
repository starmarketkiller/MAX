# NEXUS Local MT5 Worker — Setup Guide (Italiano)

## Cosa fa?
Un piccolo script Python che gira sul tuo PC Windows e ascolta i comandi dal
web dashboard NEXUS in cloud:
- **Compila l'EA** (`compile_ea`) → metaeditor.exe /compile
- **Riavvia MT5** (`restart_mt5`) → taskkill + rilancio
- **Deploya i nuovi file MQL5** (`deploy_files`) → scrive in MQL5/Experts e MQL5/Include
- **Applica template** (`apply_template`) → scrive .tpl in MQL5/Profiles/Templates
- **Apre charts** (`open_chart`) → con profilo specifico
- **Heartbeat** ogni 30s → dashboard mostra online/offline

## Installazione (3 minuti)

### 1) Installa Python 3.10+
Scarica da https://python.org → spunta "Add Python to PATH".

### 2) Installa dipendenze
Apri **PowerShell** come amministratore e:
```powershell
pip install requests
```

### 3) Copia lo script
Copia `nexus_local_worker.py` in una cartella, es: `C:\NEXUS\`.

### 4) Primo avvio (crea config)
```powershell
cd C:\NEXUS
python nexus_local_worker.py
```
Lo script crea `nexus_worker.config.json` e si chiude. Aprilo e compila:
```json
{
  "backend_url":   "https://TUO-NEXUS.preview.emergentagent.com",
  "bridge_token":  "NEXUS_BRIDGE_TOKEN_2026",
  "host_id":       "default",
  "mt5_path":      "C:/Program Files/MetaTrader 5/terminal64.exe",
  "metaeditor":    "C:/Program Files/MetaTrader 5/metaeditor64.exe",
  "mql5_experts":  "C:/Users/TUONOME/AppData/Roaming/MetaQuotes/Terminal/<HASH>/MQL5/Experts",
  "mql5_include":  "C:/Users/TUONOME/AppData/Roaming/MetaQuotes/Terminal/<HASH>/MQL5/Include/NEXUS_v1",
  "poll_sec":      3
}
```
> Per trovare `<HASH>`: in MT5 menu → **File → Apri cartella dati** → la cartella che si apre è quella corretta.

### 5) Whitelist URL backend in MT5
**Strumenti → Opzioni → Expert Advisors**:
- ✓ Consenti WebRequest per i seguenti URL
- Aggiungi: `https://TUO-NEXUS.preview.emergentagent.com`

### 6) Avvio worker
```powershell
cd C:\NEXUS
python nexus_local_worker.py
```
Dovresti vedere:
```
[NEXUS Worker] v1.0.0 started
[NEXUS Worker] backend: https://...
```

### 7) Verifica nel dashboard
Apri il dashboard NEXUS → **Settings → Local Bridge**. Vedrai il worker **online** con badge verde.

---

## Autostart (Opzionale ma consigliato)
Per far partire il worker automaticamente all'avvio di Windows:

**Opzione A — Task Scheduler:**
1. Apri "Utilità di pianificazione"
2. "Crea attività" → trigger "All'accesso"
3. Azione → `python.exe` con argomento `C:\NEXUS\nexus_local_worker.py`
4. Spunta "Esegui con privilegi più elevati"

**Opzione B — NSSM (Service):**
```powershell
nssm install NEXUS-Worker "C:\Python310\python.exe" "C:\NEXUS\nexus_local_worker.py"
nssm start NEXUS-Worker
```

---

## Sicurezza
- Il worker espone una whitelist di azioni — non può eseguire codice arbitrario
- Il `shell` handler accetta solo comandi diagnostici (`dir`, `ipconfig`, `tasklist`, `where`, `echo`)
- Token `bridge_token` è privato — non condividerlo
- Tutte le comunicazioni HTTPS

## Troubleshooting
| Problema | Soluzione |
| --- | --- |
| `metaeditor non trovato` | Verifica path in config.json |
| `Compile failed exit_code=1` | Apri `compile.log` in MQL5/ folder per dettagli |
| Worker offline nel dashboard | Verifica firewall, bridge_token, backend_url |
| `WebRequest failed` in MT5 | URL non whitelistato (vedi step 5) |

## Aggiornamenti
Il worker stesso può essere aggiornato tramite `deploy_files` (futuro update OTA).
