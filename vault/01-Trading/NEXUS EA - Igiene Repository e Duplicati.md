---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, repository, duplicati, igiene, audit]
created: 2026-07-25
updated: 2026-07-25
---

# NEXUS EA — igiene del repository e file duplicati

Scansione completa dei file tracciati da git, fatta con hash SHA-256 sul contenuto
(non sui nomi). Due dei risultati non sono questioni di spazio disco: sono problemi
di **validità dei dati** e di **sicurezza**.

## Il quadro in numeri

| | Valore |
|---|---|
| File tracciati | 674 |
| Dimensione totale | 448,4 MB |
| Spazio occupato da copie identiche | **257,5 MB (57,4%)** |
| Gruppi di file byte-identici | 10 |
| Cartella `results/` | 438,5 MB su 448,4 (97,8%) |

Il repository è per il 98% risultati di backtest, e più della metà del suo peso
sono copie dello stesso file.

---

## 1. Report di strategie diverse con contenuto identico ⚠️

**Questo non è spreco di spazio: è un dato che afferma il falso.**

Cinque coppie di report Strategy Tester hanno nomi che dichiarano strategie diverse
ma sono **byte per byte lo stesso file**, parametri di input inclusi:

| File A | File B |
|---|---|
| `ALL_ON_20260706_100304.htm` | `InpStrat_ADX_RSI_20260706_131648.htm` |
| `ALL_ON_20260706_170217.htm` | `VAL_Selector_26_MalaysianSNR_20260706_161936.htm` |
| `InpStrat_ADX_RSI_20260705_012022.htm` | `InpStrat_AMD_Reversal_20260705_015300.htm` |
| `InpStrat_BB_SQUEEZE_20260706_175739.htm` | `InpStrat_BJORGUM_20260706_180314.htm` |
| `AB_NoExh_FVG_MIT_20260706_093803.htm` | `AB_NoExh_TURTLE_SOUP_20260706_084856.htm` |

Verificato: aprendo `InpStrat_BJORGUM_...htm` la sezione parametri contiene gli
stessi input di `InpStrat_BB_SQUEEZE_...htm`. Il nome del file dice "BJORGUM", il
contenuto no.

**Le due spiegazioni possibili sono entrambe gravi:**

1. il `.set` non è stato applicato e la passata ha rigirato la configurazione
   precedente — allora quel risultato **non riguarda la strategia che dice**;
2. il report è stato copiato/rinominato — allora **non esiste** un risultato per
   una delle due strategie.

In entrambi i casi qualsiasi conclusione tratta da quei file è priva di fondamento.
Se una di queste passate è finita nelle valutazioni di
[[NEXUS EA - Screening Strategie (sito 10y)]] o nel ranking per strategia, va
rifatta prima di ricostruirci sopra un giudizio.

> È esattamente il difetto che l'audit chiamava `AUD0-MQL-014` (i CSV di
> ottimizzazione scritti da agenti paralleli senza identità di run). La correzione
> è già nel codice: ogni riga del CSV porta ora `run_id` derivato dai parametri
> della passata, l'agente e l'istante di avvio. Due passate con la stessa
> configurazione producono lo stesso `run_id` — quindi un duplicato si **riconosce**
> invece di sembrare un secondo risultato indipendente.

**Azione:** ri-eseguire le 5 coppie con identità di run attiva, oppure archiviarle
dichiarandole non valide. Non lasciarle dove sono con quei nomi.

---

## 2. 250 MB di snapshot di trade identici

Due gruppi da 6 copie ciascuno, in `results/reports/sweep37/trades_snapshots/`:

- 6 file da **25,1 MB** identici: `..._011842_S05.csv` … `..._012304_S30.csv`
- 6 file da **25,8 MB** identici: `..._194309_S05.csv` … `..._194950_S15.csv`

I suffissi (`S05`, `S10`, `S15`, `S20`, `S25`, `S30`) suggeriscono passate diverse
dello sweep. Il contenuto dice che sono la stessa passata salvata sei volte.
Stessa natura del punto 1, su scala maggiore: **10 snapshot su 12 non contengono
ciò che il nome promette.**

**Azione:** conservare un file per gruppo, spostare gli altri fuori da git (o
cancellarli). Recupero: ~250 MB, il 56% del repository.

---

## 3. Il file seed è una copia di un artefatto di ricerca

```
results/best_per_strategy_multitf_XAUUSD.json  ==  server/seed_recipe.json
```

Byte-identici (9,4 KB). `server/seed_recipe.json` viene caricato all'avvio del
backend e popola configurazione operativa. Significa che **un risultato di ricerca
è diventato, per copia manuale, configurazione di produzione** — senza revisione,
senza versione, senza un momento in cui qualcuno abbia detto "questo è approvato".

Se qualcuno rigenera l'analisi e ricopia il file, la configurazione operativa
cambia senza che nulla lo segnali.

> Mitigazione già applicata: i seed non girano più negli ambienti induriti
> (`NEXUS_SEED_ON_START=false` è il default in DEMO/PAPER/LIVE — finding
> `AUD0-DB-006`). Ma la copia manuale resta la procedura, ed è fragile.

**Azione:** decidere quale dei due è la fonte. Se il seed deve derivare
dall'analisi, generarlo con uno script versionato, non copiandolo.

---

## 4. Coppie di statistiche identiche

```
V232_3W_20260710_191201_stats.csv  ==  V233_3W_20260710_201905_stats.csv
V234_3M_20260711_012312_stats.csv  ==  V235_3M_20260711_022726_stats.csv
```

Due versioni consecutive dell'EA (v2.3.2 → v2.3.3, v2.3.4 → v2.3.5) che producono
statistiche **identiche al byte**. O la modifica di versione non toccava nulla di
ciò che quei test misurano, oppure il secondo test non è mai stato eseguito
davvero. Va chiarito prima di usare quei due confronti come evidenza di un
miglioramento.

---

## 5. Il bundle React distribuito è vecchio — e contiene le credenziali 🔴

Non è un duplicato, l'ho trovato scansionando. **È il problema più urgente di
tutto questo elenco.**

| | |
|---|---|
| Ultimo commit su `frontend/src` | `1b67a97` (correzioni di sicurezza) |
| Ultimo commit su `server/static/app/` | `4d6e2ce` (una fix MQL5, **precedente**) |

`server/static/app/` è il bundle che il backend serve davvero sotto `/app`. È stato
costruito **prima** delle correzioni al frontend, quindi non le contiene. Verificato
direttamente sul bundle distribuito:

```
grep -o "admin@nexus.local / nexus123" server/static/app/static/js/main.*.js
→ admin@nexus.local / nexus123          ← le credenziali di default sono ANCORA lì
grep -c "X-Nexus-Csrf" server/static/app/static/js/*.js
→ 0                                      ← nessuna protezione CSRF
```

Il sorgente è corretto. **Il file servito agli utenti no.** Finché non si
ricostruisce il bundle, la schermata di login continua a mostrare utente e password
di default a chiunque apra la pagina, e le mutazioni dalla dashboard non inviano il
token anti-CSRF.

> È il finding `AUD0-DOC-006`: copiare a mano `frontend/build/` dentro
> `server/static/app/` non è una pipeline di rilascio. La conseguenza non era
> teorica.

**Azione (prioritaria):** vedi [[TODO - Agente Desktop (consegna remediation)]], punto 1.

---

## Cosa NON è duplicato

Per chiarezza, perché l'assenza è un risultato:

- **nessun duplicato nel codice sorgente** — né in `MQL5/`, né in `server/*.py`,
  né in `frontend/src/`, né in `contracts/`. Nessun modulo copiato, nessuna
  versione "_old" o "_backup" rimasta in giro;
- gli otto `README.md` con lo stesso nome sono in cartelle diverse e hanno
  contenuti diversi: è la convenzione, non una duplicazione;
- i tre `index.html` sono sorgente React, bundle distribuito e dashboard statica
  di fallback: tre ruoli distinti.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Remediation Audit v18]] ·
[[TODO - Agente Desktop (consegna remediation)]] · [[NEXUS EA - Principi]]
