# NEXUS - Phase 7.6D MECH-23 Outcome-Horizon Contract

**Baseline:** `f6b0859` (Phase 7.6C Outcome-Horizon Ordering Audit). Formalizzazione **puramente concettuale** per un eventuale `SEQ-0014B_DESIGN_V2`: nessuna geometria eseguita, nessun outcome letto, nessun orizzonte alternativo ispezionato sui dati, nessuna configurazione scelta per massimizzare n.

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO STRUCTURAL PREFLIGHT EXECUTED. NO EDGE DISCOVERY PERFORMED.**

---

## Perche' questa fase

L'audit precedente (`f6b0859`) aveva mostrato che `natural_horizon=40` era `PROJECT_CONVENTION`, non derivato dall'outcome - ma aveva anche notato una sottigliezza ulteriore: nemmeno "prima scegliamo l'outcome" basta, perche' il vocabolario stesso (`outcome_surface_v3.py`) non incorpora un orizzonte nelle sue definizioni. Scegliere il NOME di un outcome (es. MAE) non dice affatto su quante barre misurarlo. La catena corretta e':

```
CLAIM → ESTIMAND → OUTCOME DEFINITION → RESOLUTION WINDOW/CENSORING → NATURAL HORIZON → EMBARGO → STRUCTURAL FEASIBILITY → INFERENCE
```

## 1-2. Claim ed estimand

Claim MECH-23 (verbatim, da `market_sequence_registry_v1.json`): *"Se i setup direzionali generati durante lo stato 'choppy' non mostrassero un tasso di fallimento/rumore superiore rispetto a quelli generati in stato 'trending', il claim sarebbe falso."*

**Primary estimand:** Delta = E[Failure | famiglia F, CHOPPY] - E[Failure | famiglia F, TRENDING], stimato per ciascuna delle 6 famiglie separatamente (mai pooled cross-family per il contrasto). Risponde a "filter utility", non a redditivita' generica o comportamento generico del prezzo (dominio gia' distinto di SEQ-0014A, Phase 7.6A).

## 3. Candidate outcome audit (semantico, senza dati)

| Candidato | Rappresenta | Uniforme su 6 famiglie | Horizon | Barrier | Censoring | Adatto come primary |
|---|---|---|---|---|---|---|
| P_PLUS_1ATR_BEFORE_MINUS_1ATR | Success/Failure diretto | Si' (ATR-norm.) | Si' | Intrinseco | Si' | **Migliore candidato** |
| MAE | Noise/magnitudo continua | Si' | Si' (dipendenza monotona!) | No | No | Secondario/diagnostico |
| REVERSAL_PROBABILITY | Failure, ma sotto-specificato | Indeterminato | Si' | Implicito, non dichiarato | Si' | Rischio ridondanza con P_PLUS |
| TIME_TO_TARGET | Timing condizionale, non fallimento | N/A | Si' | Presuppone un target altrove | Si' | **Non adatto come primary** |
| PATH_EFFICIENCY | Qualita' del percorso di prezzo | Si' | Si' | No | No | **Rischio contaminazione con SEQ-0014A** |

## 4. Primary outcome: classe identificata, magnitudo bloccata

**Classe:** `DOUBLE_BARRIER_SUCCESS_FAILURE_PROBABILITY` (famiglia P_PLUS_*ATR_BEFORE_MINUS_1ATR) - unico candidato che rappresenta direttamente successo/fallimento, ATR-normalizzato (omogeneo fra famiglie), gia' nel vocabolario congelato.

**Blocker:** il vocabolario offre 5 varianti (0.25/0.5/1/1.5/2 ATR upside, downside fisso a -1 ATR). Il testo verbatim del claim non specifica alcuna magnitudo. Scegliere ora la variante simmetrica "1 ATR" per comodita' ripeterebbe **esattamente** l'errore gia' trovato per l'horizon in `f6b0859`.

**Verdetto:** `PRIMARY_OUTCOME_CLASS_IDENTIFIED_EXACT_PARAMETERIZATION_NOT_YET_JUSTIFIED`.

## 5-6. Horizon e censoring

L'orizzonte non e' derivabile finche' la magnitudo di barriera resta aperta (una barriera piu' stretta implica tipicamente una risoluzione piu' rapida). Fonti di derivazione esplicitamente vietate: sample size, n indipendente, matching feasibility, risultato di DESIGN_V1 (`80e7cbc`), ispezione di orizzonti alternativi sui dati.

**Barrier vs censoring:** distinti esplicitamente. Tre trattamenti del caso "nessuna barriera toccata entro l'horizon" identificati (`TREAT_AS_FAILURE`, `TREAT_AS_NEUTRAL_EXCLUDED`, `THIRD_CATEGORY_REPORTED_SEPARATELY`) - nessuno scelto. `TREAT_AS_NEUTRAL_EXCLUDED` segnalato come il piu' rischioso (selection bias asimmetrico fra CHOPPY/TRENDING, esattamente il fenomeno che il claim intende misurare).

## 7. Common vs family-specific horizon

Evidenza gia' raccolta in `f6b0859`: SEQ-0014A usa horizon=20, SEQ-0009 usa horizon=40 per claim diversi sullo stesso substrato di regime. Le 6 famiglie di SEQ-0014B sono meccanicamente eterogenee (eventi istantanei vs. continuazione di trend vs. reversal vs. rilascio di compressione). **Opzione B (horizon per-famiglia) e' preliminarmente piu' difendibile** di un horizon comune imposto solo per comodita' di declustering - ma introduce un problema nuovo, non risolto qui: quale soglia di embargo usare per il declustering cross-family fra famiglie con orizzonti diversi. Decisione non presa, esplicitamente non risolta per comodita'.

## 8-9. Filter utility e materiality

Una probabilita' di fallimento si mappa direttamente su una decisione NO_TRADE reale (a differenza di MAE/PATH_EFFICIENCY/TIME_TO_TARGET) - rafforza la scelta della CLASSE di outcome. Materiality: il floor di progetto gia' esistente (`minimum_material_delta_p_default=0.10`, `minimum_evidence_gates.json`) resta riusabile come default non bloccante; una derivazione MECH-23-specifica migliorerebbe la soglia ma non blocca.

## 10. DESIGN_V2 eligibility

| Componente | Stato |
|---|---|
| primary_estimand | **Congelabile** |
| primary_outcome | **BLOCCANTE** (magnitudo di barriera non giustificata) |
| horizon | **BLOCCANTE** (dipende dalla magnitudo) |
| censoring | **BLOCCANTE** (dipende da entrambi) |
| direction_of_expected_effect | Congelabile (univoca dal testo del claim) |
| materiality_definition | Parzialmente congelabile (floor di default) |

**Verdetto: `DESIGN_V2_BLOCKED_ON_OUTCOME_HORIZON_CONTRACT`.**

## Regola di framework (raffinata, nessuna nuova infrastruttura)

Affina la regola proposta in `f6b0859` (che si fermava a "outcome class + horizon prima del verdetto"): serve un anello esplicito in piu' fra la definizione dell'outcome e l'orizzonte - **RESOLUTION WINDOW / CENSORING**. La definizione di un outcome da sola (es. "MAE") non specifica ancora la finestra di risoluzione.

## Regressione

57/57 PASS su questa suite. **0 regressioni** sulle altre 18 suite Phase 7 (19 totali). Verificato: nessuna modifica ai frozen DESIGN_V1 artifact (`6c0d3f6`/`80e7cbc`, hash invariati).

## Nota del reviewer sul risultato 2580→11 (riportata, non un task di questa fase)

Il risultato resta utile indipendentemente dall'horizon: 65.4% dei setup co-locati cross-family non dipende dall'embargo. Segnala che molte delle "sei famiglie" descrivono aspetti diversi dello stesso evento di mercato - un possibile salto architetturale futuro (Market Event Object / Event Ontology con tag semantici multipli invece di sei detector separati) e' stato annotato in backlog metodologico, non implementato ora (il reviewer vuole prima vedere se il fenomeno si ripete su altre famiglie).

## Deliverables

`seq0014b_outcome_horizon_contract_v1.json`, `build_seq0014b_outcome_horizon_contract.py`, `test_seq0014b_outcome_horizon_contract.py` - tutti in `server/research_scripts/phase7/phase7_6d/`. Nessuna modifica ai frozen DESIGN_V1 artifact.

---

**NO NEXUS OUTCOME DATA ACCESSED. NO STRUCTURAL PREFLIGHT EXECUTED. NO EDGE DISCOVERY PERFORMED.** Nessuna scelta di primary outcome. SEQ-0015 e SEQ-0009 restano chiuse.

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: 100%
VERSO DEMO: ~68%
██████▊░░░
FASE ATTUALE:
DESIGN_V1 correttamente scoped come
HORIZON-CONDITIONAL structural failure
PROSSIMO SBLOCCO:
claim → estimand → outcome → horizon
prima di qualunque DESIGN_V2
```

Il blocco su DESIGN_V2 non e' un fallimento del progetto - e' la scoperta che l'ordine "outcome-first" da solo non basta: serve anche la magnitudo esatta dell'outcome (la barriera) prima che l'horizon possa essere derivato, non solo il suo nome. Il metodo si sta autocorreggendo un livello alla volta.
