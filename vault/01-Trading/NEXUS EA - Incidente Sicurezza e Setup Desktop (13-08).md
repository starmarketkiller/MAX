---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, security, deploy, mt5]
created: 2026-08-13
updated: 2026-08-13
---

# Incidente sicurezza e setup desktop (13/08)

Sessione con l'agente desktop (accesso a MetaTrader/MetaEditor/PC), su richiesta
di completare la catena EA→worker locale→backend Render dopo il lavoro remoto
dell'11-12/08 (CRT, FVG_CONT, TSI, rischio a livelli).

## Incidente: segreti in chiaro nel repo pubblico

Durante il setup, trovato che **45 file `.set`** (`results/sets/`) e **103
report `.htm`** (`results/reports/`) del tester MT5 — già committati nel
repository **pubblico** `starmarketkiller/MAX` — incorporavano in chiaro nei
parametri di input salvati:
- `InpWebToken=NexusGold2026xK9` (il bridge token che autentica EA + backend +
  worker LocalBridge in un singolo segreto — vedi `DEPLOY.md`, finding
  AUD0-SEC-003)
- `InpLicenseKey=NXS-4CF836035700`

Entrambi ora invalidati:
- **Bridge token**: già ruotato prima di questa sessione (quello attivo ora,
  confermato identico su Render/worker/EA: inizia con `PDYtHXvwmr...`).
- **License key**: revocata in via precauzionale durante questa sessione
  (`"active": false, "status": "REVOKED"`) — chiunque provi a usarla, con
  qualsiasi account, viene rifiutato dal backend.

Pulizia repo (fatta su `main` e su `claude/export-advisor-nexus-migrate-htnz34`):
`.gitignore` aggiornato (`results/sets/**/*.set`, `results/reports/*.htm`) e
file rimossi dal tracking git (restano su disco). **Commit non ancora fatto**
— il repo locale non aveva identità git configurata e non l'ho impostata da
solo (policy); resta da fare manualmente.

**Aperto, bassa urgenza ora che entrambi i segreti sono invalidati**: i
valori vecchi restano visibili nella storia dei commit finché non si fa un
`git filter-repo` + force-push. Decisione rimandata all'utente.

## Setup desktop completato

- **MetaTrader 5** (`C:\Program Files\MetaTrader 5`) aggiornato con `MQL5/`
  dal branch `claude/export-advisor-nexus-migrate-htnz34` (Experts/Include/
  Indicators/Demo), copia additiva.
- **Worker locale** (`C:\NEXUS\nexus_local_worker.py` + `nexus_worker.config.json`)
  configurato e avviato: `backend_url=https://nexus-backend-8o4y.onrender.com`,
  token confermato corretto, log puliti (nessun errore HTTP).
- **Preset EA**: usato `MQL5/Demo/NEXUS_Demo_MultiTF_12-08.set` (ufficiale,
  token lasciato vuoto di proposito nel repo) — copia locale con token
  compilato salvata in `MQL5/Presets/` della cartella dati MT5 (mai nel repo).
- **Redeploy Render dei fix di oggi (CRT/FVG_CONT/TSI)**: **ancora da fare**,
  azione manuale sulla dashboard (l'agente desktop non ha credenziali/CLI
  Render).

## Quasi-incidente: `robocopy /MIR` su cartella dati MT5

Un primo tentativo di sincronizzare `MQL5/` ha usato `/MIR` (mirror), che
cancella nella destinazione tutto ciò che non è nella sorgente. Cancellati:
libreria standard MT5 (Scripts/Examples, Include standard) — **auto-riparata
da MT5 al riavvio successivo**, nessun danno reale — più `Files\HYDRA`
(dati del vecchio EA, confermato obsoleto/non serve più) e un `.git` locale
che tracciava la sola cartella MQL5 (contenuto equivalente a quello già in
questo repo, nessuna perdita reale). Lezione: mai più `/MIR` su cartelle non
ispezionate a fondo, solo copie additive (`/E` senza `/PURGE`) d'ora in poi.

## Bug di compilazione trovato e corretto

`NXS_Profile_Risk` in `NXS_StrategyProfiles.mqh` non aveva più la firma
della funzione né la graffa di apertura (probabilmente persa in una modifica
del 12/08 sulla ritaratura del rischio a 5 livelli) — i suoi `if(name==...)
return X;` erano orfani, trattati dal compilatore come codice a livello
globale (37 errori `expressions are not allowed on a global scope` +
`undeclared identifier 'NXS_Profile_Risk'` in `NXS_Execution.mqh`).
Corretto aggiungendo `double NXS_Profile_Risk(const string name){` al punto
giusto. **Compila pulito ora** (solo 2 warning preesistenti, innocui: macro
`NXS_MAX_SIGNALS` ridefinita, conversione `ulong`→`long`). Non era mai stato
compilato dopo la modifica del 12/08 (fatta in sessione remota senza MT5).

## Vault

Questa nota e il resto di `vault/` (branch `claude/export-advisor-nexus-migrate-htnz34`,
superset di `main`: +7 note rispetto a main, nessuna cancellazione) sono
stati sincronizzati nel vault Obsidian effettivamente in uso
(`Downloads\MAX-main\MAX-main\vault`, l'unico dei due vault registrati con
`"open": true`) — copia additiva, verificato prima che non contenesse note
locali assenti dal repo.

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - Demo Multi-Timeframe Pronta (12-08)]] ·
[[NEXUS EA - Inventario Pulizia Repo (12-08)]] ·
[[DEC - Cambi di comportamento post-remediation]]
