# NEXUS - Phase 7.13 — ORDER_BLOCK Diagnostic Adjudication

**Baseline:** `dc1874e` (Phase 7.12). Nessun commit concorrente di Codex rilevato (fetch eseguito prima e dopo il lavoro). **Nessun file MQL5/EA modificato in questa fase** — solo istrumentazione diagnostica Python, in `server/research_scripts/phase7/phase7_13/`. Nessuna optimization, nessun tuning SL/TP, nessun parameter sweep, nessun confronto di redditività, nessuna promozione live. Artifact BREAKOUT_ACC (Phase 7.9H-K) usati solo come lettura, mai modificati.

**Obiettivo**: eseguire il protocollo diagnostico preparato in Phase 7.12 per determinare se e quanto ORDER_BLOCK è realmente affetto da CROSS_TIMEFRAME_STATE_CONTAMINATION, senza correggere la strategia e senza cercare performance.

---

## 1. Identità e configurazione congelate

**Identità canonica**: `ORDER_BLOCK` (selettore 15, `InpStrat_ORDER_BLOCK=true`, TF canonico `PERIOD_D1` — `NXS_Profile_TF`, `NXS_StrategyProfiles.mqh:273`). **Funzione raggiunta**: `NXS_Strat_OrderBlock()` (`NXS_Strategies.mqh:2141-2161`), che chiama `NXS_OB_UpdateSide()` (righe 2077-2139) su due stati globali separati `g_obBuy`/`g_obSell` (`SNXSOBState { active; obLo; obHi; lastBarTime; barsWaited }`, righe 2069-2075). **Nessuna guardia TF presente** prima della lettura/mutazione dello stato — verificato riga per riga.

**Percorso**: `NEXUS_EA_v2.mq5:CollectAllSignals` (righe 670-733, multi-TF quando `InpUseStrategyProfiles=true` e `InpProfileMultiTF=true`, **entrambi default di sistema**) → per ogni TF distinto fra i profili di TUTTE le strategie live (`passes[]`, unione da `NXS_Profile_TF`) → `NXS_ActivateTF(passes[p])` (ricalcola `g_atr` ecc. per quel TF) → `NXS_CollectRaw()` → chiamata **incondizionata** a `NXS_Strat_OrderBlock()` (riga 535, blocco "Classic 16", nessun `if` di abilitazione a livello di chiamata) → mutazione di `g_obBuy`/`g_obSell` con `tf = NXS_EffTF() = passes[p]` **qualunque esso sia** → il segnale prodotto sopravvive al router **solo se** `NXS_Profile_TF("ORDER_BLOCK") == passes[p]` (riga 710) — altrimenti scartato, ma la mutazione resta.

**Non assunto identico a BREAKOUT_ACC**: verificato che il meccanismo di stato è qualitativamente diverso (vedi punto 6).

## 2. Dimostrazione causale del difetto

**Prova sintetica calcolabile a mano** (`synthetic_causal_proof_v1.json`): una zona BUY attiva condivisa, 1 barra D1 + 6 barre H4 intercalate, valori attesi calcolati a mano (non prodotti facendo girare il codice sotto verifica). Risultato — le 4 fasi richieste sono dimostrate separatamente nello stesso scenario minimo:
1. **Chiamata su TF non canonico**: passaggio H4 #5.
2. **Mutazione dello stato**: `g_obBuy.active` True→False (consumo one-shot).
3. **Output scartato**: il segnale BUY prodotto a H4#5 verrebbe scartato dal router (TF≠D1) — mai un segnale "generated".
4. **Effetto su evento canonico futuro**: la barra D1 successiva, che da sola avrebbe prodotto un segnale BUY genuino (zona ancora intatta), non produce nulla — zona già consumata dalla contaminazione H4.

## 3. Trace completo dello stato

`state_mutation_trace_v1.json`: 3 casi reali selezionati da §4 (2 segnali D1 genuini soppressi, 1 segnale D1 creato solo dalla contaminazione), ciascuno con la timeline completa fra due chiusure D1 consecutive (58-66 eventi rilevanti su 168 eventi totali multi-TF nella finestra), con timestamp/TF chiamante/TF canonico/stato prima/operazione/stato dopo/segnale prodotto/accettato-scartato/motivo del gate/effetto sull'evento canonico successivo.

## 4. Quantificazione dell'impatto (dati reali)

**Dataset**: serie M15 reale (`nxs_m15_gold_extended.csv`, già presente nel working tree, non generata in questa fase, non ri-verificata con un secondo export indipendente — provenienza dichiarata come limite) ricampionata deterministicamente in M30/H1/H4/D1 **auto-consistenti** (stesso confine di giorno 01:00, dedotto empiricamente). Periodo coperto: **2023-10-02 → 2026-08-25 (~2.9 anni)** — più corto dello storico 2019-2026 usato altrove, dichiarato esplicitamente, non usato per stime di redditività. Passaggio M5 escluso (fonte non abbastanza fine) — limite **inferiore**, non sovrastima.

| Metrica | Stream A (implementato) | Stream B (TF-scoped) |
|---|---|---|
| Raw trigger su passaggi non canonici (H4+H1+M30+M15) | **2394** | 0 (mai eseguiti) |
| Raw trigger su passaggio D1 | 59 | 34+25=59 valutati, **7 emessi** |
| Segnali D1 "generated" (pre-gate H1/SMC) | **59** | **7** |
| Sovrapposizione fra i due insiemi | **0** | **0** |

Su 745 chiusure D1 valutate: **59 eventi solo in A** (segnali creati SOLO dalla contaminazione) e **7 eventi solo in B** (segnali D1 genuini soppressi dalla contaminazione) — **zero coincidenze**. Gate a valle (`g_structH1.trend`, `NXS_SMCReactionOK`) **non modellati** in questa fase (dichiarato) — il confronto è al livello di raw trigger pre-gate, esattamente il punto dove avviene la mutazione sotto diagnosi; i gate a valle possono solo FILTRARE ulteriormente un flusso già contaminato, mai ripristinarlo.

**DEFECT EXISTS**: sì. **DEFECT MATERIALLY CHANGES STRATEGY BEHAVIOR**: sì — nel periodo studiato l'impatto è totale, non parziale.

## 5. Historical evidence impact

`historical_evidence_impact_map_v1.json` (nessun artifact cancellato, solo classificato):

| Artifact | Classificazione |
|---|---|
| `server/backtest.py::sig_order_block/_ob_series` (motore Python) | UNAFFECTED_BUT_NOT_REPRESENTATIVE_OF_LIVE — single-TF per costruzione, struttura equivalente a Stream B, ma **non rappresenta** ciò che l'EA live esegue oggi |
| `results/phase2_baseline_20260705_v2.0.27.csv` (8 trade, PF 0.00, tick reali) | POSSIBLY_CONTAMINATED — configurazione multi-TF del run non verificabile dal CSV |
| `results/phase_partB_silent_diagnostic_20260706.csv` (1955 pattern_fired) | POSSIBLY_CONTAMINATED — stessa ragione |
| Commenti PF 0.67/0.38 in `NXS_StrategyProfiles.mqh` | CANNOT_DETERMINE — origine non ricostruibile senza git blame per-strategia (fuori scope) |
| `vault_documentation=PRESENT` (census 7.11) | CANNOT_DETERMINE — non riletta articolo per articolo in questa fase |

Nessun PF/WR storico è stato reinterpretato come prova a favore o contro la strategia canonica.

## 6. Confronto con BREAKOUT_ACC (solo precedente architetturale)

`breakout_acc_comparison_v1.json`. **Identico**: la *forma* del fix (guardia precoce `if(tf != NXS_Profile_TF(...)) return s;`, già applicata per BREAKOUT_ACC in `NXS_Strategies.mqh:1548`). **Diverso**: BREAKOUT_ACC corrompe solo un *timer* di cooldown (nessuna identità di livello); ORDER_BLOCK corrompe la *zona di prezzo stessa* e la sua fase di vita — un difetto qualitativamente più profondo (sotto-classe STATE_MACHINE_CONTAMINATION vs COOLDOWN, Phase 7.12). ORDER_BLOCK propaga a OB_MIT (chiamata diretta); BREAKOUT_ACC non ha un caso analogo. **Non trasferibile**: l'entità dell'impatto misurato (periodi/dataset diversi), la disponibilità di un trace EA live reale per la validazione post-fix (esistente per BREAKOUT_ACC, **assente** per ORDER_BLOCK — dipendenza esplicita), l'adjudication documentale a fonti multiple (fatta per BREAKOUT_ACC, non ripetuta qui — l'inferenza sul TF canonico poggia sulla dichiarazione di profilo già usata ovunque nel codice, non su una revisione documentale dedicata).

## 7. Decisione finale

`decision_card_order_block_v1.json`:

- **Decisione: `DEFECT_CONFIRMED_MATERIAL_IMPACT`**
- **historical_evidence_integrity: `PARTIALLY_COMPROMISED_FOR_MT5_REAL_TICK_RESULTS`** (Python UNAFFECTED ma non rappresentativo; 2 risultati MT5 a tick reali POSSIBLY_CONTAMINATED per configurazione non verificabile)
- **distortion_direction: `BOTH`** — la contaminazione sia sopprime segnali D1 genuini (FALSE_NEGATIVE_RISK, 7 casi) sia crea segnali che non sarebbero mai esistiti (FALSE_POSITIVE_RISK, 59 casi, numericamente dominante nel periodo studiato)

## 8. Proposta di fix (NON applicata)

Guardia proposta in `NXS_Strat_OrderBlock()`, subito dopo `tf = NXS_EffTF();`: `if(tf != NXS_Profile_TF("ORDER_BLOCK")) return s;` — stessa forma di BREAKOUT_ACC, effetto automatico su OB_MIT (nessuna patch separata). Invarianti da preservare: comportamento D1 invariato, SL/TP/gate H1/SMC invariati, `SNXSOBState` invariata. Test necessari: unit test della guardia, trace Decision/Gate/Execution pre/post fix, non-regressione OB_MIT, confronto post-fix vs Stream B di questa fase. Rollback: se il trace post-fix mostra ancora mutazioni su passaggi non-D1, se OB_MIT mostra un comportamento anomalo (i suoi moltiplicatori SL/TP potrebbero essere stati implicitamente calibrati sul comportamento contaminato — CANNOT_DETERMINE), o se il volume D1 post-fix diverge senza spiegazione dalla ricostruzione Stream B. **Separazione esplicita**: verifica implementazione (fatta, indipendente da qualunque esito economico) / validità evidenza storica (nessuna corretta retroattivamente) / redditività (NON presunta — correggere il meccanismo non implica un edge).

## Deliverables

`nxs_order_block_replica.py` (porting fedele della state machine), `build_synthetic_causal_proof.py` + `synthetic_causal_proof_v1.json`, `build_multi_tf_dataset.py` + `multi_tf_dataset_v1.json`, `build_ab_simulation.py` + `ab_simulation_v1.json`, `build_state_mutation_trace.py` + `state_mutation_trace_v1.json`, `build_historical_evidence_impact_map.py` + `historical_evidence_impact_map_v1.json`, `build_breakout_acc_comparison.py` + `breakout_acc_comparison_v1.json`, `build_decision_card.py` + `decision_card_order_block_v1.json`, `verify_phase_7_13.py` (VERIFY OK, 0 problemi), `test_phase_7_13.py` (30/30 PASS), questo vault report.

## Nota di riproducibilità (`multi_tf_dataset_v1.json` NON committato)

`multi_tf_dataset_v1.json` (~31MB, barre M15/M30/H1/H4/D1 complete) è un intermedio interamente deterministico e rigenerabile — **non è stato aggiunto a git** per non far crescere il repository di 31MB per un artifact derivato al 100% da `build_multi_tf_dataset.py` + la sua fonte (`server/research_scripts/nxs_m15_gold_extended.csv`, essa stessa non tracciata). Chiunque riesegua `build_multi_tf_dataset.py` con la stessa fonte locale ottiene un file bit-identico (hash verificato dal verificatore). **Limite dichiarato**: su un clone pulito del repository, `test_phase_7_13.py`/`verify_phase_7_13.py` richiedono che questo file (e la sua fonte) siano presenti localmente — vanno rigenerati eseguendo `build_multi_tf_dataset.py` prima degli altri builder/verifiche di questa fase.

## Vincoli preservati

Nessun file MQL5/EA modificato. Nessuna guardia applicata al sorgente reale. Nessuna campagna di backtest, nessuna optimization, nessun tuning SL/TP, nessun confronto di redditività, nessun rescue, nessuna promozione live. Artifact BREAKOUT_ACC (7.9H-K) e Phase 7.10/7.11/7.12 invariati (verificato via git diff). Nessun commit concorrente di Codex al momento del push.

## Regressione

Suite completa Phase 7: **443/443 PASS** (413 precedenti + 30 nuovi). Le 4 suite standalone legacy confermano gli stessi conteggi di baseline (68/72, 18/21, 22/23, 31/33) — nessuna nuova regressione.

## Blocker e dipendenze per un eventuale prossimo passo

1. **Autorizzazione dedicata** richiesta per qualunque modifica al sorgente EA (questa fase non la include, per istruzione esplicita).
2. **Nessun trace EA live reale per ORDER_BLOCK** trovato in questo repository (a differenza di BREAKOUT_ACC) — da costruire prima di una validazione pre/post fix equivalente a quella già fatta per BREAKOUT_ACC.
3. **Scelta strumentale aperta**: EA diagnostico standalone vs guardia di test sull'EA live per raccogliere quel trace — non decisa in questa fase.
4. **Historical evidence CANNOT_DETERMINE** (commenti PF non tracciabili, vault non riletto articolo per articolo) — non blocca la diagnosi già fatta, ma andrebbe chiuso prima di un fix definitivo.

---

```
7.12: CODA PRIORITA' COMPLETATA -> ORDER_BLOCK #1
7.13: DIAGNOSI CAUSALE COMPLETATA
  prova sintetica: 4/4 fasi causali dimostrate a mano
  dati reali (2023-10 -> 2026-08, ~2.9y): 59 vs 7 segnali D1,
    SOVRAPPOSIZIONE ZERO fra implementato e TF-scoped
  2394 raw trigger su passaggi non canonici contro 59 sul canonico
DECISIONE: DEFECT_CONFIRMED_MATERIAL_IMPACT (non low-impact, non
  insufficient-evidence)
DISTORSIONE: BOTH (sopprime E crea segnali)
FIX: proposto (guardia identica in forma a BREAKOUT_ACC), NON
  applicato - richiede autorizzazione dedicata
PROSSIMO PASSO SUGGERITO (non deciso qui): costruire il trace EA live
  reale mancante prima di autorizzare la patch
```
