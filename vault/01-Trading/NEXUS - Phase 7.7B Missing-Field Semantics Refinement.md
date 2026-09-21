# NEXUS - Phase 7.7B Missing-Field Semantics Refinement (two-axis)

**Baseline:** `4743ce0` (Phase 7.7B, correzione a 3 stati). Micro-audit: separa `FIELD_KNOWLEDGE` (perche' un campo e' vuoto) da `REQUIREMENT_ROLE` (se quel campo era necessario) - la correzione precedente aveva gia' distinto audit-depth da assenza verificata, ma mescolava ancora "assenza verificata" con "quindi ineligible". Nessun backtest, nessuna modifica retroattiva.

**Conferma esplicita: NO NEW BACKTEST EXECUTED. NO EDGE DISCOVERY PERFORMED.**

---

## Il problema trovato

La tassonomia a 3 stati (`4743ce0`) faceva bene a distinguere `audit-not-extracted` da `explicitly-absent`, ma implicava che **qualunque** assenza verificata giustificasse `STRUCTURALLY_INELIGIBLE`. Questo confonde due domande: *perche'* il campo e' vuoto, e se quel campo fosse *davvero necessario*. Test-case del reviewer: H006 non ha un `invalidation_stop` separato - non perche' l'audit non l'abbia cercato, ma perche' la sua semantica di outcome a barriera (`P(+1.0xATR before -1.0xATR)`) gia' lo copre.

## I due assi

- **`FIELD_KNOWLEDGE`**: `VERIFIED_VALUE` / `VERIFIED_ABSENCE` / `NOT_EXTRACTED`
- **`REQUIREMENT_ROLE`**: `REQUIRED` / `NOT_REQUIRED_BY_DESIGN` / `SATISFIED_BY_EQUIVALENT_MECHANISM`

**Regola:** solo `VERIFIED_ABSENCE + REQUIRED` → `STRUCTURALLY_INELIGIBLE`. `VERIFIED_ABSENCE + (NOT_REQUIRED_BY_DESIGN | SATISFIED_BY_EQUIVALENT_MECHANISM)` → non implica ineligibility. `NOT_EXTRACTED` (qualunque ruolo) → sempre `STRUCTURAL_STATUS_UNVERIFIED` (non possiamo giudicare il ruolo di un campo non letto).

## Test-case H006 (verificato direttamente contro `H006_frozen_spec.json`)

| | |
|---|---|
| Campo | `invalidation_stop` |
| `FIELD_KNOWLEDGE` | `VERIFIED_ABSENCE` - nessuna chiave `invalidation`/`stop` esiste in nessuna delle 18 chiavi reali dello schema; `primary_outcome.definition` dichiara esplicitamente "nessuna gestione dinamica" |
| `REQUIREMENT_ROLE` | `SATISFIED_BY_EQUIVALENT_MECHANISM` - il lato -1.0xATR della barriera `P(+1.0xATR before -1.0xATR)` E' funzionalmente l'invalidazione |
| Implica ineligibility? | **No** |

## Risultato su tutti e 7 i candidati

**0 cambiamenti di stato** rispetto alla correzione precedente - i 3 `STRUCTURALLY_ELIGIBLE` (VOLATILITY_BREAKOUT_CONFIRMED, H006, H015-SAR) restano tali (ora con una giustificazione piu' rigorosa per H006), i 4 `STRUCTURAL_STATUS_UNVERIFIED` (WICK_SWEEP_RECLAIM, SAR_LIVE, ADX_RSI, BREAKOUT_ACC) restano tali (i loro campi core sono `NOT_EXTRACTED`, mai `VERIFIED_ABSENCE`). **0 casi di `STRUCTURALLY_INELIGIBLE`** trovati in questo registro - nessuna fonte fra i 7 candidati dichiara un'assenza verificata di un campo REQUIRED senza un meccanismo equivalente.

Research readiness confermata identica a 7.7B. Gate: **0/7 prima, 0/7 dopo** - nessun cambiamento operativo, solo maggiore rigore semantico.

## Regressione

59/59 PASS su questa suite. **0 regressioni** sulle altre 23 suite Phase 7 (24 totali). Verificato: `strategy_lifecycle_registry_v1.json`, `strategy_meta_filter_gate_v1.json`, `structural_eligibility_semantics_correction_v1.json` tutti hash-invariati.

## Deliverables

`missing_field_semantics_refinement_v1.json`, `build_missing_field_semantics_refinement.py`, `test_missing_field_semantics_refinement.py` - tutti in `server/research_scripts/phase7/phase7_7b/`. Nessuna modifica retroattiva.

---

**NO NEW BACKTEST EXECUTED. NO MECH-23 APPLIED. NO EDGE DISCOVERY PERFORMED.**

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: 100%
VERSO DEMO: ~68%
██████▊░░░
META-FILTER READY: 0/7 (invariato)
CORREZIONE PRINCIPALE:
UNKNOWN != ABSENT (7.7B)
RAFFINAZIONE:
ABSENT != NECESSARILY REQUIRED (questa fase)
DOPO:
Value of Information
→ VOLATILITY_BREAKOUT_CONFIRMED
→ Serious 3Y e' davvero il prossimo test migliore?
```

Il registro di strategia e' ora, per la prima volta, semanticamente completo su tutti e tre gli assi che contano: cosa sappiamo, perche' non lo sappiamo (quando non lo sappiamo), e se conta davvero.
