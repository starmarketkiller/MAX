# NEXUS - Phase 7.0: Discovery Engine v2 - Architecture & Preflight

**Tipo di fase:** ARCHITETTURA + PREFLIGHT + RESEARCH CONTRACT. Non e' stata eseguita alcuna discovery run reale, nessun H007, nessun nuovo edge, nessun backtest su dati di mercato. Tutti i controlli sono stati verificati su dati sintetici (`synthetic_fixtures.py`), esplicitamente etichettati `SYNTHETIC_FIXTURE_ONLY` in ogni artifact prodotto.

**Baseline di riferimento (non modificato):** Phase 5 (`b9414e6`), Phase 6 True Holdout (`0e78972`), Phase 6.6 Integrity Patch (`2fe489e`). Nessun risultato storico, nessuna decision card, nessun evidence record esistente e' stato alterato in questa fase.

---

## 1. Cosa cambia rispetto a v1 (Phase 5)?

Il cambiamento principale non e' un algoritmo migliore, ma uno spostamento dei controlli **da retroattivi a nativi**. In Phase 5, il pattern era: scoprire un edge, poi (in fasi successive: 5.5, 6, 6.5, 6.6) scoprire i problemi che lo rendevano inaffidabile - leakage nella normalizzazione, baseline non direction-aware, dipendenza fra eventi, contaminazione della validazione. In Phase 7 questi controlli (`baseline_contract_v4.json`, `cross_split_safety.py`, `dependence_diagnostics_v2.py`, `post_hoc_quarantine.py`) fanno parte della definizione stessa del processo di scoperta, applicati PRIMA che un candidato possa avanzare, non scoperti mesi dopo con un audit. La seconda differenza sostanziale: l'unita' di scoperta (`setup_candidate.schema.json`) e' ora `EdgeCandidate = Setup x MarketState x Direction x Outcome vs MatchedBaseline`, un oggetto singolo, versionato, con una signature canonica - in Phase 5 un "pattern" era un concetto piu' informale, ricostruito a posteriori dai file di codice usati.

## 2. Come si previene l'esplosione combinatoria?

Tre meccanismi indipendenti, non uno solo: (a) `candidate_generation_policy.json` limita esplicitamente ogni candidato a Level 0/1/2 (massimo 2 state_conditions oltre alla direzione), vietando a livello di POLICY threshold grid, prodotti cartesiani, ottimizzazione genetica o ricerca casuale come generatori; (b) l'unico generatore di proposte ammesso oltre l'ipotesi di dominio e' un albero decisionale poco profondo (depth 2-3), usato SOLO per proporre, mai per verdetto (`statistical_methods_policy.json`); (c) `candidate_signature.py` deduplica meccanicamente qualunque candidato che normalizzi alla stessa signature canonica (stesso event_family/direction/state_conditions ordinati/outcome), indipendentemente dall'ordine con cui e' stato scritto - dimostrato nel preflight (Check 3).

## 3. Come si gestisce la dipendenza fra eventi?

Nativamente, non come audit a posteriori (a differenza di Phase 6.5, dove `dependence_diagnostics.py` fu introdotto retroattivamente su H006). `dependence_diagnostics_v2.py` reintroduce le stesse primitive (clustering, autocorrelazione, ESS) ma aggiunge il confronto esplicito **EVENT VIEW vs EPISODE VIEW**: ogni cluster di eventi ravvicinati viene collassato al suo PRIMO evento (temporale, mai quello con l'outcome migliore - scelta dichiarata per evitare cherry-picking). Se l'effetto esiste in EVENT VIEW ma collassa (cambia segno o scende sotto la soglia di materialita') in EPISODE VIEW, il candidato e' marcato `DEPENDENCE_SENSITIVE` e non puo' essere promosso basandosi solo sulla vista piu' favorevole. Verificato nel preflight (Check 7) su dati sintetici clusterizzati.

## 4. Come si separano discovery, validation e holdout?

`partition_contract_v2.json` definisce la struttura a tre segmenti (DEVELOPMENT con discovery+internal_validation, LOCKED_VALIDATION, FINAL_HOLDOUT) e `cross_split_safety.py` la impone TECNICAMENTE: nessun controllo di baseline puo' attraversare split diversi da quello dell'evento senza un'eccezione esplicita e motivata (mai silenziosa - un tentativo di eccezione senza motivazione solleva `ValueError`). Verificato nel preflight sia a livello di singola chiamata (Check 1) sia su un pass completo di 30 eventi sintetici con un caso corrotto deliberato (Check 6). **Nota di onesta':** oggi esiste solo un dataset a 2 segmenti (Phase 5: 2019-2022, Phase 6: 2022-2023) - la struttura a 3 segmenti e' progettata e pronta, ma NON ancora popolata con dati reali (vedi domanda 11).

## 5. Come si impedisce che una scoperta nel segmento diagnostico diventi un edge?

`post_hoc_quarantine.py` intercetta meccanicamente qualunque osservazione scoperta attraverso un canale diverso dal test primario pre-registrato (direction_split, quarter_split, subgroup_split, failure_anatomy, residual_analysis): tali osservazioni ricevono automaticamente `is_edge=False`, `requires_new_hypothesis=True`, `requires_new_holdout=True` e non possono essere promosse a `SUPPORTED`/`PRE_REGISTERED_CANDIDATE`/`INDEPENDENT_VALIDATION` nella stessa run (`PostHocPromotionBlocked`). Il modulo replica deliberatamente lo scenario storico reale `SELL_SWEEP_RECLAIM_ASYMMETRY` (Phase 6.5/6.6) come test - dimostrando che il gate blocca oggi meccanicamente cio' che allora era garantito solo da disciplina umana. Verificato nel preflight (Check 4).

## 6. Qual e' il contratto della Baseline Engine v4?

`baseline_contract_v4.json` dichiara esplicitamente sei proprieta' obbligatorie: direction-aware nativamente (non piu' retroattiva, correggendo l'errore di Phase 6 - vedi FAIL-005), temporalmente sicura, state-matched solo con dimensioni giustificate (volatility_state/trend_state/regime), fittata solo su discovery (mai su validation/holdout), split-safe (enforced da `cross_split_safety.py`), e auditabile per-match (direzione evento, direzione baseline, distanza, qualita'). Il documento dichiara anche esplicitamente il trade-off overmatching/undermatching e una regola di risoluzione (partire minimale, aggiungere una dimensione solo se la qualita' del match resta GOOD/FAIR) - senza fissare un algoritmo di matching specifico, che resta da implementare in Phase 7.1.

## 7. Come si gestisce il multiple testing e le famiglie di candidati?

`multiple_testing_v2.py` generalizza la matematica gia' in uso da Phase 5.5 (Benjamini-Hochberg) in una funzione libreria (`run_family`) richiamabile per QUALUNQUE famiglia futura con un `family_id` esplicito - non piu' un ledger costruito ad hoc per un solo batch. La regola dichiarata (non negoziabile, presente nel `guardrail_statement` di ogni output): **FDR correction != independent validation** - un p-value aggiustato significativo non autorizza da solo alcuna transizione di lifecycle oltre `INTERNAL_VALIDATION`. `red_team_analysis.json` (vettore `CORRELATED_HYPOTHESES_COUNTED_AS_INDEPENDENT`) documenta il rischio residuo: la definizione di "quali varianti appartengono alla stessa famiglia" resta in parte euristica.

## 8. Come si rilevano candidati duplicati?

`candidate_signature.py`: una stringa canonica multi-riga (`EVENT=.../DIR=.../STATE.<feature><op><threshold>` ordinato per feature_id, mai per ordine di inserimento, `/OUTCOME=...`), hashata SHA-256. Nessuna componente semantica/AI - solo normalizzazione testuale deterministica, come esplicitamente richiesto. Dimostrato nel preflight (Check 3): due candidati con le stesse condizioni scritte in ordine diverso producono la stessa signature; un cambio di direzione produce una signature distinta.

## 9. Quali soglie sono statisticamente giustificate e quali sono scelte di policy?

La maggioranza e' `POLICY_THRESHOLD`, dichiarata come tale senza infingimenti (n_nominal_minimum=30, cluster_count_minimum=20, effective_n_minimum=20, minimum_controls_per_match=20, minimum_material_delta_p_default=0.10, match_quality_thresholds, cluster_gap_threshold) - vedi `minimum_evidence_gates.json` e `baseline_contract_v4.json`, ciascuna con una rationale che distingue il PRINCIPIO (spesso motivato) dal NUMERO esatto (quasi sempre arbitrario). Una sola gate e' marcata `STATISTICALLY_JUSTIFIED` in senso pieno: il requisito che gli intervalli di confidenza Wilson di evento e baseline non si sovrappongano - un criterio statistico riconosciuto, non un numero scelto per convenienza.

## 10. Quali modalita' di fallimento NON sono ancora risolte?

Cinque gap espliciti, elencati in `red_team_analysis.json.open_gaps_summary` e in `failure_memory_registry_v1.json` (FAIL-004):
1. **EVENT_FIRING_RATE** - nessun check automatico sul tasso di attivazione di un `event_family` (rischio: un detector troppo permissivo come PULLBACK in Phase 5.5, 83% delle barre).
2. **CALENDAR_LEAKAGE** indiretto - nessun test dedicato oltre il leakage guard generico ereditato da Phase 5.5.
3. **CANDIDATE_SURVIVORSHIP** - nessun modo tecnico di verificare che un'idea non sia stata scartata mentalmente prima di essere formalizzata (rischio di processo, non di codice).
4. **VALIDATION_REUSE** - nessun log tecnico di accesso ai segmenti locked/holdout; l'enforcement "una sola lettura" e' oggi solo documentale.
5. **DATASET_VERSION_DRIFT** - `candidate_result_v2.schema.json` prevede gia' il campo `dataset_version_hash`, ma nessun collegamento automatico a `dataset_versioning_v1.json` e' ancora implementato.

## 11. Il sistema e' pronto per una vera run di Phase 7.1?

**NO.** Non per limiti di progettazione (l'architettura, gli schemi e le sei gate meccaniche sono costruiti e verificati sul preflight sintetico - 14/14 PASS), ma per limiti di dati e implementazione mancante:

- **Dati:** esistono oggi solo due segmenti Dukascopy (Phase 5: 2019-02-03/2022-02-03; Phase 6: 2022-02-04/2023-02-03). Non esiste alcun dato per il periodo successivo al 2023-02-03 (`partition_contract_v2.json`, verificato per ispezione diretta dei manifest, non assunto). La struttura DEVELOPMENT/LOCKED_VALIDATION/FINAL_HOLDOUT a 3 segmenti e' **progettabile ma non ancora acquisita** - serve un nuovo download Dukascopy per un periodo di circa 3+ anni mai toccato prima di poter eseguire una vera Phase 7.1 con tre segmenti realmente indipendenti.
- **Baseline Engine v4:** il contratto (`baseline_contract_v4.json`) e' scritto, ma l'implementazione dell'algoritmo di matching vero e proprio (nearest-neighbour standardizzato, versione 2024 del codice Phase 5.5/6.5 riadattata al contratto v4) non e' stata scritta in questa fase - solo la specifica.
- **Cinque gap espliciti** della domanda 10 restano aperti.
- **candidate_result_v2.schema.json** e' pronto, ma nessun generatore reale di candidate_result su dati veri esiste ancora - solo la demo sintetica del preflight.

**Cosa manca esattamente, in ordine di priorita', prima di poter dichiarare pronta una Phase 7.1 reale:**
1. Acquisire dati Dukascopy per un nuovo periodo (2023-02-04 in poi) sufficiente a popolare i tre segmenti dichiarati in `partition_contract_v2.json`.
2. Implementare l'algoritmo di Baseline Engine v4 (oggi solo contratto, non codice).
3. Chiudere almeno il gap EVENT_FIRING_RATE (rischio piu' concreto, gia' osservato in forma simile con PULLBACK in Phase 5.5).
4. Implementare un log di accesso tecnico ai segmenti locked/holdout (VALIDATION_REUSE).
5. Collegare `dataset_version_hash` a `dataset_versioning_v1.json` in modo automatico (DATASET_VERSION_DRIFT).

Fino ad allora, Phase 7 resta esattamente cio' che l'utente ha richiesto: un'architettura e un contratto di ricerca verificato, non ancora una macchina di scoperta operativa.

---

## Artifact prodotti

**Schemi:**
- `server/research_scripts/phase7/schemas/setup_candidate.schema.json`
- `server/research_scripts/phase7/schemas/outcome_surface_v2.schema.json`
- `server/research_scripts/phase7/schemas/research_journal.schema.json`
- `server/research_scripts/phase7/schemas/candidate_result_v2.schema.json`

**Registry e contratti:**
- `server/research_scripts/phase7/feature_registry_v2.json` (+ `build_feature_registry_v2.py`)
- `server/research_scripts/phase7/partition_contract_v2.json`
- `server/research_scripts/phase7/baseline_contract_v4.json`
- `server/research_scripts/phase7/failure_memory_registry_v1.json`
- `server/research_scripts/phase7/red_team_analysis.json`

**Policy:**
- `server/research_scripts/phase7/policies/candidate_generation_policy.json`
- `server/research_scripts/phase7/policies/threshold_policy.json`
- `server/research_scripts/phase7/policies/minimum_evidence_gates.json`
- `server/research_scripts/phase7/policies/effect_size_first_policy.json`
- `server/research_scripts/phase7/policies/stability_matrix_policy.json`
- `server/research_scripts/phase7/policies/cross_market_readiness_policy.json`
- `server/research_scripts/phase7/policies/cost_model_integration.json`
- `server/research_scripts/phase7/policies/statistical_methods_policy.json`

**Motore (codice, ciascuno verificato con caso valido + caso negativo):**
- `server/research_scripts/phase7/engine/candidate_lifecycle.py`
- `server/research_scripts/phase7/engine/candidate_signature.py`
- `server/research_scripts/phase7/engine/dependence_diagnostics_v2.py`
- `server/research_scripts/phase7/engine/multiple_testing_v2.py`
- `server/research_scripts/phase7/engine/post_hoc_quarantine.py`
- `server/research_scripts/phase7/engine/cross_split_safety.py`

**Preflight (sec.26 - sintetico, nessun dato di mercato):**
- `server/research_scripts/phase7/synthetic_fixtures.py`
- `server/research_scripts/phase7/preflight_simulation.py` (14/14 check PASS)
- `server/research_scripts/phase7/preflight_output/discovery_run_manifest_v2.json`
- `server/research_scripts/phase7/preflight_output/candidate_registry_v2.json`
- `server/research_scripts/phase7/preflight_output/multiple_testing_report_v2.json`
- `server/research_scripts/phase7/preflight_output/dependence_diagnostics_v2.json`

---

## Nota di chiusura

Ogni gate descritta in questo documento e' stata dimostrata su dati sintetici, non solo dichiarata: `preflight_simulation.py` produce 14 controlli PASS/FAIL veri, inclusi almeno un caso deliberatamente rotto per ciascun meccanismo critico (split isolation, leakage guard, deduplicazione, quarantena post-hoc, FDR, baseline cross-split, dipendenza, lifecycle). Questo e' il punto centrale della richiesta originale: trasformare gli errori scoperti in Phase 5/6/6.5/6.6 in vincoli strutturali verificabili meccanicamente, non in promemoria da ricordare a mano nella prossima run.
