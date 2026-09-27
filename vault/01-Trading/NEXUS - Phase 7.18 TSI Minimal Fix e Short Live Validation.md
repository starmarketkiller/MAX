# NEXUS - Phase 7.18 — TSI Minimal Fix + Short Live Validation

**Baseline:** `8590f63` (Phase 7.17, `DEFECT_CONFIRMED_MATERIAL_IMPACT`). Nessun lavoro concorrente rilevato (fetch eseguito prima del commit). Nessuna optimization, nessun confronto PF/WR economico, nessuna ricerca di edge, nessun backtest pluriennale in questa fase — solo due run diagnostici **corti** (2026.01.01-2026.08.25, ~8 mesi) pre/post fix.

**Obiettivo**: applicare il fix minimale TF-scoped a TSI (autorizzato senza richiedere un trace pre-fix pluriennale, data la forza dell'evidenza matematica già raccolta in Phase 7.17) e validarlo dinamicamente con il minimo run MT5 necessario, verificando convergenza reale verso la versione TF-scoped e assenza di side-effect.

---

## 1. Fix applicato

`if(tf != NXS_Profile_TF("TSI")) return s;` in `NXS_Strat_TSI()` (`NXS_Strategies.mqh:1367`), subito dopo `ENUM_TIMEFRAMES tf = NXS_EffTF();`, **prima** di qualunque lettura di `curBar0`/`c1` e di ogni mutazione di `g_tsiState` — verificato staticamente (test dedicato) che nessuna mutazione precede la guardia. Diff finale rispetto alla baseline: **esattamente una riga**. Nessuna modifica a formula/periodi/soglie/TF canonico/gate/SL-TP/selector/altre strategie. Nessun wrapper riusa `NXS_Strat_TSI()` (confermato: un solo punto di chiamata reale nell'intero albero `MQL5/`, il router in `NEXUS_EA_v2.mq5`) — il fix non si propaga a nessun'altra strategia, a differenza di ORDER_BLOCK/OB_MIT.

## 2. Baseline pre-fix congelata

Riusati gli artifact Phase 7.17 (formalizzazione matematica, casi minimi ad aritmetica esatta, misura di materialità su dati reali già disponibili) — nessun nuovo lavoro di baseline richiesto, come esplicitamente autorizzato.

## 3. Run diagnostico corto pre/post fix

Istrumentazione diagnostica temporanea non comportamentale (stesso schema di Phase 7.14, aggiunta e poi rimossa due volte: prima e dopo il fix). **Nota operativa**: a differenza di ORDER_BLOCK, TSI non ha rami "silenziosi" a basso costo prima del punto di log — pre-fix l'istrumentazione logga OGNI tick che raggiunge la chiamata TSI nel router multi-TF (non solo le transizioni di barra), producendo un trace molto più pesante per unità di tempo calendario (75.474 righe / ~50 min per la finestra pre-fix, contro poche migliaia attese). Post-fix, la guardia blocca l'esecuzione PRIMA del punto di log per ogni TF non canonico, riducendo drasticamente il volume (12.579 righe / ~47 min, tutte D1). Due run MT5 (GOLD H4/tick reali, `InpStrategySelector=5`, `InpProfileMultiTF=true`, selettore isolato), stessa finestra 2026.01.01-2026.08.25: pre-fix completato in 0:50:15, post-fix in 0:47:19 — tempo di calendario simile (stessa mole di tick da riprodurre), I/O drasticamente più leggero post-fix.

## 4. Curazione delle tracce (scoperta metodologica)

Le tracce raw (10.4MB/1.7MB) sono troppo grandi per il commit. Una prima curazione ingenua ("1 riga per barra") si è rivelata **scorretta per la traccia pre-fix**: verificato che tutte le 166 chiavi D1 pre-fix mostrano **più di un `signal_dir` distinto** entro lo stesso `close_time_srv` (fino a 4 valori: WARMUP/NONE/BUY/SELL) — prova diretta che la contaminazione cross-TF altera lo stato **fra due tick etichettati D1 della stessa barra apparente**. Collassare al primo tick avrebbe cancellato evidenza reale del difetto. Adottata invece una curazione **transition-based** (tiene una riga solo quando il `signal_dir` cambia rispetto all'ultima riga tenuta per la stessa chiave `(close_time_srv, tf)`): verificata senza perdita di informazione (i risultati del confronto A/B/C sono identici, byte per byte nel conteggio finale, a quelli calcolati sulle tracce raw complete). Tracce curate committate: 47.634 righe (prefix, 6.6MB) e 166 righe (postfix, 23KB).

## 5. Confronto A/B/C

**Guardia efficace al 100%**: 0 righe non-D1 osservate post-fix (atteso: 0). **A (pre-fix) vs B (post-fix)**, stessi tick reali: solo 4 coppie (data,direzione) coincidono; **250 eventi "canonici" presenti SOLO in A** (spuri, eliminati dal fix) contro **4 presenti solo in B** — la contaminazione produce un numero di eventi D1-taggati ordini di grandezza superiore a quelli realmente generati post-fix, coerente con Phase 7.17 (contaminazione universale). **B (EA reale post-fix) vs C (ricostruzione Python TF-scoped, storia locale piena 2023-10-02+ per il warm-up poi ritagliata sulla finestra)**: **tutti gli 8 segnali B trovati in C** (0 presenti solo in B), **5 presenti solo in C** — tutti antecedenti al primo segnale reale post-fix (2026-04-28) e interamente spiegati dalla differenza di warm-up (B riparte da `barsSeen=0` all'avvio del run Tester breve, gate `barsSeen<75` chiuso fino a metà aprile; C eredita un filtro già maturo dalla storia locale piena). Per il periodo maturo comune, **B e C coincidono al 100%**. Valori TSI intermedi su 92 date comuni: differenza media assoluta 0.109, massima 0.875 — piccola, coerente con la differenza di warm-up dichiarata. Python NON è ground truth — MT5 post-fix resta la fonte canonica.

## 6. Decisione finale

**`FIX_CAUSALLY_VALIDATED`**. Basi: guardia efficace al 100% sul trace reale; eliminazione di 250 eventi spuri pre-fix su stessi tick reali; convergenza 100% fra EA reale post-fix e ricostruzione Python TF-scoped nel periodo maturo comune; nessun side-effect inatteso (compilazione pulita, 0 errori, stessi 2 warning della baseline; nessun'altra strategia toccata).

## 7. Evidenza storica

Riusata la classificazione per-artifact già fatta in Phase 7.17 (`tsi_historical_evidence_map_v1.json`, tutti `POSSIBLY_CONTAMINATED`). Creata `TSI_IMPL_V1_CONTAMINATED` (storica, fino a `8590f63`) e `TSI_IMPL_V2_TF_GUARDED` (canonica corrente). Nessun artifact cancellato, nessun PF/WR storico riusato come evidenza della nuova implementazione. Motore Python: `PARTIAL_STRUCTURAL_MODEL_NOT_EVENT_LEVEL_PARITY_VALIDATED` — elevata fiducia dalla convergenza B/C di questa fase, ma non equivalente a parity evento-per-evento nel senso stretto (nessun trace EA pluriennale raccolto).

## 8. Binario finale

Istrumentazione rimossa due volte (prima e dopo la cattura post-fix); compilazione finale pulita confermata (`compile_final_clean.log`, 0 errori, 2 warning, invariati rispetto alla baseline pre-fix). `git diff` rispetto a `8590f63` limitato a una riga in `NXS_Strategies.mqh`.

## 9. Regressione

Suite completa Phase 7 eseguita **prima del commit** (working tree con la sola riga del fix, nessun'altra modifica): 24 fallimenti, tutti riconducibili — per struttura identica al pattern già documentato in Phase 7.15 per ORDER_BLOCK — al fatto che ogni fase precedente verifica "nessuna modifica a `MQL5/`" contro un working tree **non ancora committato**. Ri-eseguita **dopo il commit** (checkout pulito, `git status` vuoto): questa classe si è **auto-risolta come previsto** (24 → 5 fallimenti residui). I 5 residui, tutti classificati:

| Gruppo | N test | Categoria | Causa |
|---|---|---|---|
| Phase 7.12 staleness self-check (ORDER_BLOCK) | 1 | Atteso, preesistente | Già documentato in Phase 7.15 - non causato da questa fase |
| Phase 7.13 staleness self-check (ORDER_BLOCK) | 1 | Atteso, preesistente | Idem |
| Phase 7.15 `sources_and_binaries_audit_v1.json` hash | 2 | Atteso, **nuovo in questa fase** | L'audit di Phase 7.15 registra l'hash di `NXS_Strategies.mqh` "come sorgente finale pulito" al tempo di Phase 7.15 (post-fix OB, pre-fix TSI) - la guardia TSI di questa fase ha legittimamente cambiato quel file, rendendo l'hash storico stale per costruzione, non un difetto |
| Phase 7.17 staleness self-check (TSI) | 1 | Atteso, **nuovo in questa fase** | Il self-check di Phase 7.17 rileva correttamente che la guardia TSI (allora solo proposta) è ora presente - stesso comportamento voluto già visto per Phase 7.12/7.13 su ORDER_BLOCK |

**Nessuna regressione reale attribuibile al fix TSI.** Stesso pattern esatto già classificato "atteso" in Phase 7.15 per ORDER_BLOCK, ora esteso naturalmente a TSI. *(Non è stata eseguita una "Integration Closure" dedicata come Phase 7.15 - valutazione lasciata all'utente: la classe di fallimenti osservata è la stessa già classificata come attesa/non bloccante in precedenza, non richiede necessariamente una fase dedicata ora.)*

## Deliverables

`build_tsi_parity_comparison.py` + `tsi_parity_comparison_v1.json`, `build_tsi_decision_card_v2.py` + `tsi_decision_card_v2.json`, `build_tsi_historical_evidence_migration.py` + `tsi_historical_evidence_migration_v1.json`, `build_curated_traces.py` + le due tracce curate committate, log di compilazione (diag prefix/postfix/final clean), config Tester (prefix/postfix), snapshot dell'istrumentazione (prefix/postfix), verificatore indipendente (`verify_phase_7_18.py`, VERIFY OK), 28/28 test propri (`test_phase_7_18.py`), questo vault report. Tracce RAW (10.4MB/1.7MB) non committate, riproducibili localmente rilanciando i due run Tester con le config committate.

## Vincoli preservati

Nessuna optimization, nessun backtest pluriennale, nessuna ricerca di edge in questa fase. Nessuna promozione live. Nessun'altra strategia toccata. Nessun artifact storico cancellato o reinterpretato economicamente.

## Regressione

```
7.17: TSI INTEGRITY AUDIT (DEFECT_CONFIRMED_MATERIAL_IMPACT)
7.18: TSI MINIMAL FIX + SHORT LIVE VALIDATION - COMPLETATO
  fix: una riga, guardia TF-scoped, verificata prima di ogni mutazione
    di stato, nessun wrapper/riuso (a differenza di ORDER_BLOCK)
  run diagnostico corto pre/post (8 mesi, non pluriennale): guardia
    efficace al 100% (0 righe non-D1 post-fix)
  A(pre-fix)/B(post-fix) stessi tick: 250 eventi spuri eliminati dal
    fix, solo 4 coincidono esattamente pre/post
  B(EA reale post-fix)/C(Python TF-scoped): 100% di convergenza nel
    periodo maturo comune - le uniche differenze sono spiegate dal
    warm-up piu' corto del run breve, non da un residuo del difetto
  curazione tracce: scoperta che una curazione ingenua avrebbe
    cancellato evidenza reale (flip-flop di signal_dir da
    contaminazione entro la stessa barra) - corretta con approccio
    transition-based, verificata senza perdita
DECISIONE: FIX_CAUSALLY_VALIDATED
SUITE COMPLETA (checkout pulito, post-commit): 594 passed, 5 failed
  (tutti staleness self-check/hash attesi - 2 preesistenti su
  ORDER_BLOCK, 3 nuovi ma della stessa categoria su TSI/audit 7.15 -
  0 regressioni reali)
PROSSIMO: nessuna promozione live. Come da richiesta utente, pausa del
  ciclo bug-hunting - prossimo passo e' il checkpoint shortlist
  strategie candidate a edge validation (BREAKOUT_ACC/ORDER_BLOCK/TSI
  ora sufficientemente ripulite)
```
