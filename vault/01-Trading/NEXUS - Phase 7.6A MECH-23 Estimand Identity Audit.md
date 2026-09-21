# NEXUS - Phase 7.6A MECH-23 Estimand Identity Audit

**Baseline:** `6b0c916` (preregistrazione SEQ-0014, bloccata sulla variante di control pool). Audit **concettuale** - nessun outcome letto, nessuna discovery, nessun control pool modificato, nessuna nuova structural spec creata.

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.**

---

## Il problema trovato

Il claim MECH-23 originale (registry, **Phase 7.2**, scritto mesi prima di qualunque test strutturale) e' testuale e verbatim:

> *"Se i setup direzionali generati durante lo stato 'choppy' non mostrassero un tasso di fallimento/rumore superiore rispetto a quelli generati in stato 'trending', il claim sarebbe falso."*

L'unita' di analisi qui e' un **setup direzionale di un altro meccanismo**, e l'outcome e' la **sua performance/fallimento**. La preregistrazione congelata in `6b0c916` studia invece il comportamento del **prezzo dopo l'ingresso nello stato stesso** - un oggetto diverso.

## Classificazione formale: `RELATED_BUT_DISTINCT`

| | Esperimento state-entry (gia' congelato) | Claim MECH-23 originale |
|---|---|---|
| **Nome** | `SEQ-0014A` - `LOW_INFORMATION_STATE_ENTRY_PHENOMENON` | `SEQ-0014B` - `LOW_INFORMATION_STATE_FILTER_UTILITY` |
| **Unita' di analisi** | una barra H4 (lo state-entry event) | un setup direzionale (di un altro meccanismo) |
| **Esposizione** | ingresso nello stato vs barra comparabile | regime CHOPPY vs TRENDING al momento del setup |
| **Outcome** | range/spostamento/path-efficiency futuri del **prezzo** | fallimento/rumore del **setup stesso** |
| **Domanda** | "il mercato si comporta diversamente dopo un ingresso in chop?" | "i setup direzionali falliscono di piu' se nascono in chop?" |

**Non equivalenti** (verificato esplicitamente, non assunto): "state-entry vs barra non-choppy" non implica ne' esclude "setup direzionali in choppy vs trending falliscono diversamente" - proprieta' logicamente indipendenti. **Non incompatibili**: condividono la stessa classificazione di stato sottostante (`directional_efficiency` in tercile LOW, gia' congelata in Phase 7.5C) come fondamento comune.

## Il lavoro gia' fatto resta valido - correttamente delimitato

```
189 (EVENT_VIEW) -> 128 (EPISODE_VIEW) -> 49 (INDEPENDENT_VIEW), matching 49/49, FEASIBLE
```

Questo risultato (Phase 7.5C, `844f852`) **resta valido e invariato** - ma **solo** come esito strutturale del fenomeno state-entry (`SEQ-0014A`). Non va reinterpretato, ora o in futuro, come evidenza a favore del claim filter-utility (`SEQ-0014B`), che e' un esperimento distinto, mai formalizzato.

## SEQ-0014B: cosa manca (nessuna risposta inventata)

`NEEDS_DIRECTIONAL_SETUP_POPULATION_SPECIFICATION` - 5 domande aperte, nessuna risolta arbitrariamente in questo audit:

1. Quale popolazione di "setup direzionali"? (il progetto ha gia' 6 famiglie candidate in `build_events.py`/`build_events_p71.py` - BREAKOUT, DISPLACEMENT, VOLATILITY_EXPANSION, PULLBACK, COMPRESSION_RELEASE, SWEEP - elencate come inventario, non come scelta).
2. Come si opera zionalizza "TRENDING" (regime complementare)? Il terzile HIGH di `directional_efficiency` e' un candidato naturale, non ancora congelato.
3. Quale entry/trigger identifica il momento t del setup?
4. Quale outcome operazionalizza "fallimento/rumore"? (`REVERSAL_PROBABILITY`, `MAE`, le famiglie `P_PLUS_*ATR` sono gia' nel vocabolario, tutte compatibili con un setup CON direzione propria - a differenza di SEQ-0014A che e' `NON_DIRECTIONAL`).
5. Quale contrasto accoppiato (matched su cosa)?

Richiederebbe una futura fase dedicata, con formalizzazione minima e freeze ex-ante - stesso workflow gia' rispettato per SEQ-0009/SEQ-0014A.

## Correzione di nomenclatura (per evitare confusione)

La preregistrazione precedente (`6b0c916`) usava "estimand A/B" per due **varianti di control pool** *all'interno* dello stesso esperimento state-entry. Questo audit introduce SEQ-0014A/SEQ-0014B per due **esperimenti diversi**. Per chiarezza, le varianti di control pool sono rinominate: `CONTROL_POOL_VARIANT_GENERIC` (ex "estimand A") e `CONTROL_POOL_VARIANT_NON_LOW_INFO` (ex "estimand B") - nessun cambiamento di sostanza, solo di etichetta.

## Outcome naming audit

`REALIZED_VOLATILITY_AFTER_SETUP` (ID di sistema, gia' congelato in `outcome_surface_v3.py`) e' definito nella preregistrazione come `(max(high[t+1..t+20])-min(low[t+1..t+20]))/ATR_t` - metricamente un **range futuro ATR-normalizzato** (`FORWARD_RANGE_ATR`), non una volatilita' realizzata in senso statistico classico. **L'ID di sistema resta invariato** (nessuna rinominazione globale, per istruzione esplicita) - ma in ogni report scientifico futuro va nominato esplicitamente `FORWARD_RANGE_ATR (ID legacy: REALIZED_VOLATILITY_AFTER_SETUP)` per evitare ambiguita'.

## Stato aggiornato

| | |
|---|---|
| **SEQ0014A_STATUS** | `STRUCTURALLY_FEASIBLE_PREREGISTRATION_BLOCKED_ON_CONTROL_POOL_VARIANT` |
| **MECH23_FILTER_CLAIM_STATUS** | `NEEDS_DIRECTIONAL_SETUP_POPULATION_SPECIFICATION` |
| **discovery_authorized** | `false` per entrambi |

## Regressione - 32/32 PASS

`test_seq0014_estimand_identity_audit.py`: citazione verbatim della fonte canonica, non-equivalenza verificata esplicitamente, scoping del risultato strutturale, nessuna risposta inventata per SEQ-0014B, nessuna rinominazione dell'ID di outcome, **conferma che ne' il frozen structural spec ne' la preregistrazione precedente sono stati toccati** (nessun diff). **0 regressioni** sulle altre 13 suite Phase 7 (14 totali).

## Deliverables

`seq0014_estimand_identity_audit_v1.json`, `build_seq0014_estimand_identity_audit.py`, `test_seq0014_estimand_identity_audit.py`. Nessuna modifica a `seq0014_frozen_structural_spec_v1.json` ne' a `seq0014_statistical_preregistration_v1.json`.

---

**NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.** SEQ-0015 e SEQ-0009 restano chiuse. Discovery non autorizzata per nessuno dei due esperimenti.

**Progresso verso demo (invariato, come richiesto): ~68%.** Prima candidate strutturalmente FEASIBLE, ma identita' dell'estimand ora esplicitamente chiarita - non alzato finche' non esiste una candidate che superi sia la struttura sia la coerenza scientifica del claim.
