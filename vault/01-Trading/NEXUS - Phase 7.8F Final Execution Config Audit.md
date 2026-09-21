# NEXUS - Phase 7.8F Final Execution Config Audit

**Baseline:** `9b75ceeee1e49ef1e3efd2e5127bdc5bc50e7f1a` (Phase 7.8E, `FINAL_PRE_RUN_SEAL_VERIFIED_READY_TO_EXECUTE`). L'utente ha ispezionato l'`.ini` congelato e trovato due dettagli tecnici concreti prima di autorizzare il RUN: `Leverage=100` contro un protocollo che ricordava a 1:500, e `FromDate`/`ToDate` a granularità giorno contro un confine frozen con un'ora precisa (`12:06:50`).

**Conferma esplicita: SERIOUS_VALIDATION_NOT_EXECUTED. NO STRATEGY OUTCOME ACCESSED.**

---

## Punto 1 — Leverage: verificata la fonte canonica, non assunta

Cercato in tutto il progetto ogni riferimento a `Leverage=`. Trovate due fonti in apparente conflitto:

- **10-09** (`STRUCT_LEVEL_SWEEP...md`, sezione "Verifica leva 1:500"): istruzione esplicita dell'utente di standardizzare a **Leverage=500**. I 4 file RAW ufficiali con `Leverage=100` sono segnalati **esplicitamente come errore** ("NON 1:500"). I template `.ini` per "qualunque futuro rilancio" sono stati aggiornati a 500.
- **17-09** (`sar_dukascopy_independent_validation.md`, SAR Serious 3Y — il precedente da cui 7.8B/C/D/E hanno ereditato la convenzione): `Leverage 1:100 "matches sar_serious_3y.ini/volbrk_fs_6mo.ini conventions"` — un valore ereditato da un artefatto probabilmente creato **prima** del 10-09, mai riallineato alla direttiva esplicita.

La direttiva del 10-09 è la fonte più autorevole e più recente sulla convenzione di leva per i test ufficiali — il valore 100 nel config attuale è un retaggio non riallineato, non una scelta deliberata.

**Verificato nel codice** (non assunto): `NXS_ResearchMode.mqh` → `NXS_ResearchLot()` ritorna `InpResearchFixedLot` (0.01, fisso), indipendente da margine/leva. Margine per 0.01 lotto GOLD: ~$40 a 1:100, ~$8 a 1:500 — trascurabile in entrambi i casi rispetto al deposito 10000 USD. L'esito sarebbe verificabilmente identico con 100 o 500 (coerente con `BUG-024`, aperto, "impatto nullo su sweep isolati"). Ma la scelta segue comunque la fonte canonica più autorevole, non la comodità di "combaciare" col precedente.

**Corretto nel futuro tester config: `Leverage=500`.**

## Scoperta collaterale critica — bug nel formato `Expert=`

Mentre si eseguivano i probe empirici per il punto 2 (sotto), il **primo tentativo di lancio è fallito**: `Expert=Experts\NXS_VolBrkTesterWindowProbe` (stesso formato usato nel tester config congelato in 7.8E, `Expert=Experts\NEXUS_EA_v2`) ha prodotto nel log reale del terminale:

```
Tester   Experts\Experts\NXS_VolBrkTesterWindowProbe.ex5 not found
Terminal tester didn't start
Terminal shutdown with -1000012355 (tester EX5 not found)
```

Il campo `Expert=` nella sezione `[Tester]` vuole **solo il nome**, senza il prefisso di cartella (MT5 lo aggiunge da sé) — verificato correggendo a `Expert=NXS_VolBrkTesterWindowProbe`, che ha prodotto `automatic testing started` e ha completato normalmente. **Il tester config congelato in 7.8E, così com'era, avrebbe fatto fallire l'avvio del futuro Serious validation con lo stesso identico errore.** Corretto: `Expert=NEXUS_EA_v2`.

## Punto 2 — Semantica esatta FromDate/ToDate (misurata, non assunta)

Scritto un Expert Advisor probe (`NXS_VolBrkTesterWindowProbe.mq5`, nessun trading, nessun include NEXUS_v1) che registra il primo/ultimo tick e barra H4 realmente visti dal Tester. Due run reali nel vero Strategy Tester:

- **Probe A** (`FromDate=2023.12.20, ToDate=2023.12.25`): `first_bar_time=2023.12.20 00:00:00` → **FromDate è INCLUSIVO da mezzanotte**.
- **Probe B** (`FromDate=2024.01.08, ToDate=2024.01.10` — lunedì/mercoledì, giorni feriali puri per isolare la regola dal weekend): `last_bar_time=2024.01.09 20:00:00`, `last_tick_time=2024.01.09 23:58:56` → **ToDate è ESCLUSIVO**, il Tester si ferma esattamente a 00:00:00 del giorno `ToDate`.

**Applicato ai confini frozen** (non ricalcolati, solo ricontrollati):

| Confine | Valore frozen | Coincide con la semantica misurata? | Regola |
|---|---|---|---|
| FINE (`2026-03-01 00:00:00`) | `ToDate=2026.03.01` | **Sì, esattamente** | `EXACT_TESTER_WINDOW` — nessuna azione |
| INIZIO (`2023-12-20 12:06:50`) | `FromDate=2023.12.20` | No — il Tester coprirebbe l'intera giornata da 00:00, ~12h06m prima del confine dichiarato | `RUN_SUPERSET_AND_FILTER_EXACT_WINDOW` |

**Regola congelata ORA, prima di vedere qualunque risultato**: il futuro Serious validation girerà con `FromDate=2023.12.20` (il Tester non accetta un'ora specifica), ma il verdetto primario **dovrà escludere/classificare separatamente ogni trade con apertura < 2023-12-20 12:06:50**.

**Osservazione collaterale sui dati (non un cambio di confine):** il probe A mostra tick reali GOLD già disponibili dalle 01:00:00 del 20 dicembre 2023 — un'ora prima delle 12:06:50 rilevate nell'audit di 7.8D. Coerente con la volatilità dei dati già documentata in 7.8E (`reverification_required_before_run`) — non usato per modificare il confine frozen in questa fase, solo annotato.

## Punto 3 — Nessuna dipendenza temporale nascosta (verificato nel codice, non assunto)

- **Segnale** (`NXS_Strat_VolatilityBreakoutConfirmed`, `NXS_Strategies.mqh`): usa solo `iHigh`/`iLow`/`iClose`/ATR su barre H4 — nessuna chiamata a `TimeCurrent`/`TimeGMT`/`InpServerGMTOffset`/sessione.
- **Esecuzione**: esiste un sistema legacy di soglie per sessione (`InpUseSessions=true` di default, dipendente da `InpServerGMTOffset`) che con lo score fisso di VOLBRK (65.0) bloccherebbe il segnale in sessione AFTERNY (20-24 GMT, soglia 70). **Ma verificato nel codice reale** (`NEXUS_EA_v2.mq5`, percorso "PROFILI PER-STRATEGIA", commento esplicito del 10/09) che questo gate è **morto, mai raggiunto** quando `InpUseStrategyProfiles=true` (default, "sempre vero in Research Mode") — il percorso realmente eseguito chiama `NXS_OpenTrade()` direttamente, saltando il gate di sessione.

**Conclusione: `NO_TIMEZONE_DEPENDENT_SIGNAL_LOGIC` — confermato**, sia per il segnale sia per il percorso di esecuzione realmente attivo. Per non dipendere da un default silenzioso, `InpUseStrategyProfiles=true` è ora congelato **esplicitamente** nel tester config finale (prima era implicito).

## Tester config finale (congelato, mai lanciato)

Cambiamenti vs 7.8E: `Expert=Experts\NEXUS_EA_v2` → `Expert=NEXUS_EA_v2` (bug corretto); `Leverage=100` → `Leverage=500` (fonte canonica); `InpUseStrategyProfiles=true` aggiunto esplicitamente. Date/selector/simbolo invariati. Nuovo SHA256 calcolato.

## Osservazione ulteriore, scoperta rieseguendo la regressione

Rieseguendo la suite Phase 7 dopo i probe di questa fase, **il verificatore indipendente di 7.8E ora fallisce**: `history/GOLD/2026.hcc` è cambiato di nuovo (15.651.363 → 15.827.739 byte) rispetto al manifest sigillato in 7.8E — il `mtime` del file coincide con l'orario dell'ultimo probe Tester lanciato qui, causa più probabile. **Nessuna modifica ai dati o al manifest 7.8E in questa fase** (vietato dal punto 5 dell'istruzione). Questo è esattamente lo scenario per cui `reverification_required_before_run` esisteva: la riverifica immediatamente-prima-del-RUN troverà quasi certamente questo stesso mismatch e bloccherà — **servirà un breve RESEAL del manifest dati (non un nuovo Data Freeze completo) subito prima di lanciare il Serious validation**, non dopo. Riguarda il gate-dati (7.8E), non i due punti di execution-config richiesti qui.

## Final verdict

**`EXECUTION_CONFIG_VERIFIED_READY_FOR_RUN`** (per l'ambito di questa fase: leverage, path Expert, semantica timestamp, nessuna dipendenza temporale nascosta).

**Attenzione prima di autorizzare il RUN:** il gate-dati indipendente (7.8E) risulta *ora* bloccato per il motivo sopra — un reseal del manifest a 31 file va rieseguito subito prima del lancio reale.

## Regressione

58/58 PASS sulla nuova suite dedicata. 29/30 delle altre suite Phase 7 passano; **1 fallisce correttamente e per il motivo atteso** (`test_volatility_breakout_final_data_freeze.py`, il fail-closed data-drift gate di 7.8E — non un bug di codice, la conferma pratica che il gate funziona).

## Deliverables

`NXS_VolBrkTesterWindowProbe.mq5`, `build_volatility_breakout_execution_config_audit.py`, `verify_volatility_breakout_execution_config_audit.py`, `test_volatility_breakout_execution_config_audit.py`, `volatility_breakout_execution_config_audit_v1.json`, `raw_probes/` (output reali dei due probe + estratto di log del bug Expert=).

---

**SERIOUS_VALIDATION_NOT_EXECUTED. NO STRATEGY OUTCOME ACCESSED.**

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: 100%
VERSO DEMO: ~68%
██████▊░░░
7.8F:
EXECUTION_CONFIG_VERIFIED_READY_FOR_RUN ✓
(leverage 500 corretto, bug Expert= trovato e corretto,
 timestamp semantics misurate, nessuna dipendenza temporale nascosta)
ATTENZIONE:
reseal manifest dati richiesto subito prima del RUN
(2026.hcc cambiato di nuovo - gate fail-closed confermato in pratica)
PROSSIMO:
reverify data hashes -> execute -> raccogliere risultato immutabile
```
