# NEXUS - Phase 7.6C SEQ-0014B Structural Feasibility Preflight

**Baseline:** `fb52168` (Phase 7.6B, popolazione di setup a 6 famiglie, architettura pooled stratificata). Concern nuovo del reviewer, aggiunto esplicitamente a questa fase: **cross-family same-bar/near-bar dependence** (es. BREAKOUT+DISPLACEMENT+VOLATILITY_EXPANSION sullo stesso bar 1500 non devono contare come 3 realizzazioni indipendenti).

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.** Nessuna scelta di primary outcome.

**SPEC COMMIT:** `6c0d3f64d74a8d0495c4b634bee0c9d7d2ea8a93`
**RESULT COMMIT:** `80e7cbc124e40c61a9f0d28a31dd3c6d2e1a5fc3`

---

## Esito

| | |
|---|---|
| **SEQ0014B_STATUS** | `NOT_TESTABLE_WITH_FROZEN_SETUP_POPULATION` (hard stop) |
| **Verdetto composito** | `MATCHING_STRUCTURALLY_INFEASIBLE` (tutte e 6 le famiglie) + `POOLED_DEPENDENCE_COLLAPSE` + `NEEDS_ARM_SIZE_POLICY` |

Nessun "fix" applicato (vietati esplicitamente): nessuna famiglia rimossa, nessun cutpoint terzile cambiato, MED non reincluso, timing t-1 non toccato, nessun cherry-picking sulla famiglia migliore.

## 1. Unita' di analisi (SPEC COMMIT, prima di qualunque count)

**Decisione: FAMILY-EVENT UNIT con clustering di dipendenza cross-family obbligatorio** (non ROW-FIRST). Motivata dall'estimand MECH-23 e dalla necessita' di preservare `setup_family_id` come stratificazione per il contrasto "stessa famiglia, CHOPPY vs TRENDING" - **non** dalla dimensione campionaria risultante (decisione presa prima di calcolare qualunque n).

**Geometria within-family:** `natural_horizon=40`/`outcome_overlap_embargo_bars=39` condivisi (convenzione di progetto gia' usata per SEQ-0009/SEQ-0015/H006-RECLAIM), ma `episode_gap_rule` **derivato dal meccanismo di ciascun detector** (mai copiato fra meccanismi diversi):

| Famiglia | episode_gap_rule | Motivazione meccanica |
|---|---|---|
| VOLATILITY_EXPANSION | 1 | confronto istantaneo TR vs propria ATR, nessun livello persistente |
| DISPLACEMENT | 1 | stessa classe meccanica (confronto istantaneo) |
| BREAKOUT | 2 | livello rolling 20-barre, shift di 1 barra/step (stessa classe di SWEEP) |
| SWEEP | 2 | **riusato identico** da SEQ-0009 (Phase 7.5B), non ri-derivato |
| COMPRESSION_RELEASE | 5 | lunghezza della propria precondizione (`compression_min_bars`) |
| PULLBACK | 2 | livello rolling 20-barre, stessa classe di BREAKOUT/SWEEP |

**Cross-family dependence clustering (nuovo, obbligatorio):** soglia condivisa = embargo (39 barre), applicata all'UNIONE delle righe rappresentative within-family indipendenti di tutte e 6 le famiglie - mai una somma ingenua.

**Matching:** contrasto sempre "stessa `setup_family_id`, CHOPPY vs TRENDING" - control pool ristretto a `SAME_SETUP_FAMILY_ID_OPPOSITE_REGIME_ONLY`, dimensione `volatility_state_pre_setup` (atr_percentile[t-1], cutpoint riusati identici da Phase 7.5C) - nessuna dimensione aggiuntiva inventata.

**Arm-size policy:** confermata l'assenza di un requisito canonico "minimo per braccio" in `minimum_evidence_gates.json` - flag `NEEDS_ARM_SIZE_POLICY` esplicito, nessuna soglia inventata.

## 2. Popolazione di setup reale (development_discovery, [396,2789), 2393 barre)

| | n_total | n_CHOPPY | n_TRENDING | n_MED_excluded |
|---|---|---|---|---|
| **Overall** | 2580 | 1265 | 1315 | 1251 |
| VOLATILITY_EXPANSION | 592 | 277 | 315 | 276 |
| DISPLACEMENT | 77 | 32 | 45 | 32 |
| BREAKOUT | 282 | 68 | 214 | 98 |
| SWEEP | 177 | 61 | 116 | 71 |
| COMPRESSION_RELEASE | 166 | 79 | 87 | 93 |
| PULLBACK | 1286 | 748 | 538 | 681 |

## 3. Overlap audit same-bar/cross-family (concern del reviewer, confermato empiricamente)

- **65.4%** dei record di setup condivide la propria riga con almeno un'altra famiglia (1687/2580).
- Fino a **5 famiglie** sullo stesso bar.
- Combinazione piu' frequente: `PULLBACK + VOLATILITY_EXPANSION` (232 righe), seguita da `COMPRESSION_RELEASE + PULLBACK + VOLATILITY_EXPANSION` (79) e `BREAKOUT + DISPLACEMENT + VOLATILITY_EXPANSION` (26, l'esempio-tipo del reviewer).
- Diagnostica secondaria: **0** righe escluse per MED hanno una famiglia non-MED co-locata sulla stessa riga - atteso strutturalmente (`regime_at_t_minus_1` e' una proprieta' della RIGA, non della famiglia: tutte le famiglie sulla stessa riga condividono lo stesso regime per costruzione).

## 4. Geometria within-family (EVENT -> EPISODE -> INDEPENDENT, per famiglia x regime)

| Famiglia | Regime | EVENT | EPISODE | INDEPENDENT |
|---|---|---|---|---|
| BREAKOUT | CHOPPY / TRENDING | 68 / 214 | 50 / 95 | **26 / 20** |
| COMPRESSION_RELEASE | CHOPPY / TRENDING | 79 / 87 | 34 / 34 | **16 / 18** |
| DISPLACEMENT | CHOPPY / TRENDING | 32 / 45 | 32 / 43 | **21 / 22** |
| PULLBACK | CHOPPY / TRENDING | 748 / 538 | 150 / 161 | **12 / 12** |
| SWEEP | CHOPPY / TRENDING | 60 / 116 | 42 / 88 | **19 / 21** |
| VOLATILITY_EXPANSION | CHOPPY / TRENDING | 277 / 315 | 201 / 208 | **9 / 14** |

Compressione fortissima per le famiglie ad alta frequenza (PULLBACK 748/538 nominali -> 12/12 indipendenti).

## 5. Geometria pooled cross-family (il punto centrale di questa fase)

| | Valore |
|---|---|
| Record di setup nominali pooled | 2580 |
| Righe uniche | 1550 |
| Cluster "episodio" grezzi pooled (diagnostico) | **1** (l'intera popolazione collassa in un solo cluster grezzo - conferma quanto densamente le 6 famiglie co-occorrono) |
| Somma naive independent units per-famiglia (MAI l'autorita') | 210 |
| **Pooled independent units (autorita', dopo declustering cross-family)** | **11** |
| CHOPPY independent units (pooled) | 26 |
| TRENDING independent units (pooled) | 29 |

**No-double-counting invariant:** verificato meccanicamente (`pooled <= naive_sum` sempre vero, mai violato) + **test sintetico di regressione dedicato**: famiglia A e famiglia B ciascuna indipendente da sola (3+3=6 naive), ma con righe sottostanti condivise entro l'embargo -> il pooled collassa correttamente a 3 (non 6); controllo negativo con righe lontane -> pooled=6 (nessun collasso spurio). 52/52 PASS.

Il collasso da 210 (naive) a 11 (pooled reale) e' la conferma diretta, sui dati reali, del rischio segnalato dal reviewer: pooling senza declustering cross-family avrebbe gonfiato il campione di quasi 20x.

## 6. Matching feasibility per famiglia

**Tutte e 6 le famiglie: `MATCHING_STRUCTURALLY_INFEASIBLE`.** Causa: il control pool (setup TRENDING della stessa famiglia) e' strutturalmente sotto `minimum_control_count=20` (soglia gia' congelata/riusata, non inventata per questa fase) una volta condizionato per direzione (BUY/SELL trattati separatamente, correttamente, per evitare di confrontare un breakout rialzista con un breakout ribassista). Esempio: BREAKOUT-TRENDING ha 20 unita' indipendenti totali, ma solo 11 BUY e 9 SELL - entrambi sotto soglia.

## 7. Verdetto strutturale composito (nessun family-level nascosto sotto un pooled verde)

- Nessuna famiglia raggiunge `FAMILY_LEVEL_FEASIBLE`.
- `pooled_all_regimes_independent_units=11` sotto la soglia canonica riusata (`n_nominal_minimum=30`).
- `POOLED_DEPENDENCE_COLLAPSE` rilevato.
- `NEEDS_ARM_SIZE_POLICY` sempre presente (nessun gate per-braccio inventato).
- **Hard stop:** `SEQ0014B_STATUS = NOT_TESTABLE_WITH_FROZEN_SETUP_POPULATION`.

## RECLAIM discrepancy e failure-memory

Solo riferimento a quanto gia' documentato in `fb52168` (registry dice REFUTED_AT_DISCOVERY, l'artifact frozen mostra INSUFFICIENT_SAMPLE) - `market_sequence_registry_v1.json` **non toccato**, fuori scope. Gli status storici `REFUTED_AS_AUTONOMOUS_EDGE` (Phase 5.5) riportati come provenance, mai usati per alterare la geometria.

## Regressione

**SPEC:** 60/60 PASS. **RESULT:** 52/52 PASS (incluso il test sintetico obbligatorio del no-double-counting invariant + controllo negativo). **0 regressioni** sulle altre 15 suite Phase 7 (17 totali).

## Deliverables

`seq0014b_structural_preflight_spec_v1.json` + `build_seq0014b_structural_preflight_spec.py` + `test_seq0014b_structural_preflight_spec.py` (SPEC COMMIT `6c0d3f6`); `seq0014b_structural_preflight_result_v1.json` + `build_seq0014b_structural_preflight_result.py` + `test_seq0014b_structural_preflight_result.py` (RESULT COMMIT `80e7cbc`), entrambi in `server/research_scripts/phase7/phase7_6c/`.

---

**NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.** Nessuna scelta di primary outcome. SEQ-0015 e SEQ-0009 restano chiuse.

**Progresso verso demo (invariato, come richiesto): ~68%.**

```
PRIMO SERIOUS BACKTEST: 100%
VERSO DEMO: ~68%
██████▊░░░
FASE ATTUALE:
SEQ-0014B setup population formalizzata
PROSSIMO SBLOCCO:
structural preflight pooled
con controllo cross-family dependence
DOPO:
preregistration outcome/inference
→ discovery
→ internal validation
```

Resta al 68%: il preflight pooled con controllo cross-family dependence e' stato eseguito - ha scoperto che il disegno frozen non ha abbastanza informazione (`NOT_TESTABLE_WITH_FROZEN_SETUP_POPULATION`), non che ne ha di piu'. Nessuna nuova evidenza empirica di edge/filter-utility ottenuta - anzi, un esito negativo strutturale, riportato per intero senza nasconderlo.
