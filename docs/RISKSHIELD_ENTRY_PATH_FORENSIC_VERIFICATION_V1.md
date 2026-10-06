# RiskShield Entry Path — Forensic Verification V1

**Stato:** verifica forense completa, non committata. Nessuna correzione applicata, nessuna modifica a runtime/risk/execution. Ogni affermazione sotto è CODE_VERIFIED con citazione file:riga — nessuna inferita dal commento di un altro documento.

**Riferimento di partenza:** `docs/architecture/07_RISK_AND_PROTECTION_PIPELINE.md` (commit `289cdcf6`, 2026-07-20): *"`NXS_RS_BlockEntry()` was not observed in the reconstructed normal entry call graph."*

---

## Verdetto

## **WIRED_CORRECTLY**

Con una precisazione temporale importante: il gate **non era wired** quando quel documento è stato scritto (20 luglio), ma **è stato cablato correttamente il 12 settembre 2026** (commit `c9a8ebc`, *"Decision/Gate/Execution Trace v1"*) — **quasi due mesi prima di questa verifica**, non come conseguenza di questo audit. Il documento di architettura di luglio è **stale**, non falso per il periodo che descriveva.

---

## 1. Call graph ricostruito (tutti i path di entry enumerati)

### Il punto di convergenza: `NXS_CommonExposurePreflight()`

`MQL5/Include/NEXUS_v1/NXS_Execution.mqh:63-213` — dichiarata esplicitamente nel codice come *"Invariante unica di creazione esposizione"* (righe 44-56), costruita per chiudere un problema **già trovato e corretto in un audit precedente** (citato nel codice: `AUD0-ADD-001/002/003`, `AUD0-INST-001/002`) — quel problema era esattamente *"esistevano tre pipeline distinte con sottoinsiemi DIVERSI di controlli: entry primaria, grid/pyramid, istituzionale"*. La correzione sposta tutti i gate non aggirabili in questa unica funzione, chiamata da ogni path.

**Gate interni, in ordine, righe 63-213:** (1) licenza, (2) ruin freeze, (3) protezioni giornaliere, (4) stop obbligatorio, (4a) incertezza di stato (ledger/snapshot/indicatori), (4b) durabilità Virtual SL, **(5) RiskShield — riga 152: `bool rsBlocked = NXS_RS_BlockEntry(g_sym, stratName, rsReason);`**, (6) cap esposizione direzionale, (7) margine proiettato, (8) preflight broker.

### Path 1 — Strategie legacy (incl. NXR)

```
Strategia (NXS_Strat_*) produce SNXSSignal
  → NEXUS_EA_v2.mq5:1643  NXS_TryExecuteRC(sig, ...)
  → NXS_Execution.mqh:825  NXS_OpenTrade(sig, ...)
  → NXS_Execution.mqh:548  NXS_CommonExposurePreflight("PRIMARY:"+stratName, ...)
  → NXS_Execution.mqh:152  NXS_RS_BlockEntry()  ✅ GATE ATTRAVERSATO
```

**Il motore NXR condivide lo stesso punto di ingresso**, non un path parallelo: `NXS_ReusePerformancePack.mqh:1942` chiama **lo stesso** `NXS_TryExecuteRC(sig, amd, sw, htf, vel, ...)` — confermato per lettura diretta. OB_MIT, FVG_MIT, il ramo NXR di MALAYSIAN_SNR passano quindi per lo stesso gate del Path 1, non per uno scavalcato.

### Path 2 — Modello Istituzionale (apertura di gruppo)

```
NXS_Institutional_Decide() produce SNXSDecision
  → NEXUS_EA_v2.mq5:1476  NXS_OpenTrade(isig, InpMagic + MAGIC_CORE, 1.0)
  → NXS_Execution.mqh:548  NXS_CommonExposurePreflight(...)
  → NXS_Execution.mqh:152  NXS_RS_BlockEntry()  ✅ GATE ATTRAVERSATO
```

Verificato leggendo `NEXUS_EA_v2.mq5:1448-1486`: l'apertura di gruppo chiama **la stessa** `NXS_OpenTrade()` del Path 1, non una funzione di apertura dedicata.

### Path 3 — Grid / Recovery

```
NXS_GridRecovery.mqh (logica di grid)
  → NXS_GridRecovery.mqh:86  NXS_CommonExposurePreflight("GRID", "GRID", ...)
  → NXS_Execution.mqh:152    NXS_RS_BlockEntry()  ✅ GATE ATTRAVERSATO
```

### Path 4 — Pyramiding (scale-in)

```
NXS_Pyramiding.mqh (logica di piramide)
  → NXS_Pyramiding.mqh:166  NXS_CommonExposurePreflight("PYRAMID", "PYRAMID", ...)
  → NXS_Execution.mqh:152   NXS_RS_BlockEntry()  ✅ GATE ATTRAVERSATO
```

### Path 5 — Institutional Management (add-on su posizione di gruppo esistente)

```
NXS_InstManage.mqh (gestione add/scale del gruppo istituzionale)
  → NXS_InstManage.mqh:195  NXS_CommonExposurePreflight("INST:"+tag, "INST:"+tag, ...)
  → NXS_Execution.mqh:152   NXS_RS_BlockEntry()  ✅ GATE ATTRAVERSATO
```

### Path 6 — Profit Reclaim (SAR re-entry)

```
NXS_ProfitReclaim.mqh (re-entry dopo profit reclaim)
  → NXS_ProfitReclaim.mqh:107  NXS_CommonExposurePreflight("PROFITRECLAIM", "SAR", ...)
  → NXS_Execution.mqh:152      NXS_RS_BlockEntry()  ✅ GATE ATTRAVERSATO
```

### Path 7 — SL Reclaim

```
NXS_SLReclaim.mqh (re-apertura dopo reclaim SL)
  → NXS_SLReclaim.mqh:214  NXS_CommonExposurePreflight("SLRECLAIM", strategy, ...)
  → NXS_Execution.mqh:152  NXS_RS_BlockEntry()  ✅ GATE ATTRAVERSATO
```

**Nota di provenance:** `FVG_CONT` ha un defect noto `SLRECLAIM_ACCOUNT_PROTECTION_BYPASS` con `remediation_state=UNKNOWN_REMEDIATION` nel registry (`contracts/edge-validation-registry.json`, da `docs/TRADING_EDGE_STATUS_RECONCILIATION_V1.md`). Questa verifica riguarda il gate RiskShield, **non** risolve quel defect separato — il meccanismo SLReclaim passa oggi per `NXS_CommonExposurePreflight` (riga 214), ma se quel defect descrive un bypass delle protezioni in una versione di codice diversa o in un ramo non coperto da questa lettura, resta un gap **diverso e non chiuso da questa verifica**. Segnalato come limite esplicito, non risolto qui.

### Path 8 — Pending orders

**Non esiste.** Grep su `TRADE_ACTION_PENDING`/`ORDER_TYPE_*_LIMIT`/`ORDER_TYPE_*_STOP` su tutto `MQL5/`: **zero risultati**. NEXUS invia solo ordini di mercato (`TRADE_ACTION_DEAL`). Non è un gap, è un path inesistente per costruzione del sistema.

## 2. Primitive di invio ordine — nessun bypass trovato

Unica funzione che crea NUOVA esposizione: `NXS_DoBuy`/`NXS_DoSell` (`NXS_Globals.mqh:348,367`) — entrambe raggiunte **solo** dall'interno di `NXS_OpenTrade()`, mai chiamate direttamente da nessuna strategia o add-on (verificato: tutti i chiamanti passano per `NXS_CommonExposurePreflight` prima). Altre chiamate `OrderSend` trovate nel codebase (`NXS_DoClose`, `NXS_DoClosePartial`, `NXS_DoModify`, `NXS_Prot_ClosePositionWithReason`) sono tutte `TRADE_ACTION_DEAL` di **chiusura** (posizione opposta su ticket esistente) o `TRADE_ACTION_SLTP` — riducono o modificano esposizione esistente, non ne creano di nuova. Correttamente **non** gated da RiskShield (un gate anti-nuova-esposizione non ha senso su una chiusura).

## 3. RiskShield stesso: alimentato o inerte?

Verificato che i 3 sotto-meccanismi del master gate sono davvero attivi, non solo dichiarati:

- **Equity Breaker**: `NXS_RS_Breaker_Update()` chiamato da `NEXUS_EA_v2.mq5:1131` (dentro `OnTick`, prima della valutazione segnali). Il codice stesso documenta (righe 215-219 di `NXS_RiskShield.mqh`) un **secondo defect già trovato e corretto**: *"il breaker non era MAI alimentato... una protezione documentata e completamente inerte"* — bug diverso dal wiring di `NXS_RS_BlockEntry`, già risolto nello stesso file.
- **Spread Burst**: `NXS_RS_SpreadSample()` chiamato da `NEXUS_EA_v2.mq5:1145` (stesso punto in `OnTick`).
- **Correlation Cluster**: calcolato on-demand dentro `NXS_RS_Cluster_Block()`, chiamato da `NXS_RS_BlockEntry()` stesso — nessuna dipendenza da stato pre-popolato.

Tutti e 3 risultano alimentati, non inerti.

## 4. Protezioni equivalenti già presenti — non confondere con RiskShield

- `NXS_Prot_EntryBlocked()` — protezioni giornaliere/pausa, gate (3) di `NXS_CommonExposurePreflight`, **diverso** da RiskShield.
- `NXS_RuinFrozen()` — kill switch di conto per risk-of-ruin, gate (2), **diverso** da RiskShield.
- Nessuno dei due sostituisce RiskShield (Spread Burst/Equity Breaker/Correlation Cluster) — sono gate complementari nella stessa invariante, non alternative.

## 5. Distinzione richiesta

- **Protezioni equivalenti già presenti**: nessuna — RiskShield copre fenomeni (burst di spread, Sharpe rolling per-strategia, cluster di correlazione) che nessun altro gate della lista copre.
- **Protezioni parziali**: nessuna trovata in questa verifica.
- **Vera assenza del master gate**: **non riscontrata nello stato attuale del codice** (HEAD `8e5284a`, verificato 2026-10-06). Era vera assenza fino al 2026-09-11, chiusa dal commit `c9a8ebc` del 2026-09-12.

## 6. Test/trace deterministico (statico, non a runtime — nessun trade live apribile da questo ambiente)

Non è stato possibile compilare/eseguire MT5 in questo ambiente (nessun MetaEditor/Strategy Tester disponibile qui) — il test deterministico prodotto è una **traccia statica riproducibile**, non un'esecuzione dinamica. Chiunque (incluso Codex via LocalBridge) può riprodurre esattamente questi risultati con:

```bash
grep -n "NXS_RS_BlockEntry|NXS_RS_Breaker_Update|NXS_RS_SpreadSample" -r MQL5/
grep -n "NXS_CommonExposurePreflight\s*(" -r MQL5/
grep -n "OrderSend\s*(" -r MQL5/Include/NEXUS_v1/ | xargs -I{} echo {}   # poi verificare req.action per ciascuno
grep -n "TRADE_ACTION_PENDING|ORDER_TYPE_.*_LIMIT|ORDER_TYPE_.*_STOP" -r MQL5/
```

Ogni citazione file:riga in questo documento è stata prodotta da questi comandi più lettura diretta del codice circostante — riproducibile esattamente, nessuna inferenza.

**Raccomandazione per un vero test dinamico (non eseguito qui):** uno scenario di Strategy Tester con `InpSpreadBurst_Enable=true`, `InpSpreadBurst_P95Cap` artificialmente basso, e verifica che nessun trade venga aperto durante la finestra di freeze — dimostrerebbe il comportamento a runtime, non solo il call graph statico. Non eseguito in questa fase (richiederebbe MetaEditor/Tester, non disponibili qui, e comunque "nessuna modifica live/risk/execution in questa fase" come richiesto).

## 7. Nessun fix proposto

Il verdetto è `WIRED_CORRECTLY` — non è richiesta alcuna correzione. Punti aperti non chiusi da questa verifica, da tenere distinti:

- Il defect `SLRECLAIM_ACCOUNT_PROTECTION_BYPASS` (FVG_CONT, `UNKNOWN_REMEDIATION`) resta un gap **diverso**, non di questo audit.
- `docs/architecture/07_RISK_AND_PROTECTION_PIPELINE.md` è **stale** — descrive uno stato precedente al fix del 12/09. Andrebbe aggiornato o marcato superseded perché un lettore futuro non lo prenda per lo stato attuale (come quasi è successo in questo stesso filone di lavoro).

---

## Vincoli rispettati

Nessuna modifica a codice/runtime/risk/execution. Nessun trade live aperto o tentato. Nessun fix applicato.

RISKSHIELD_ENTRY_PATH_FORENSIC_VERIFICATION_V1_READY_FOR_DECISION
