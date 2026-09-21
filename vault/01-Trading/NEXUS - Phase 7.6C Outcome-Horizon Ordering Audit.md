# NEXUS - Phase 7.6C Outcome-Horizon Ordering Audit

**Baseline:** `80e7cbc124e40c61a9f0d28a31dd3c6d2e1a5fc3`. Audit di **sequencing metodologico**, non un rescue di SEQ-0014B: nessun outcome letto, nessun orizzonte alternativo ispezionato/calcolato, nessuna modifica ai frozen artifact (`6c0d3f6` spec, `80e7cbc` result - verificati byte-identici via hash).

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.**

---

## Il problema trovato dal reviewer

`natural_horizon=40`/`outcome_overlap_embargo_bars=39` sono stati congelati nello SPEC COMMIT `6c0d3f6` **prima** che SEQ-0014B avesse un primary outcome scelto. Il collasso cross-family 210→11 (RESULT COMMIT `80e7cbc`) dipende direttamente da quell'embargo. Ordine corretto sarebbe: outcome scientifico → orizzonte naturale dell'outcome → embargo derivato → geometria strutturale. Quello eseguito e' stato: orizzonte convenzionale (40) → geometria → (futura) scelta dell'outcome.

## Classificazione di horizon=40: `PROJECT_CONVENTION`

Tre opzioni valutate esplicitamente:

| Opzione | Verdetto | Motivazione |
|---|---|---|
| **A. MECHANISM_DERIVED** | Respinta | Solo SWEEP ha una derivazione meccanica indipendente di un orizzonte (Phase 7.5B, per il claim SWEEP-reversal) - ma quella derivazione era per un claim diverso, non per SEQ-0014B. Le altre 5 famiglie non hanno mai avuto una derivazione di orizzonte indipendente in questo progetto. |
| **B. OUTCOME_DERIVED** | Respinta | Impossibile per costruzione: nessun primary outcome era scelto per SEQ-0014B al momento del freeze (verificato contro `fb52168`/`seq0014b_setup_population_spec_v1.json` - nessuna chiave `primary_outcome`). Anche il vocabolario stesso degli outcome candidati (`outcome_surface_v3.py`) non porta un orizzonte in barre incorporato - e' definito solo a livello di tipo (barriera di prezzo/statistica descrittiva). |
| **C. PROJECT_CONVENTION** | **Confermata** | Il valore e' stato riusato dalla convenzione generale di progetto per meccanismi reversal/continuation su H4, motivato dalla necessita' pratica di una soglia di embargo UNICA per rendere ben definito il declustering cross-family - non da una derivazione indipendente per il claim specifico di SEQ-0014B. |

**Evidenza di supporto:** all'interno dello stesso progetto, esperimenti diversi sullo stesso substrato di regime hanno gia' usato orizzonti diversi - SEQ-0014A (state-entry) usa `natural_horizon=20`, SEQ-0009 (sweep-reversal) usa `natural_horizon=40`. L'orizzonte non e' quindi una costante universale derivabile meccanicamente per qualunque nuovo claim: e' scelto per esperimento, in funzione del claim/outcome specifico.

## Correzione di scope (il punto centrale di questo audit)

Il verdetto `NOT_TESTABLE_WITH_FROZEN_SETUP_POPULATION` va **esplicitamente delimitato**:

```
SEQ-0014B_DESIGN_V1:
  setup population:        fb52168 (6 famiglie, pooled stratificato)
  natural_horizon:          40
  outcome_overlap_embargo:  39
  matching contract:        volatility_state_pre_setup, k=5, min_control_count=20
  → NOT_TESTABLE_WITH_FROZEN_SETUP_POPULATION
```

**Non** a: "MECH-23 (il claim filter-utility originale) e' impossibile da testare in assoluto." Un futuro DESIGN_V2 con un outcome scelto ex-ante e un orizzonte derivato indipendentemente da quell'outcome resta una domanda aperta, non preclusa da questo risultato.

## Regola di framework proposta (nessuna nuova infrastruttura costruita)

> `if dependence geometry depends on outcome horizon: outcome class + natural horizon must be frozen before final structural feasibility verdict`

Nuova etichetta di risultato proposta per futuri preflight: **`HORIZON_CONDITIONAL_STRUCTURAL_RESULT`** - un verdetto calcolato prima che l'outcome (e quindi il suo orizzonte naturale) sia stato scelto ex-ante non e' universale, resta valido solo per l'identita' di design con cui e' stato calcolato. Applicazione retroattiva dichiarata qui (senza modificare l'artifact originale, per disciplina di cronologia dei commit): il RESULT COMMIT `80e7cbc` va inteso come un `HORIZON_CONDITIONAL_STRUCTURAL_RESULT` scoped a DESIGN_V1.

## Requisiti per un futuro DESIGN_V2 (nessuna esplorazione ammessa ora)

1. Primary outcome scelto EX-ANTE, prima di qualunque nuova geometria.
2. Orizzonte con giustificazione meccanica INDIPENDENTE, derivata dall'outcome scelto - mai riusata per convenzione.
3. Nuova identita' di esperimento (es. `SEQ-0014B_DESIGN_V2`), mai una modifica silenziosa dei parametri di DESIGN_V1.
4. L'intera provenance di DESIGN_V1 (fallito, hard stop) resta referenziata, mai nascosta.
5. Nessuna esplorazione di orizzonti alternativi (10/20/30/ecc.) per "salvare" SEQ-0014B - l'orizzonte deve emergere dall'outcome scelto, non essere scelto per far tornare i conti.

## Regressione

60/60 PASS su questa suite. **0 regressioni** sulle altre 17 suite Phase 7 (18 totali). Verificato meccanicamente: hash di `seq0014b_structural_preflight_spec_v1.json` e `seq0014b_structural_preflight_result_v1.json` invariati rispetto a `6c0d3f6`/`80e7cbc`.

## Deliverables

`seq0014b_outcome_horizon_ordering_audit_v1.json`, `build_seq0014b_outcome_horizon_ordering_audit.py`, `test_seq0014b_outcome_horizon_ordering_audit.py` - tutti in `server/research_scripts/phase7/phase7_6c/`. Nessuna modifica a spec/result gia' congelati.

---

**NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.** Nessuna scelta di primary outcome. Nessun orizzonte alternativo ispezionato. SEQ-0015 e SEQ-0009 restano chiuse.

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: 100%
VERSO DEMO: ~68%
██████▊░░░
FASE ATTUALE:
SEQ-0014B design V1 → structural hard stop
RISULTATO UTILE:
2580 nominali → 11 pooled indipendenti
cross-family dependence confermata
PROSSIMO:
verificare corretto ordering
outcome ↔ horizon ↔ structural geometry
```

Non siamo avanzati percentualmente, ma il risultato di questo audit e' esso stesso un progresso di rigore: il verdetto NOT_TESTABLE resta corretto, ma ora e' correttamente delimitato a DESIGN_V1 invece di essere letto come una condanna universale del claim MECH-23.
