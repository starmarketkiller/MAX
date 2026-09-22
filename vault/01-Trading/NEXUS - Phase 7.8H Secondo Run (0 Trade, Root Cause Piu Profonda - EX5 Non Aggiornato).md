# NEXUS - Phase 7.8H Corrected Serious Validation RUN (0 trade, causa più profonda)

**Baseline:** `7cd7910f323bb54cb2fdcc49ef46a50a53184338` (Phase 7.8G). L'utente ha autorizzato esplicitamente il secondo run, con la condizione che il fix `InpStrat_VolBreakoutConfirmed=true` fosse incorporato in un nuovo config hash + atomic reseal window-aware fresco, immediatamente prima del rilancio.

---

## Config corretto + classificazione (prima del run)

Partito **esattamente** dal tester config finale congelato in 7.8F, aggiunto **un solo campo**: `InpStrat_VolBreakoutConfirmed=true`. Nuovo SHA256 calcolato. Classificazione esplicita: `TECHNICAL_ENABLEMENT_FIX` — `changes_strategy_identity/parameters/verdict_rules/data_window = false`. Il run 7.8G resta `TECHNICALLY_INVALID_ZERO_TRADE_RUN`, mai reinterpretato come FAIL/INSUFFICIENT_SAMPLE.

## Atomic reseal fresco (immediatamente prima del run)

Ricostruito da zero (non riusato da 7.8G): audit window-aware fresco (244 barre dentro FRESH, invariate rispetto a 7.8G — nessun drift rilevante), 27 hash tick ricalcolati, snapshot H4 rigenerato (3.379 barre, invariato), timezone rimisurato (10.800s, invariato), identità ambiente completa (EA EX5/source hash, broker/server). **Verdetto: `ATOMIC_RESEAL_VERIFIED`**, confermato indipendentemente (26/26 check).

## Secondo run reale: ancora 0 trade

Eseguito (~1h55m, 08:42→10:37). Raccolti e hashati i raw output **prima** di qualunque interpretazione. Il report ufficiale mostra di nuovo **"Numero di Operazioni di Trading Totali: 0"** (Qualità storico 100% ticks reali).

## Sanity gate (punto 8, applicato prima di qualunque verdetto statistico)

Verificato: master switch `InpStrat_VolBreakoutConfirmed=true` presente nell'ini usato ✓, selector `56` presente ✓. Cercata nel journal la riga `[RESEARCH][INIT] strategy=VOLATILITY_BREAKOUT_CONFIRMED selector=56` (che conferma l'inizializzazione della ricerca per questa strategia) — **assente**. Classificazione: **`TECHNICAL_EXECUTION_FAILURE_STRATEGY_NEVER_INITIALIZED`** — non applicato automaticamente `INSUFFICIENT_SAMPLE`, come richiesto esplicitamente.

## Root cause più profonda: l'EX5 in uso precede la strategia stessa

Investigando la causa esatta: **l'EX5 deployato nel terminale (`NEXUS_EA_v2.ex5`) è datato 2026-09-10**, mentre il **commit che introduce `VOLATILITY_BREAKOUT_CONFIRMED` nel sorgente è `f035d30` del 2026-09-17** — una settimana dopo. Il binario compilato in esecuzione in **entrambi** i run (7.8G e 7.8H) non conteneva né la variabile `InpStrat_VolBreakoutConfirmed`, né la funzione segnale, né l'aggancio del selettore 56 alla logica del breakout attuale — **la strategia semplicemente non esisteva ancora in quel binario**.

**Prova diretta ed empirica**: MT5 stampa automaticamente ogni variabile `input` nell'ordine di dichiarazione del sorgente compilato, all'avvio del Tester. Nel dump reale del secondo run, `InpStrat_BREAKOUT_ACC` e `InpStrat_LONDON_BO` (che circondano `InpStrat_VolBreakoutConfirmed` nel sorgente attuale, righe 543/545) sono presenti; **`InpStrat_VolBreakoutConfirmed` (riga 544) è assente** — un salto di sole 54 caratteri, coerente con un binario compilato prima che questa riga esistesse. Verificato indipendentemente (9/9 check).

**Perché il fix di 7.8H sembrava corretto ma è stato inefficace**: il nome della variabile nel tester config è quello giusto nel sorgente attuale del repo — ma applicato a un binario che non la riconosce affatto. MT5 ignora silenziosamente un nome `.ini` che non corrisponde a nessun `input` del programma compilato in esecuzione, senza errore.

## Nessun verdetto calcolato

Nessuna statistica preregistrata è stata applicata a questo run: sarebbe scientificamente vuoto farlo su uno zero-trade causato da un binario disallineato. Sia il run 1 (7.8G) sia il run 2 (7.8H) restano archiviati, immutati, ciascuno con la propria root cause documentata.

## Deliverables

`build_corrected_config_and_classification.py`, `volatility_breakout_corrected_config_v1.json`, `build_atomic_reseal_before_run2.py`, `verify_atomic_reseal_before_run2.py`, `volatility_breakout_atomic_reseal_before_run2_v1.json`, `collect_immutable_run_manifest.py`, `immutable_run_manifest_run2_v1.json` (+ report/ini raw), `compute_serious_validation_verdict.py` (con sanity gate incorporato), `volatility_breakout_serious_3y_result_v1.json`, `build_run2_deeper_root_cause.py`, `verify_run2_deeper_root_cause.py`, `volatility_breakout_run2_deeper_root_cause_v1.json`, `test_phase_7_8h.py`.

## Regressione

21/21 PASS sulla nuova suite dedicata. 32/33 delle altre suite Phase 7 passano; 1 fallisce per il motivo già noto (7.8E, whole-file hash legacy, non modificato per non "far diventare verde" artificialmente un test superseded).

## Fix proposto per un terzo run (non ancora eseguito)

**Ricompilare `MQL5/Experts/NEXUS_EA_v2.mq5` dal sorgente corrente del repo (HEAD)** con MetaEditor, verificare che il nuovo EX5 sia più recente del commit `f035d30` e che il dump Input del prossimo run includa finalmente `InpStrat_VolBreakoutConfirmed`, **poi** rilanciare un terzo run con lo stesso tester config già corretto in 7.8H (nessun altro campo da cambiare).

**Ci si ferma qui prima di ricompilare**: questa scoperta tocca il *binario* stesso dell'EA, un salto di sostanza tecnica ulteriore rispetto al semplice campo `.ini` già corretto — richiede conferma esplicita, coerentemente con il principio che ha già governato ogni fase precedente.

---

**SERIOUS_VALIDATION_RESULT: NOT_YET_PRODUCED (0 trade per causa tecnica più profonda — EX5 non aggiornato — non un esito di mercato, in nessuno dei due run finora).**

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: in corso
VERSO DEMO: ~68%
7.8H:
RUN 1 (7.8G): 0 trade - master switch OFF (risolto)
RUN 2 (7.8H): 0 trade - EX5 non aggiornato, precede il commit
della strategia di una settimana (nuova causa, mai vista prima)
PROSSIMO:
ricompilare NEXUS_EA_v2.ex5 dal sorgente corrente
→ conferma esplicita richiesta
→ RUN 3
```
