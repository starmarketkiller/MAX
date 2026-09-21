# NEXUS - Phase 7.8B VOLATILITY_BREAKOUT_CONFIRMED Serious 3Y Preregistration

**Baseline:** `b8c598f` (Phase 7.8A, verdetto `SERIOUS_3Y_IS_NEXT_BEST_EXPERIMENT`). Pre-registra il protocollo ESATTO del Serious 3Y prima di autorizzarne l'esecuzione. Nessun backtest eseguito, nessun nuovo outcome letto, nessun parametro della strategia modificato, nessuna optimization, nessuna applicazione di MECH-23.

**Conferma esplicita: SERIOUS_3Y_NOT_EXECUTED. NO NEW OUTCOME DATA ACCESSED. NO PARAMETER OPTIMIZATION.**

---

## 1. Correzione evidence-dependence (annotazione, 7.8A non modificato)

Le 4 letture concordi (discovery/validation/full-backtest/fast-structural) **non sono prove statisticamente indipendenti** - condividono strategia, lineage e in parte dati. Corretto: `evidence_concordance=POSITIVE`, `evidence_independence=NOT_ESTABLISHED`. **Non ribalta il verdetto VoI** - anzi rafforza la necessita' di un test genuinamente fresco.

## 2. Identita' della strategia congelata

Commit `f035d30` (Strategy Foundry Phase 3). Detector, entry, direzione, range lookback (N=20), conferma volatilita' (1.0xATR, gia' `DOMAIN_DEFINED` in `threshold_policy.json`), invalidazione (lato opposto del range), R definition, target (esattamente 1xR), timeout (40 barre, chiusura a prezzo reale - **mai un valore R fisso**), nessuna gestione dinamica. **Nessun parametro puo' cambiare dopo questo commit.**

## 3. Dataset e periodo

Simbolo/TF: XAUUSD H4. Regola di selezione finestra: ultimi 3 anni continui (stessa convenzione gia' usata per SAR/MACD Serious 3Y, commit `e557b22`) - **date esatte non fabbricate qui** (richiede sincronizzazione MT5 live al momento del run).

**Marcatura esplicita:**
- Ultimi 6 mesi (2026-03/2026-09): **`PREVIOUSLY_OBSERVED`** (identici al fast-structural gia' fatto) - esclusi dal verdetto primario, riportati solo come replica diagnostica.
- ~2.5 anni precedenti: **`FRESH_FOR_THIS_EXACT_COMBINED_STRATEGY`** - MAI questa combinazione esatta, ma con un caveat onesto: il mercato sottostante in quella finestra e' gia' stato usato per testare i componenti raw separati (BREAKOUT=H001, VOLATILITY_EXPANSION=H008, entrambi REFUTED in Phase 5.5).

## 4. Execution contract

Fill reale MT5 tick-driven, nessuna idealizzazione shadow (Failure Memory: `SHADOW_EXECUTION_ASSUMPTION`). **Un genuino gap dichiarato**: `same_bar_sl_tp_ambiguity_rule = NOT_YET_JUSTIFIED` se il tick model reale non fosse disponibile per l'intero periodo.

## 5. Scenari di costo (riusati identici, non re-inventati)

`ZERO_COST` (diagnostico) / **`BROKER_BASELINE`** (primario per il verdetto - spread=0.54 pip, commission=0.0, slippage=0.10 pip, da `cost_model_integration.json`) / `CONSERVATIVE` (x1.5, stress) / `STRESS` (x2.0, stress).

## 6. Endpoint primario

**`expectancy_R`** (media R-multiple per trade, scenario BROKER_BASELINE, porzione FRESH) - stessa metrica gia' usata per l'intera evidenza pregressa. Metodo: `moving_block_bootstrap` (gia' ammesso in `statistical_methods_policy.json`, non il metodo superato). Diagnostiche secondarie (win rate, PF, payoff ratio, DD, max consecutive losses) **non possono mai sostituire il primario**.

## 7. Soglie esatte - dove riusabili, riusate; dove no, dichiarate apertamente

| Criterio | Valore | Fonte |
|---|---|---|
| Campione nominale minimo | 30 | `minimum_evidence_gates.json` (riusato) |
| Campione effettivo minimo | 20 | `minimum_evidence_gates.json` (riusato) |
| Segno | PF>1.0 AND expectancy_R>0 | DOMAIN_DEFINED (breakeven matematico) |
| **Materialita' oltre breakeven** | **`NOT_YET_JUSTIFIED`** | Nessun equivalente canonico per scala R-multiple (il default 0.10 e' su scala probabilita') |
| Incertezza | CI95 bootstrap esclude 0 | Adattato da `uncertainty_requirement` |
| **Stabilita' temporale** | **`NOT_YET_JUSTIFIED`** | Il precedente SAR/MACD ha usato giudizio qualitativo, mai un numero |
| Robustezza ai costi | expectancy_R>0 anche sotto STRESS | DOMAIN_DEFINED |

**`run_authorization_status = PARTIALLY_BLOCKED`** - 3 blocker (materialita', stabilita' temporale, ambiguita' same-bar SL/TP) richiedono una decisione umana **prima** del run, non dopo aver visto un risultato borderline.

## 8. Campione effettivo

Nessun ESS inventato - se non stimabile con i metodi gia' ammessi, fallback esplicito a solo n nominale con flag `DEPENDENCE_ADJUSTMENT_NOT_APPLIED`.

## 9. Asimmetria direzionale

Diagnostica pre-registrata (axis riusato da `stability_matrix_policy.json`). **Vietato esplicitamente**: "overall FAILS → keep only SELL" - richiederebbe una nuova hypothesis identity, mai un rescue nello stesso test. Precedente diretto: SAR (SELL PF=0.84/92 trade → BORDERLINE), MACD (SELL PF=0.13 nell'IS → FAIL).

## 10. Stabilita' temporale

Segmentazione annuale + meta' (stessa di SAR/MACD), OOS check sull'ultimo ~22.5% della finestra FRESH. Criterio di concentrazione cita esplicitamente il pattern gia' osservato (2 mesi su 5 = quasi tutto il profitto fast-structural) - **non una sorpresa da scoprire al 3Y, un rischio gia' noto**.

## 11. No-rescue clause

7 azioni esplicitamente vietate dopo aver visto risultati (tuning parametri, filtri di sessione/regime, eliminazione direzione, aggiustamento SL/TP, **aggiustamento di QUALUNQUE soglia incluse quelle NOT_YET_JUSTIFIED**, rescue di sottogruppo post-hoc). Precedente: MACD FAIL "documentato, non corretto."

## 12-13. Result branches e next gate

`PASS→ADVANCE_TO_NEXT_VALIDATION_GATE` / `BORDERLINE→HOLD_NEEDS_MORE_EVIDENCE` / `FAIL→ARCHIVE_CURRENT_DESIGN` / `INSUFFICIENT_SAMPLE→HOLD`. **Nessun branch porta a LIVE.** Next gate dopo PASS deciso ORA: **`EXECUTION_VALIDATION`** (non demo diretto, non cross-feed) - esattamente lo stage che ha refutato WICK_SWEEP_RECLAIM nonostante un'ipotesi "STRONGLY SUPPORTED".

## Regressione

79/79 PASS su questa suite. **0 regressioni** sulle altre 25 suite Phase 7 (26 totali). Verificato: `volatility_breakout_voi_contract_v1.json` (7.8A) hash invariato.

## Deliverables

`volatility_breakout_serious_3y_prereg_v1.json`, `build_volatility_breakout_serious_3y_prereg.py`, `test_volatility_breakout_serious_3y_prereg.py` - tutti in `server/research_scripts/phase7/phase7_8b/`. Nessuna modifica retroattiva.

---

**SERIOUS_3Y_NOT_EXECUTED. NO NEW OUTCOME DATA ACCESSED. NO PARAMETER OPTIMIZATION. NO EDGE DISCOVERY PERFORMED.**

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: 100%
VERSO DEMO: ~68%
██████▊░░░
FASE ATTUALE:
Protocollo Serious 3Y pre-registrato -
PARTIALLY_BLOCKED (3 soglie non
ancora giustificabili senza
decisione umana)
PROSSIMO SBLOCCO:
risolvere i 3 blocker
(materialita', stabilita' temporale,
same-bar SL/TP) → poi RUN
```

Il protocollo e' pronto per l'esecuzione tranne per tre soglie che richiedono un giudizio di dominio non ancora dichiarato altrove nel progetto - fissarle ORA, prima del risultato, e' esattamente il punto di questa fase.
