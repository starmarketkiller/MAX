# NEXUS - Phase 7.7B Strategy Readiness & Meta-Filter Gate

**Baseline:** `6ac26cc` (Phase 7.7A + Company Control Plane, merge senza conflitti). Separa formalmente **STRUCTURAL ELIGIBILITY** da **RESEARCH READINESS** per l'uso futuro di strategie in META_FILTER_RESEARCH. Nessun nuovo backtest, nessuna applicazione di MECH-23, nessuna modifica ai risultati storici.

**Conferma esplicita: NO NEW BACKTEST EXECUTED. NO EDGE DISCOVERY PERFORMED.**

---

## Il problema trovato

`strategy_meta_filter_eligibility_v1.json` (Phase 7.7A) mescolava due domande sotto un'unica etichetta `META_FILTER_ELIGIBLE`: "e' strutturalmente possibile?" e "e' scientificamente maturo farlo ora?". VOLATILITY_BREAKOUT_CONFIRMED e H006 erano entrambi `META_FILTER_ELIGIBLE` nonostante essere rispettivamente `HOLD_NEEDS_MORE_EVIDENCE` e `BORDERLINE/RETAIN_E2` - un dashboard futuro avrebbe potuto leggere "ELIGIBLE" come "pronto a testare", il che sarebbe stato sbagliato.

**Il vecchio artifact non e' stato modificato** (`strategy_meta_filter_eligibility_v1.json`, hash invariato) - la correzione vive in un nuovo artifact separato con cross-reference esplicito.

## I due assi, calcolati meccanicamente dagli stessi dati di Phase 7.7A

- **`meta_filter_structural_eligibility`** (`ELIGIBLE`/`NOT_ELIGIBLE`): richiede classificazione `FULL_STRATEGY_SPEC` **E** i campi-chiave del lifecycle_contract (entry+direction+almeno uno fra invalidation_stop/target_exit) **realmente estratti** in 7.7A - non dedotti dalla sola classificazione.
- **`meta_filter_research_readiness`** (`READY`/`NEEDS_MORE_EVIDENCE`/`BORDERLINE_LOW_PRIORITY`/`REFUTED_INAPPROPRIATE`/`EXECUTION_FAILED_INAPPROPRIATE`/`NOT_READY`): derivato esclusivamente dall'`evidence_verdict` gia' congelato - nessun nuovo giudizio statistico.

**Gate:** `META_FILTER_READY` richiede `structural=ELIGIBLE` **AND** `readiness=READY`. Nessuna promozione automatica da `FULL_STRATEGY_SPEC`.

## Risultati (7 candidati valutati)

| Candidato | Structural | Readiness | Gate |
|---|---|---|---|
| VOLATILITY_BREAKOUT_CONFIRMED | ELIGIBLE | NEEDS_MORE_EVIDENCE | ✗ |
| H006_LIQUIDITY_SWEEP_RECLAIM | ELIGIBLE | BORDERLINE_LOW_PRIORITY | ✗ |
| WICK_SWEEP_RECLAIM | NOT_ELIGIBLE (PARTIAL_STRATEGY) | EXECUTION_FAILED_INAPPROPRIATE | ✗ |
| H015_SAR_EXTERNAL_VALIDATION | ELIGIBLE | REFUTED_INAPPROPRIATE | ✗ |
| SAR_LIVE | NOT_ELIGIBLE (audit depth) | REFUTED_INAPPROPRIATE | ✗ |
| ADX_RSI | NOT_ELIGIBLE (audit depth) | REFUTED_INAPPROPRIATE | ✗ |
| BREAKOUT_ACC | NOT_ELIGIBLE (audit depth) | NOT_READY | ✗ |

**Conteggi:** 3/7 structurally eligible, **0/7 research-ready**, **0/7 pass il gate completo**, 7/7 bloccati. Nessun candidato e' oggi `META_FILTER_READY` - fatto onesto riportato esplicitamente, non un difetto della classificazione.

**SAR_LIVE, ADX_RSI, BREAKOUT_ACC risultano NOT_ELIGIBLE non per assenza di struttura reale, ma perche' Phase 7.7A non ne aveva estratto il lifecycle_contract completo** (limite di scope dichiarato allora) - distinto esplicitamente da WICK_SWEEP_RECLAIM (NOT_ELIGIBLE per classificazione `PARTIAL_STRATEGY` genuina). Un futuro deep-dive del codice MQL5 reale potrebbe promuoverli a ELIGIBLE senza cambiare l'evidenza empirica sottostante - segnalato come nuova incoerenza di governance (`STRUCTURAL_ELIGIBILITY_AUDIT_DEPTH_GAP`).

## Next required evidence per candidato

- **VOLATILITY_BREAKOUT_CONFIRMED**: serious 3Y backtest (campione attuale n=14/6 mesi troppo piccolo/concentrato).
- **H006**: CROSS_FEED_VALIDATION indipendente (E4) - priorita' bassa data la natura gia' borderline.
- **WICK_SWEEP_RECLAIM**: nessuna evidenza aggiuntiva sullo stesso design di esecuzione lo salverebbe.
- **H015/SAR_LIVE/ADX_RSI**: nessuna - refutati, richiederebbe una nuova identita' di design.
- **BREAKOUT_ACC**: trattamento statistico rigoroso (Wilson CI/dependence-aware), oggi solo R-multiple/PF informale.

## Regressione

67/67 PASS su questa suite. **0 regressioni** sulle altre 21 suite Phase 7 (22 totali). Verificato: `strategy_meta_filter_eligibility_v1.json` e `strategy_lifecycle_registry_v1.json` (Phase 7.7A) hash invariati.

## Deliverables

`strategy_meta_filter_gate_v1.json`, `strategy_meta_filter_gate_crossref_v1.json`, `build_strategy_meta_filter_gate.py`, `test_strategy_meta_filter_gate.py` - tutti in `server/research_scripts/phase7/phase7_7b/`. Nessuna modifica agli artifact Phase 7.7A.

---

**NO NEW BACKTEST EXECUTED. NO MECH-23 APPLIED. NO HISTORICAL RESULTS MODIFIED. NO EDGE DISCOVERY PERFORMED.**

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: 100%
VERSO DEMO: ~68%
██████▊░░░
QUANT:
Structural eligibility separata da
research readiness - 0/7 candidati
oggi meta-filter-ready
PROSSIMO:
Value of Information: quale evidenza
mancante (es. serious 3Y su
VOLATILITY_BREAKOUT_CONFIRMED) vale
di piu' del suo costo?
```

Nota: la parte di questo messaggio rivolta a Codex (integrazione del Company Control Plane) non e' stata eseguita in questa sessione - va inoltrata separatamente alla sessione Codex, che non e' raggiungibile da qui.
