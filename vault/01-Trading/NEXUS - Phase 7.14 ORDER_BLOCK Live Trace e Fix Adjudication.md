# NEXUS - Phase 7.14 — ORDER_BLOCK Live Trace e Fix Adjudication

**Baseline:** `7b823b9` (Phase 7.13). **Prima applicazione di un fix reale al sorgente EA in questo intero progetto** — autorizzata esplicitamente e solo per la riga `if(tf != NXS_Profile_TF("ORDER_BLOCK")) return s;`, dopo dimostrazione causale sul trace EA reale. Nessuna ricerca economica: nessuna optimization, SL/TP tuning, parameter sweep, confronto di redditività, rescue o promozione live.

**Obiettivo**: ottenere la prova dinamica reale del difetto ORDER_BLOCK nel percorso EA → router → stato → segnale e, solo se confermata, applicare il fix minimale già proposto in Phase 7.13, con parity pre/post.

---

## 1. Trace diagnostico reale

Istrumentazione **temporanea, non comportamentale** (solo `FileWrite` prima di ogni `return` già esistente in `NXS_OB_UpdateSide()`/`NXS_Strat_OrderBlock()`, guardata da `#ifdef NXS_OB_DIAG_TRACE`) applicata al sorgente reale, compilata con MetaEditor, eseguita nella Strategy Tester MT5 su **tick reali GOLD, 2023-10-02→2026-08-25** (`InpStrategySelector=15` isola ORDER_BLOCK, `InpProfileMultiTF=true`+`InpUseStrategyProfiles=true` attivano il vero loop multi-TF, `InpResearchMode=true`). Snapshot esatto dell'istrumentazione preservato in `nxs_ob_diag_instrumentation_snapshot.mqh.txt` per riproducibilità; **rimossa dal sorgente canonico subito dopo ogni cattura** (verificato: zero tracce di `NXS_OB_DIAG_TRACE` nel commit finale).

## 2. Riproduzione del difetto

Trace reale (321.655 righe, tutti i passaggi D1/H4/H1/M30/M15/M5): **18.485 mutazioni di stato su passaggi non canonici**, **673 segnali sparati e scartati su TF non canonico** (contro 123 tenuti su D1), **14.732 esempi end-to-end** (mutazione non canonica → evento canonico successivo) trovati direttamente nel trace — il meccanismo ipotizzato in Phase 7.13 è confermato nel percorso EA reale, non solo nella ricostruzione Python. **Scoperta aggiuntiva**: `lastBarTime` è condiviso da tutti i passaggi TF nello stesso `SNXSOBState` — un passaggio veloce lo sovrascrive, disfacendo il gate "nuova barra" di D1 stesso: **19 giorni D1 mostrano fino a 17 fire nello stesso giorno solare** pre-fix (0 post-fix) — una manifestazione più severa di quanto descritto in Phase 7.13.

## 3. Baseline pre-fix

Congelata in `baseline_pre_fix_v1.json`: 123 segnali D1 tenuti, 673 scartati su TF non canonico, zone create (BUY 6638/SELL 6556), invalidate (4439/4672), scadute (1881/1405), consumate da retest (317/479). Nessun PF/WR usato. Riproducibile via `nxs_orderblock_realtrace_prefix.ini` + istrumentazione snapshot.

## 4. OB_MIT

Verifica statica (non assunta dal nome né da Phase 7.13): `NXS_Strat_OB_Mitigation_Structural()` non ha stato proprio, chiama **direttamente** `NXS_Strat_OrderBlock()` e ne copia il risultato (solo `stratName`/`reason`/floor score diversi) → **correggere `NXS_Strat_OrderBlock()` risolve automaticamente OB_MIT**, nessuna patch separata. **Finding correlato** (non richiesto, non corretto qui): la chiamata a OB_MIT nel collector è gated dal selettore 20, ma `NXS_Strat_OrderBlock()` al suo interno ha il proprio gate sul selettore 15 — isolare OB_MIT da solo (`InpStrategySelector=20`) lo rende strutturalmente muto; in produzione (`selettore=0`) non ha effetto.

## 5. Fix minimale applicato

`MQL5/Include/NEXUS_v1/NXS_Strategies.mqh`, `NXS_Strat_OrderBlock()`: `if(tf != NXS_Profile_TF("ORDER_BLOCK")) return s;` subito dopo `tf = NXS_EffTF();`, prima di ogni lettura di `g_atr`/`g_obBuy`/`g_obSell` — stessa forma già applicata a BREAKOUT_ACC. Nessun'altra riga toccata (verificato: geometria zona, soglie, gate HTF/SMC, SL/TP, cooldown, altre strategie invariati — `git diff` mostra solo questa funzione modificata in `MQL5/`).

## 6. Parity post-fix

Compilato e rieseguito lo stesso .ini (`nxs_orderblock_realtrace_postfix.ini`) con la stessa istrumentazione sopra il fix:

| | A (pre-fix) | B (post-fix) | C (ricostruzione Python 7.13) |
|---|---|---|---|
| Segnali D1 tenuti (raw) | 123 | **8** | 7 |
| Righe su TF non canonico | 18.485+ mutazioni | **0** | n/d |
| Giorni D1 con fire multipli | 19 (max 17x) | **0** | n/d |

**Guardia efficace al 100%**: post-fix, il trace mostra **esclusivamente** righe `PERIOD_D1` (53658/53658). A vs B (stessi tick reali, confronto a multiset): 4 eventi coincidono esattamente, 119 solo in A (soppressi dal fix — contaminazione), 4 solo in B (segnali D1 genuini che riemergono dopo il fix) — **questo confronto A/B, sugli stessi tick reali, resta pienamente valido e non è toccato da alcuna correzione**. B vs C: 8 vs 7 — vicini in conteggio, ma **corretto in Phase 7.15** (vedi nota di revisione sotto): la vicinanza numerica NON era sostenuta da una ricostruzione causale.

> **Nota di revisione (Phase 7.15)**: l'affermazione originale qui ("residuo spiegato dalla diversità delle fonti, non forzato a coincidere") è stata verificata più a fondo in Phase 7.15 e **corretta**: solo 1 degli 8 eventi B e 7 eventi C condivide la stessa data+direzione — gli altri cadono su date completamente diverse. Un confronto diretto delle barre D1 sulle date contestate fra due fonti indipendenti mostra barre numericamente **identiche**, escludendo "quel giorno ha un prezzo diverso" come spiegazione. Classificazione corretta: `CANDIDATE_CAUSE_NOT_ISOLATED` (probabile path-dependence della state machine su un punto a monte mai isolato), non più "residuo spiegato". Vedi `phase7_15/ea_python_comparison_classification_v1.json` e il vault report di Phase 7.15 per il dettaglio. **Questa correzione riguarda solo il confronto strutturale B/C (fonti diverse) — non tocca la validazione del fix, stabilita dal confronto A/B sugli stessi tick reali.**

## 7. Migrazione dell'evidenza storica

`historical_evidence_migration_v1.json`: **ORDER_BLOCK_IMPL_V1_CONTAMINATED** (senza guardia, attiva fino a `7b823b9`) marcata storica — nessun artifact cancellato (`results/phase2_baseline_20260705_v2.0.27.csv`, `results/phase_partB_silent_diagnostic_20260706.csv`, il trace pre-fix di questa fase restano preservati, non riusati come evidenza della nuova implementazione). **ORDER_BLOCK_IMPL_V2_TF_GUARDED** (con guardia, da questo commit) è la nuova identità canonica — nessuna evidenza precedente le si applica. Il motore Python (`backtest.py`) resta separato: `UNAFFECTED_BY_THIS_BUG_NOT_SEMANTIC_PARITY_PROVEN` — non affetto dal difetto per costruzione, ma questo NON dimostra parità semantica con V2.

## 8. Decisione finale

`decision_card_v2_order_block_v1.json`: **`FIX_CAUSALLY_VALIDATED`**. **OB_MIT**: fix si propaga automaticamente (nessuna patch separata necessaria né possibile).

## Deliverables

`nxs_ob_diag_instrumentation_snapshot.mqh.txt`, `baseline_pre_fix_v1.json`, `ob_mit_dependency_map_v1.json`, `real_trace_comparison_v1.json`, `parity_comparison_v1.json`, `historical_evidence_migration_v1.json`, `decision_card_v2_order_block_v1.json`, 6 builder, verificatore indipendente (VERIFY OK), 22 test propri (22/22 PASS), tracce curate committate (eventi di cambio stato: 26.387 righe pre-fix, 51 post-fix — le tracce raw complete, 39MB/6MB, restano locali per dimensione, rigenerabili via gli .ini + lo snapshot dell'istrumentazione), questo vault report.

## Vincoli preservati

Nessuna optimization, tuning SL/TP, parameter sweep, confronto di redditività, rescue o promozione live. Nessun artifact cancellato. Nessuna modifica a geometria zona/trigger/gate/cooldown/altre strategie — solo la guardia TF autorizzata. Istrumentazione diagnostica temporanea rimossa dal sorgente canonico prima del commit finale (verificato).

## Regressione

Suite propria: **22/22 PASS**. Suite Phase 7 completa: **447 passed, 18 failed** — **tutti e 18 i fallimenti sono attribuibili a un'unica causa attesa**: i verificatori indipendenti di fasi storiche (7.9e, 7.9f, 7.9h, 7.9i, 7.9j, 7.9k, 7.12, 7.13) controllano `git diff HEAD -- MQL5/` == vuoto, condizione vera per tutta la storia del progetto fino ad ora — smentita per la prima volta da questo commit, che modifica legittimamente `NXS_Strategies.mqh` con autorizzazione esplicita. Nessun fallimento è dovuto a una regressione di logica; nessun file storico di test è stato modificato per "nascondere" questo effetto — resta una nota metodologica aperta (i controlli "MQL5 congelato" delle fasi passate andrebbero ancorati a un commit di baseline invece che a HEAD, se in futuro si vorranno mantenere verdi dopo un fix reale).

---

```
7.13: DIAGNOSI CAUSALE COMPLETATA (Python)
7.14: TRACE REALE + FIX ADJUDICATION COMPLETATA
  trace EA reale: meccanismo CONFERMATO end-to-end (18485 mutazioni
    non canoniche, 14732 esempi end-to-end)
  scoperta extra: gate temporale D1 stesso rotto da TF piu' veloci
    (fino a 17 fire/giorno pre-fix, 0 post-fix)
  FIX APPLICATO (autorizzato, minimale, 1 riga): guardia TF-scoped
  PARITY: 123 -> 8 segnali D1 (stessi tick reali) - guardia efficace
    al 100% (zero mutazioni non canoniche post-fix)
  OB_MIT: fix si propaga automaticamente, nessuna patch separata
DECISIONE: FIX_CAUSALLY_VALIDATED
SECONDO CASO COMPLETO dopo BREAKOUT_ACC: difetto -> prova causale ->
  trace reale -> fix minimale -> parity post-fix
PROSSIMO: nessuna promozione live, nessuna valutazione di
  redditivita' in questa fase - decisione separata e futura
```
