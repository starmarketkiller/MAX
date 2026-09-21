# NEXUS - Phase 7.8C Serious 3Y Blocker Resolution & Run Authorization

**Baseline:** `26be386` (Phase 7.8B, 3 blocker `NOT_YET_JUSTIFIED`). Risolve i 3 blocker senza inventare numeri, corregge il naming fresh-window, definisce lo schema del PRE-RUN MANIFEST/SEAL. Nessun Serious 3Y eseguito, nessun outcome letto, nessuna optimization.

**Conferma esplicita: SERIOUS_3Y_NOT_EXECUTED. NO NEW OUTCOME DATA ACCESSED. NO PARAMETER OPTIMIZATION.**

---

## 1. Correzione di naming (annotazione, 7.8B non modificato)

"Serious 3Y" resta il nome del test, ma il verdetto primario copre **solo `PRIMARY_FRESH_VERDICT_WINDOW` (~2.5 anni)** - `PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW` (~6 mesi) e' diagnostica, mai fusa nel verdetto. Vietate esplicitamente etichette come "3Y OOS" o "full 3-year fresh validation".

## 2. Materiality blocker → RESOLVED

**Non** inventato un +0.05R/+0.10R. Adottato:
```
executable_edge_gate = CI95(expectancy_R, BROKER_BASELINE).lower_bound > 0
                        AND expectancy_R(STRESS) > 0
numeric_materiality_threshold = NOT_REQUIRED_AT_THIS_STAGE
```
Supportato da `cost_model_integration.json`'s framework a due stati gia' esistente (`STRUCTURAL_EDGE` vs `EXECUTABLE_EDGE_AFTER_COST`, quest'ultimo definito come esistenza-dopo-costo, non magnitudo minima). Classificato onestamente **`PARTIALLY_SUPPORTED_BY_EXISTING_POLICY_STRUCTURE_ADAPTED`** (un'estensione coerente, non una conseguenza gia' scritta parola-per-parola). La magnitudo (`expectancy_R`) resta **sempre riportata** (preserva lo spirito di `effect_size_first_policy.json`) - la soglia economica di allocazione capitale e' rimandata a `PORTFOLIO_RISK`, mai stabilita qui.

## 3. Temporal stability blocker → RESOLVED (regola scale-free)

- Almeno 2 dei 3 segmenti annuali con `expectancy_R >= 0` (segno, non magnitudo)
- Nessun singolo segmento spiega >100% del risultato netto mentre tutti gli altri combinati sono negativi (rapporto fra quantita' omogenee, mai un valore R assoluto)

Entrambi i criteri sono **confronti di segno e rapporti**, non richiedono calibrazione della scala R di questa strategia specifica - genuinamente scale-free.

## 4. Same-bar SL/TP blocker → RESOLVED (sintesi, non pura A né pura B)

**`REAL_TICK_REQUIRED_FOR_PRIMARY_VERDICT`** - se l'ordine reale dei tick e' disponibile, usato senza assunzioni. Se non risolvibile: flag esplicito `EXECUTION_ORDER_UNRESOLVED` per quel trade (mai TP-first o SL-first assunto silenziosamente - stesso principio gia' in Failure Memory, pattern `DATA_COVERAGE_GAP`).

**Sintesi adottata** (ne' pura esclusione ne' puro blocco totale): il punto stimato primario usa solo i trade risolti; un **bracket obbligatorio** [worst_case: tutti SL-first, best_case: tutti TP-first] viene sempre calcolato per i trade ambigui. Se il bracket non cambia la classificazione PASS/BORDERLINE/FAIL, il verdetto primario resta valido. Se la cambia: nuovo stato esplicito **`EXECUTION_ORDER_UNRESOLVED_BLOCKS_VERDICT`** - mai risolto scegliendo arbitrariamente un lato.

## 5. PRE-RUN MANIFEST/SEAL - schema definito, artifact NON creato

16 campi obbligatori (timestamp esatti, finestre fresh/observed, timezone, symbol/TF, tick coverage, hash dataset/strategy/cost-model/prereg/commit). Regola procedurale: creato **DOPO** la sincronizzazione dati, **PRIMA** di qualunque statistica - **nessun risultato puo' comparire nel manifest**. Non creato in questa fase (nessun accesso dati MT5 live in questa sessione di ricerca).

## 6. Run authorization

Tutti e 3 i blocker: `RESOLVED`. **Verdetto: `READY_FOR_PRE_RUN_SEAL`** - esplicitamente **non** `READY_TO_RUN` (richiederebbe il manifest reale, un passo procedurale successivo non ancora compiuto).

## 7. Final gate chain

```
7.8C_BLOCKER_RESOLUTION → PRE_RUN_MANIFEST_SEAL → VERIFY_SEAL → EXECUTE_SERIOUS_VALIDATION → IMMUTABLE_RESULT_ARTIFACT
```

## Regressione

58/58 PASS su questa suite. **0 regressioni** sulle altre 26 suite Phase 7 (27 totali). Verificato: `volatility_breakout_serious_3y_prereg_v1.json` (7.8B) e `volatility_breakout_voi_contract_v1.json` (7.8A) hash invariati.

## Deliverables

`volatility_breakout_serious_3y_run_authorization_v1.json`, `build_volatility_breakout_run_authorization.py`, `test_volatility_breakout_run_authorization.py` - tutti in `server/research_scripts/phase7/phase7_8c/`. Nessuna modifica retroattiva.

---

**SERIOUS_3Y_NOT_EXECUTED. NO NEW OUTCOME DATA ACCESSED. NO PARAMETER OPTIMIZATION. NO EDGE DISCOVERY PERFORMED.**

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: 100%
VERSO DEMO: ~68%
██████▊░░░
FASE ATTUALE:
3 blocker risolti senza numeri
inventati - protocollo completo
VERDETTO:
READY_FOR_PRE_RUN_SEAL
(non READY_TO_RUN)
PROSSIMO:
sincronizzare dati MT5 reali
→ creare PRE-RUN MANIFEST
→ verificare seal
→ RUN
```

Il protocollo e' ora completamente specificato senza un solo numero inventato. Il prossimo passo (creazione del manifest con date/hash reali) richiede accesso dati live, fuori dalla portata di questa sessione di ricerca.
