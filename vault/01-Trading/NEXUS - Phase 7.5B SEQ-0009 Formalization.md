# NEXUS - Phase 7.5B SEQ-0009 (MECH-18 SWEEP) Minimal Detector Formalization

**Baseline:** `8593f9c` (Phase 7.5A closed - infrastructure complete). Prima applicazione reale del Sequence Structural Feasibility Gate a una nuova family. **Questo e' il FORMALIZATION COMMIT - congela detector/direction/episode/horizon/embargo/matching_spec PRIMA di eseguire il gate.** Nessun risultato del gate e' stato ancora osservato al momento di questo commit.

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED. NO STATISTICAL CONTRACT BUILT.**

---

## 1. Detector riusato senza modifica

Fonte operativa: `server/research_scripts/phase7/phase7_1/build_events_p71.py` (copia verbatim del blocco SWEEP di `server/research_scripts/phase5/build_events.py` - stesso `CFG['sweep_lookback_n']=20`, stessa formula, verificato leggendo entrambi i file riga per riga).

```
sw_hi = max(high[i-20:i])   (esclude la barra i)
sw_lo = min(low[i-20:i])

HIGH sweep: high[i] > sw_hi  AND  close[i] < sw_hi   -> direction=-1
LOW  sweep: low[i]  < sw_lo  AND  close[i] > sw_lo    -> direction=+1
```

**Verifica causale:** `sw_hi`/`sw_lo` usano solo le 20 barre precedenti (indice `i` escluso dallo slice) - nessun dato con indice `>i` entra nella detection. `atr[i]` e' usato solo per normalizzare la *magnitude* diagnostica, mai per la soglia di rilevazione (che confronta prezzi grezzi). **Freeze decision: REUSED_UNCHANGED** - nessuna incompatibilita' trovata, il detector non e' stato corretto guardando la sua firing geometry.

## 2. Direction semantics

`event_direction_policy = PER_EVENT_DIRECTION`, derivata dal campo `swept_side` gia' emesso dal detector: **HIGH swept → SELL**, **LOW swept → BUY** - stessa convenzione di segno (+1=bullish/-1=bearish) gia' usata da ogni altro detector in `build_events.py`. Codifica l'ipotesi causale dichiarata per MECH-18 (liquidity-grab-then-reversal): rigetto del livello superiore → aspettativa ribassista, e viceversa. Derivata dalla semantica del meccanismo, non da alcun outcome.

**Edge case documentato ex-ante:** una barra puo', in teoria, soddisfare entrambe le condizioni HIGH/LOW-sweep simultaneamente (evento composto/ambiguo) - **esclusa per regola** dal sequence_event set. Verificato occorrere su **2/641** barre SWEEP (0.31%) sull'intero dataset (righe 1472, 4305 - conteggio strutturale su row_index, nessun outcome coinvolto).

**Isolamento da RECLAIM:** SEQ-0009 valuta il solo SWEEP, mai condizionato sul verificarsi di un RECLAIM successivo (famiglia distinta, gia' legata al claim RECLAIM refutato in Phase 7.1).

## 3. Episode rule (derivata ex-novo, non copiata da SEQ-0015)

`episode_gap_rule = 2` barre. **Rationale meccanico specifico a SWEEP:** il riferimento (`rolling_high_20`/`rolling_low_20`) si sposta di una barra ad ogni step - due sweep flag sullo stesso lato a distanza ≤2 barre sono quasi certamente reazioni alla stessa zona di liquidita' ancora in fase di rigetto, non due raid indipendenti. SEQ-0015 usa gap=3 per un fenomeno diverso (burst pluri-barra) - **non riusato qui**.

## 4. Natural horizon ed embargo

`proposed_natural_horizon = 40` barre H4 (~6.7 giorni) - derivato dalla scala temporale del meccanismo (rigetto/inversione atteso risolversi entro un orizzonte multi-giorno), stesso ordine di grandezza gia' indipendentemente valido per altri meccanismi di reversal H4 nel progetto - riusato come convenzione generale, non ottimizzato guardando alcun conteggio di eventi SEQ-0009.

`proposed_outcome_overlap_embargo_bars = 39` - **vincolato matematicamente** da `natural_horizon - 1` (stessa formula di SEQ-0015), non una scelta indipendente.

## 5. Matching spec

| Campo | Valore | Fonte |
|---|---|---|
| `match_dimensions` | `["volatility_state_pre_event"]` | terzile di `atr_percentile` a **t-1** (mai a t - stessa motivazione causale di SEQ-0015, non lo stesso numero), fit **solo** su discovery |
| `k` | 5 | convenzione generale, `baseline_contract_v4.json` |
| `minimum_control_count` | 20 | default `BaselineEngineV4`/`baseline_contract_v4.json` |
| `max_control_reuse_per_run` | 5 | stesso valore di k, regola simmetrica generale |
| `split_boundaries` | discovery=[396,2789), internal_validation=[2789,3980), locked_validation=[3980,5189), final_holdout=[5189,6179) | tradotti in row-index da `partition_manifest_v1.json`/`splits_p71.py` sul dataset `xauusd_h4_bars_p71.csv` |
| `control_pool_construction_policy` | stesso split, esclusi evento stesso + `\|r-t\|<=40` + stesso episode_id | stessa formula/motivazione di `control_exclusion_window` SEQ-0015 |

`trend_state` **escluso** in questa formalizzazione minimale (direzione gia' derivata dal lato swept - aggiungerlo aumenterebbe i gradi di liberta' senza giustificazione causale distinta immediata).

`discovery_partition.n_bars = 2393` - **stesso valore gia' pubblicato** per `development_discovery` in Phase 7.4A/SEQ-0015 (stesso dataset/partition, confermato).

## 6. No-rescue clause

Nessuno di questi parametri sara' modificato dopo aver visto il risultato del gate. Un verdetto non-FEASIBLE non autorizza un secondo tentativo sotto la stessa identita' - una variante richiederebbe una nuova `sequence_family_id` e una nuova preregistrazione.

## 7. Regressione - 26/26 PASS

`test_seq0009_frozen_spec.py`: coerenza interna dello spec (hash detector correnti, embargo=horizon-1, confini di split contigui, terzili crescenti, edge case documentato, tutti i flag `no_*` presenti). Nessun outcome letto, nessuna esecuzione del gate strutturale in questo commit.

## 8. File

`server/research_scripts/phase7/phase7_5b/build_seq0009_frozen_spec.py`, `seq0009_frozen_structural_spec_v1.json`, `test_seq0009_frozen_spec.py`.

---

**NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED. NO STATISTICAL CONTRACT BUILT.** SEQ-0015 resta chiusa, non riesaminata.

**Prossimo passo (commit separato):** eseguire il Sequence Structural Feasibility Gate (Phase 7.5A) su questo spec congelato, outcome-blind, sulla sola partition `development_discovery`.
