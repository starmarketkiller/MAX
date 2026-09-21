# NEXUS - Phase 7.5C SEQ-0014 (MECH-23 LOW_INFORMATION_STATE) Structural Feasibility Result

**Formalization commit:** `28e3435` (frozen spec, congelato PRIMA di eseguire il gate). **Baseline pre-formalizzazione:** `f7559ee` (SEQ-0015/SEQ-0009 chiuse). **Questo e' il RESULT COMMIT** - eseguito il gate strutturale reale su dati reali (`market_state_dataset_p71.csv`, partition `development_discovery`), separato dal formalization commit.

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.** Nessun parametro e' stato aggiustato dopo aver visto questo risultato.

---

## Verdetto finale

| | |
|---|---|
| **FINAL STRUCTURAL VERDICT** | **`FEASIBLE`** |
| **geometry_verdict** | `FEASIBLE` (49 unita' indipendenti, 1.63× il minimo di 30) |
| **matching.status** | `EXECUTED_FEASIBLE` (49/49 matchati, qualita' GOOD, nessun problema di reuse/determinismo) |
| **formalization_level** | `MATCHING_PREFLIGHT_READY` (preflight REALMENTE eseguito) |

**Questa e' la prima family delle 5 rimaste che supera l'intero gate strutturale.** Come da istruzione esplicita, **mi fermo qui**: nessuna lettura di outcome, nessun contratto statistico, nessun BH - il passo successivo (preregistrazione/discovery) sara' autorizzato separatamente.

## Diagnostica state → episode → entry-event (richiesta esplicitamente, sec.11)

```
n_bars discovery = 2393
raw positive-state bars (directional_efficiency in tercile LOW) = 798   (firing_rate = 33.3% delle barre)
state episodes (corse contigue di in_state=True)                = 189
state-entry events (transizioni 0->1, identico per costruzione)  = 189
durata di stato: media=4.2 barre, mediana=3, min=1, max=20 barre

EVENT_VIEW      = 189
EPISODE_VIEW     = 128   (episode_gap_rule=5)
INDEPENDENT_VIEW =  49   (outcome_overlap_embargo_bars=19)

minimo richiesto = 30
```

**Verifica chiave (la domanda posta esplicitamente):** il 33% delle barre e' "in stato" - un firing rate per-barra molto alto - ma la trasformazione STATE→ENTRY-EVENT lo riduce immediatamente a 189 eventi (non 798), e le due passate di declustering (episode_gap_rule poi embargo) lo riducono ulteriormente a 49 unita' realmente indipendenti. **La persistenza di regime NON e' stata trasformata in sample size artificiale** - il gate ha correttamente distinto "quante barre sono nello stato" da "quante osservazioni indipendenti di INGRESSO nello stato esistono".

## Cluster geometry (autorita' - `inferential_independent_geometry`)

| Metrica | Valore |
|---|---|
| episode_retention | 0.677 (128/189) |
| independence_retention | 0.383 (49/128) |
| n_independent_clusters | 49 ✅ = `INDEPENDENT_VIEW.n` (invariant verificato, nessun `ClusterGeometryInconsistencyError`) |
| max_cluster_size | 7 |
| median_cluster_size | 2 |
| fraction_episode_representatives_in_largest_cluster | 0.055 (nessun cluster dominante, a differenza di SEQ-0009 dove un cluster raccoglieva il 59%) |
| firing_geometry_risk_flag | `risk_flag=true` (median_gap=9 ≤ embargo=19) - **diagnostico**, l'autorita' (independent_units=49) mostra che il rischio non si e' materializzato |

## Matching preflight (eseguito realmente)

`match_dimensions=[volatility_state_pre_entry]` (terzile di `atr_percentile` a t-1, distinto dalla feature che definisce lo stato - nessuna tautologia): **49/49 eventi matchati**, tutti qualita' **GOOD** (0 FAIR, 0 POOR), reuse massimo osservato = 1 (ben sotto il tetto di 5), tie-break deterministico verificato.

## Confronto con le famiglie precedenti (contesto, non nuova valutazione)

| | SEQ-0015 (chiusa) | SEQ-0009 (chiusa) | SEQ-0014 (questo risultato) |
|---|---|---|---|
| EVENT→EPISODE→INDEPENDENT | 249→210→1 | 246→169→10 | 189→128→**49** |
| independence_retention | 0.005 | 0.059 | **0.383** |
| Verdetto | NOT_TESTABLE | NOT_TESTABLE | **FEASIBLE** |

Le prime due family (eventi puntuali a rigetto/rottura) collassavano quasi interamente nella seconda passata di declustering. SEQ-0014 (una classificazione di stato, con episode_gap_rule/horizon derivati dalla propria scala temporale di 20 barre invece che dal default di 40) mantiene una frazione molto piu' alta di informazione indipendente - **non perche' "più facile da testare" in astratto, ma perche' la sua stessa scala temporale (20 barre) produce episodi piu' brevi e piu' distanziati relativi all'embargo**, esattamente il tipo di risultato che il gate e' progettato per far emergere onestamente.

## Deliverables prodotti

- `seq0014_frozen_structural_spec_v1.json` (formalization commit `28e3435`)
- `seq0014_state_entry_detector.py` (nuovo, v1, 5/5 self-test)
- `seq0014_structural_feasibility_result_v1.json` (questo commit) - diagnostica state→episode→entry-event, detection funnel, cluster geometry, matching preflight, verdetto completo
- `test_seq0014_frozen_spec.py` (30/30 PASS, formalization commit)
- `run_seq0014_structural_feasibility.py` (script di esecuzione, questo commit)

## Bug policy

**Nessun bug concreto del gate e' emerso durante questa esecuzione** - il gate (incl. l'invariant di geometria e la fedelta' direzionale delle patch precedenti) ha gestito correttamente una family di tipo STATO senza richiedere alcuna modifica. Nessuna nuova infrastruttura aggiunta, come da istruzione.

## Confermato

- **NO NEXUS OUTCOME DATA ACCESSED** - solo `market_state_dataset_p71.csv` (feature CAUSAL_SAFE), mai `outcomes_v1.csv`.
- **NO EDGE DISCOVERY PERFORMED.**
- **NO STATISTICAL CONTRACT BUILT.**
- SEQ-0015 e SEQ-0009 restano `CLOSED_NOT_REEXAMINED_AS_CANDIDATE`.
- Nessun parametro del formalization commit e' stato modificato dopo aver visto questo risultato.

---

**SEQ-0014 e' `FEASIBLE`** sulla partition `development_discovery` con il design congelato in `28e3435` - geometria e matching entrambi verificati realmente, non solo dichiarati. Questo **non e'** un'autorizzazione a procedere alla preregistrazione statistica: quel passo, per istruzione esplicita, va autorizzato separatamente. Mi fermo qui.
