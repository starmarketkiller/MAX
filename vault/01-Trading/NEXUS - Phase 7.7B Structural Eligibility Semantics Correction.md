# NEXUS - Phase 7.7B Structural Eligibility Semantics Correction

**Baseline:** `72bcbf2` (Phase 7.7B gate). Corregge una conflazione semantica trovata dal reviewer: `NOT_ELIGIBLE` era usato sia per "assenza strutturale verificata" sia per "audit non abbastanza approfondito" - due cose diverse. Nessun nuovo deep-dive del codice, nessun backtest, nessuna applicazione di MECH-23 - solo rilettura del testo gia' scritto in Phase 7.7A.

**Conferma esplicita: NO NEW BACKTEST EXECUTED. NO EDGE DISCOVERY PERFORMED.**

---

## Il problema trovato

Phase 7.7B affermava per WICK_SWEEP_RECLAIM: *"manca un componente reale del lifecycle, non solo un limite di questo o quell'audit"*. Ma la fonte reale (Phase 7.7A, `classification_rationale`) dice l'esatto opposto: *"classificato PARTIAL non per assenza di formalizzazione ma perche' questo audit non ha approfondito il contratto completo"*. 7.7B aveva trasformato silenziosamente `UNKNOWN_DUE_TO_AUDIT_DEPTH` in `KNOWN_STRUCTURAL_ABSENCE` - lo stesso errore gia' correttamente evitato per SAR_LIVE/ADX_RSI/BREAKOUT_ACC, ma non applicato coerentemente a WICK.

## I tre stati (non due)

- **`STRUCTURALLY_ELIGIBLE`** - lifecycle sufficientemente verificato nella fonte (campi realmente estratti).
- **`STRUCTURALLY_INELIGIBLE`** - esiste una dichiarazione ESPLICITA e positiva nella fonte che un componente e' realmente assente.
- **`STRUCTURAL_STATUS_UNVERIFIED`** - campi null perche' l'audit sorgente non ha approfondito, MAI perche' un'assenza reale e' stata verificata.

**Tassonomia generale del "missing field"** (riusabile dal futuro Company Control Plane): `source-null` (assenza reale verificata), `audit-not-extracted` (limite di audit → sempre `UNVERIFIED`), `explicitly-absent` (unica base per `INELIGIBLE`).

**Regola:** `MISSING_FIELD != VERIFIED_ABSENCE` - un campo null implica `UNVERIFIED` per default, mai `INELIGIBLE` senza una dichiarazione positiva.

## Risultato della riclassificazione (7 candidati, testo di 7.7A riletto, nessuna nuova informazione)

| Candidato | Prima (7.7B) | Dopo (corretto) |
|---|---|---|
| VOLATILITY_BREAKOUT_CONFIRMED | ELIGIBLE | `STRUCTURALLY_ELIGIBLE` (rinominato, invariato) |
| H006_LIQUIDITY_SWEEP_RECLAIM | ELIGIBLE | `STRUCTURALLY_ELIGIBLE` (rinominato, invariato) |
| H015_SAR_EXTERNAL_VALIDATION | ELIGIBLE | `STRUCTURALLY_ELIGIBLE` (rinominato, invariato) |
| **WICK_SWEEP_RECLAIM** | NOT_ELIGIBLE | **`STRUCTURAL_STATUS_UNVERIFIED`** (corretto) |
| **SAR_LIVE** | NOT_ELIGIBLE | **`STRUCTURAL_STATUS_UNVERIFIED`** (gia' coerente, confermato) |
| **ADX_RSI** | NOT_ELIGIBLE | **`STRUCTURAL_STATUS_UNVERIFIED`** (gia' coerente, confermato) |
| **BREAKOUT_ACC** | NOT_ELIGIBLE | **`STRUCTURAL_STATUS_UNVERIFIED`** (gia' coerente, confermato) |

**0 casi di `STRUCTURALLY_INELIGIBLE`** in questo registro - nessuna fonte contiene una dichiarazione esplicita di assenza per nessuno dei 7 candidati (dichiarato, non assunto).

## Research readiness: invariata (verificato)

`EXECUTION_FAILED_INAPPROPRIATE` (WICK), `REFUTED_INAPPROPRIATE` (H015/SAR_LIVE/ADX_RSI), `NOT_READY` (BREAKOUT_ACC), `NEEDS_MORE_EVIDENCE` (VOLBRK), `BORDERLINE_LOW_PRIORITY` (H006) - **identici a 7.7B, nessun ricalcolo**. Coesistenza confermata senza contraddizione: es. SAR_LIVE = `STRUCTURAL_STATUS_UNVERIFIED` + `REFUTED_INAPPROPRIATE`.

## Gate: invariato

`META_FILTER_READY` count: **0 prima, 0 dopo** - `UNVERIFIED` fallisce chiuso esattamente come `NOT_ELIGIBLE` faceva. **Nessun candidato promosso da questa correzione** - il punto era la correttezza semantica, non il risultato operativo.

## Proposta concettuale (non implementata): terzo asse futuro

`META_FILTER_EXECUTION_READINESS` - WICK_SWEEP_RECLAIM ha gia' dimostrato che struttura+evidenza non bastano (shadow PF=5.80 → reale PF=0.78-0.80). Pipeline completa: `STRUCTURE → RESEARCH EVIDENCE → EXECUTION REALISM → DEPLOYABILITY`, con gate distinti `META_FILTER_READY` / `EXECUTION_READY` / `DEPLOYABLE`. Non implementato ora - solo annotato per il futuro.

## Regressione

69/69 PASS su questa suite. **0 regressioni** sulle altre 22 suite Phase 7 (23 totali). Verificato: `strategy_lifecycle_registry_v1.json` (7.7A) e `strategy_meta_filter_gate_v1.json` (7.7B) hash invariati.

## Deliverables

`structural_eligibility_semantics_correction_v1.json`, `build_structural_eligibility_semantics_correction.py`, `test_structural_eligibility_semantics_correction.py` - tutti in `server/research_scripts/phase7/phase7_7b/`. Nessuna modifica retroattiva a 7.7A/7.7B.

---

**NO NEW BACKTEST EXECUTED. NO MECH-23 APPLIED. NO EDGE DISCOVERY PERFORMED.**

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: 100%
VERSO DEMO: ~68%
██████▊░░░
PHASE 7.7B:
bug semantico corretto -
UNKNOWN != MISSING
META-FILTER READY: 0/7 (invariato)
PROSSIMO:
scegliere il prossimo test
per Value of Information
(candidato naturale:
VOLATILITY_BREAKOUT_CONFIRMED,
structural=ELIGIBLE,
readiness=NEEDS_MORE_EVIDENCE,
blocker pulito: Serious 3Y)
```

Nota: la parte del messaggio precedente rivolta a Codex resta fuori dalla portata di questa sessione.
