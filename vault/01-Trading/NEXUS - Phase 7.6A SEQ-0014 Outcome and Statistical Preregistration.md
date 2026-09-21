# NEXUS - Phase 7.6A SEQ-0014 Outcome & Statistical Preregistration

**Baseline:** `844f852` (SEQ-0014 `FEASIBLE` sul gate strutturale). **Questo e' il PREREGISTRATION COMMIT - nessun outcome calcolato, nessuna discovery eseguita.**

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED. NO INTERNAL VALIDATION / LOCKED / FINAL HOLDOUT OPENED.**

---

## Stato: BLOCCATO su un punto solo

| | |
|---|---|
| **preregistration_status** | `BLOCKED_ON_CONTROL_POOL_ESTIMAND_AMBIGUITY` |
| **discovery_authorized** | `false` |

Tutte le altre sezioni del contratto (domanda scientifica, outcome family, inference/dependence/multiplicity, effect size, accesso ai dati) sono **congelate e complete** - sono logicamente indipendenti dalla scelta del control pool (definiscono COSA misurare, non CHI sono i controlli) e resteranno valide quando il blocco sara' risolto.

## 1. Il blocco - audit del control pool (sec.2 della richiesta)

Due estimand possibili per il contrasto causale:

- **A** (implementato oggi): EVENT = state-entry vs CONTROL = barra comparabile generica, **a prescindere** dal fatto che sia essa stessa in `LOW_INFORMATION_STATE`.
- **B**: EVENT = state-entry vs CONTROL = barra comparabile **specificamente non-choppy**.

**Audit strutturale quantificato (nessun outcome coinvolto):** la `control_pool_construction_policy` gia' congelata in Phase 7.5C esclude solo per finestra temporale (`|r-t|<=20`) e stesso episodio - **mai** per appartenenza allo stato. Risultato: **33.3%** del pool di controllo eleggibile per ciascuno dei 189 eventi e' esso stesso in `LOW_INFORMATION_STATE` - un valore che coincide quasi esattamente (33.35%) col base rate generale dello stato su tutta `development_discovery`. La policy attuale **non filtra affatto** per stato: implementa l'estimand A, non B.

**Evidenza che B e' il contrasto nativo del meccanismo (non scelta guardando outcome):** la `falsification_definition` originale di MECH-23, scritta in **Phase 7.2** (mesi prima che SEQ-0014 fosse mai sottoposta al gate strutturale), contrasta esplicitamente *"setup generati durante lo stato 'choppy'"* vs *"quelli generati in stato 'trending'"* - non vs una barra generica. Questa e' evidenza pre-esistente, non un ragionamento post-hoc.

**Conclusione:** correggere la control-pool semantics per implementare l'estimand B richiede una **NUOVA structural spec e un nuovo preflight** (il pool si restringerebbe di ~1/3, potendo cambiare `n_matched`/qualita'/reuse per alcuni eventi) - **mai una modifica silenziosa dopo il verdetto `FEASIBLE` gia' raggiunto**. Non risolto in questo commit, come da istruzione esplicita.

## 2. Domanda scientifica (congelata)

*"L'ingresso in `LOW_INFORMATION_STATE` modifica la distribuzione del movimento/range di prezzo futuro (orizzonte 20 barre) rispetto a una baseline comparabile per regime di volatilita' - senza alcuna direzione BUY/SELL implicita."* `event_direction_policy=NON_DIRECTIONAL` confermato invariato.

## 3. Outcome contract (congelato, riusa vocabolario esistente senza estenderlo)

| Outcome | Tier | Formula |
|---|---|---|
| `REALIZED_VOLATILITY_AFTER_SETUP` | **PRIMARY** | `(max(high[t+1..t+20])-min(low[t+1..t+20])) / ATR_t` |
| `PATH_EFFICIENCY` | SECONDARY | Kaufman Efficiency Ratio calcolato su finestra **strettamente futura** (t+1..t+20), non circolare |

Nessun outcome direzionale (`P(+X ATR before -1ATR)`, `MFE`/`MAE`) riusato - verificato che non compaiono nel contratto. Entrambi gli outcome sono **gia' presenti** in `outcome_surface_v3.py:ALL_OUTCOME_DEFINITIONS` (nessuna estensione del vocabolario generale) e corrispondono 1:1 all'`expected_outcome_family` di MECH-23 gia' dichiarato in Phase 7.2. Normalizzazione: `ATR_t` fisso (mai ricalcolato sulla finestra futura). Nessun outcome diagnostic registrato (famiglia ridotta al minimo: 1 primary + 1 secondary = 2).

## 4. Inference & dependence contract

Candidato: `block_sign_flip_permutation_matched_pair` (infrastruttura generale gia' calibrata in Phase 7.4A su simulazioni AR(1) sintetiche) - il test di simmetria sul segno di `d_i` si applica identico a un outcome continuo non-direzionale, nessuna modifica necessaria. **`validation_status = PRIMARY_INFERENCE_METHOD_NOT_YET_VALIDATED`** - stessa classificazione onesta gia' usata per SEQ-0015 (non "mai calibrato", ma "non ancora esercitato end-to-end su una discovery reale di questa family"). `dependence_validity_gate` riusato senza modifiche, stesse soglie congelate in Phase 7.4A (`acf_lag1_sensitive=0.2`, ecc.).

## 5. Multiplicity & effect size

Famiglia: 1 candidato (nessuno split direzionale) × 2 outcome inferenziali = **2 confronti**, BH-FDR q=0.10 (riusato). Soglia di materialita': **10% di differenza relativa** - stessa soglia e stessa filosofia gia' congelata in `minimum_evidence_gates.json` (`minimum_material_delta_p_default=0.10`), qui riespressa come rapporto invece che differenza di probabilita'.

## 6. Accesso ai dati

Autorizzata per un futuro run: **solo** `development_discovery`. `internal_validation`/`locked_validation`/`final_holdout` restano chiuse.

## 7. Regressione - 32/32 PASS

`test_seq0014_statistical_preregistration.py`: stato di blocco coerente, audit di contaminazione plausibile e coerente col base rate, nessun outcome direzionale riusato, famiglia inferenziale=2, soglie di dipendenza invariate da Phase 7.4A, **verifica statica che ne' questo script ne' il builder aprano mai `outcomes_v1.csv`**. **0 regressioni** sulle altre 12 suite Phase 7 (13 suite totali).

## Deliverables

`seq0014_statistical_preregistration_v1.json`, `build_seq0014_statistical_preregistration.py`, `test_seq0014_statistical_preregistration.py`. Nessun file contenente risultati di outcome.

---

**NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.** SEQ-0015 e SEQ-0009 restano chiuse, non riesaminate. **Discovery NON eseguita.**

**Prossimo passo (non autorizzato qui):** formalizzare una nuova structural spec con `control_pool_construction_policy` corretta per escludere controlli essi stessi in `LOW_INFORMATION_STATE` (estimand B), ri-eseguire il Sequence Structural Feasibility Gate su quella spec, e solo allora sbloccare questa preregistrazione.
