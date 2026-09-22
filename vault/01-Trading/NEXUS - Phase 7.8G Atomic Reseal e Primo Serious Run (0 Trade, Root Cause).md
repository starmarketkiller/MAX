# NEXUS - Phase 7.8G Atomic Reseal + Primo Serious Run (0 trade, root cause)

**Baseline:** `3528f495c86af1f1ba140073a13cbad31f84b481` (Phase 7.8F, `EXECUTION_CONFIG_VERIFIED_READY_FOR_RUN`). L'utente ha identificato che l'hash dell'intero `history/GOLD/2026.hcc` non è window-aware (contiene barre ben oltre `PRIMARY_FRESH_VERDICT_WINDOW`, che crescono ogni giorno indipendentemente dal periodo testato) e ha chiesto un reseal window-aware seguito, se verificato, dall'esecuzione immediata del Serious validation.

---

## Parte 1 — Atomic Reseal (window-aware)

**Re-valutazione del drift**: `history/GOLD/2026.hcc` era cambiato di nuovo rispetto al seal 7.8E. Verificato con un audit dedicato (`NXS_VolBrkWindowAwareAudit.mq5`, script read-only): la barra più recente nel file è **2026.09.22 00:00:00** (essenzialmente "oggi"), ben oltre il confine FRESH (2026-03-01) — il file cresce in coda verso il presente, non nel mezzo. 244 barre H4 dentro FRESH (gennaio-febbraio 2026, un range storico concluso), 869 barre fuori FRESH (marzo-oggi, un range che cresce per costruzione). **Conclusione: `IRRELEVANT_POST_WINDOW_CACHE_DRIFT`** (alta confidenza, evidenza diretta — nessun confronto byte-per-byte retroattivo possibile per gennaio-febbraio, dichiarato onestamente come limite).

**Nuovo fingerprint window-aware**: 27 file `.tkc` mensili (ricalcolati ora) + uno **snapshot deterministico delle barre H4** nell'esatto superset che il Tester carica (`FromDate=2023.12.20` → `ToDate=2026.03.01`, 3.379 barre, OHLCV+spread+real_volume, esportate via `CopyRates`) — il dato più direttamente collegato a ciò che Model=4 userà davvero. Questo **sostituisce** l'hash dell'intero `.hcc` come gate.

**Timezone rimisurato immediatamente prima del run**: 10.800s (identico a 7.8E, nessuna discrepanza).

**Verdetto: `ATOMIC_RESEAL_VERIFIED`** — confermato da un verificatore indipendente che ricalcola tutto dai file reali su disco.

## Parte 2 — Primo Serious Run reale: 0 trade, root cause identificata

Eseguito il tester config congelato in 7.8F (`Expert=NEXUS_EA_v2`, `Symbol=GOLD`, `Period=H4`, `Model=4`, `FromDate=2023.12.20`, `ToDate=2026.03.01`, `Deposit=10000`, `Leverage=500`, `InpStrategySelector=56`). Durata reale: **~2h01m** (01:52:42 → 03:53). Raccolti e hashati gli output RAW **prima** di qualunque interpretazione (`immutable_run_manifest_v1.json`).

**Scoperta**: il report ufficiale MT5 riporta **"Numero di Operazioni di Trading Totali: 0"**, con **"Qualità dello Storico: 100% ticks reali"** — quindi non è un problema di dati/copertura.

**Root cause identificata e verificata indipendentemente**: `InpStrat_VolBreakoutConfirmed` (`NXS_Inputs.mqh:544`) è un **secondo master-switch per-strategia**, default `false` ("17/09 - Strategy Foundry Phase 3, mai verificata su MT5 - default OFF"), mai incluso in NESSUN tester config congelato attraverso le fasi 7.8B→7.8G. Il segnale `NXS_Strat_VolatilityBreakoutConfirmed()` ritorna `DIR_NONE` immediatamente se questo flag è false, **prima** di valutare qualunque condizione di prezzo — indipendentemente da `InpStrategySelector=56` (che era già corretto). Il pattern `InpStrat_<Nome>` è consolidato ed esiste per ogni strategia dell'EA — non un caso isolato.

**Perché questo NON è un risultato scientifico valido**: 0 trade non significa "nessun breakout in ~3 anni di GOLD H4" (implausibile, contraddetto dal fast-structural test precedente) — significa che il segnale non è mai stato valutato. Dichiarare `INSUFFICIENT_SAMPLE` o qualunque altro verdetto su questo run sarebbe fuorviante.

**Perché questo NON è un rescue**: nessun parametro di strategia, soglia di verdetto, o filtro è stato toccato — è un prerequisito di abilitazione mai discusso in nessuna fase precedente, per puro oversight. Analogo diretto al bug `Expert=Experts\NEXUS_EA_v2` già scoperto e corretto in 7.8F.

**Nessun verdetto preregistrato calcolato su questo run** (sarebbe scientificamente vuoto).

## Deliverables

`NXS_VolBrkWindowAwareAudit.mq5`, `build_atomic_reseal.py`, `verify_atomic_reseal.py`, `volatility_breakout_atomic_prerun_reseal_v1.json`, `collect_immutable_run_manifest.py`, `immutable_run_manifest_v1.json` (+ report/journal/ini raw reali), `build_zero_trade_root_cause.py`, `verify_zero_trade_root_cause.py`, `volatility_breakout_zero_trade_root_cause_v1.json`, `test_phase_7_8g.py`.

## Regressione

21/21 PASS sulla nuova suite dedicata. 31/32 delle altre suite Phase 7 passano; 1 fallisce per il motivo già noto e ora strutturalmente superato (7.8E, whole-file hash legacy — il vero gate window-aware di 7.8G resta valido).

## Fix proposto per il secondo run (non ancora eseguito)

Aggiungere **un solo campo** al tester config: `InpStrat_VolBreakoutConfirmed=true` in `[TesterInputs]`. Nessun altro valore cambia (Expert/Symbol/Period/Model/FromDate/ToDate/Deposit/Currency/Leverage/InpStrategySelector/InpProfileTF/InpUseStrategyProfiles/InpResearchUse* invariati). Costo stimato: ~2 ore reali (stesso ordine di grandezza del run appena completato).

**Ci si ferma qui, prima di lanciare un secondo run**, per lo stesso principio che governa l'intero protocollo: nessuna modifica alla configurazione dopo aver visto un esito senza dichiararla esplicitamente e attendere conferma — anche quando, come qui, la correzione è innocua rispetto alla logica della strategia.

---

**SERIOUS_VALIDATION_RESULT: NOT_YET_PRODUCED (0 trade per misconfigurazione tecnica, non un esito di mercato).**

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: in corso
VERSO DEMO: ~68%
7.8G:
ATOMIC_RESEAL_VERIFIED ✓
PRIMO RUN REALE: 0 trade (root cause: InpStrat_VolBreakoutConfirmed
mancante nel tester config, mai incluso in 7.8B-7.8F)
PROSSIMO:
conferma esplicita per il secondo run con il fix a un solo campo
```
