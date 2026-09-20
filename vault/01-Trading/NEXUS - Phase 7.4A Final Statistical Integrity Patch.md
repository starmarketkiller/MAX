# NEXUS - Phase 7.4A Final Statistical Integrity Patch

> **CORREZIONE (Phase 7.4A Dependence Validity Gate, 2026-09-20)**: la sezione "4. Struttura matched preservata" sotto interpretava erroneamente il risultato `rejection_rate=0%` dello scenario shared-regime come possibile effetto di "varianza sottostimata" che "può rendere il test anti-conservativo". È l'opposto: 0% di rigetto è **fortemente conservativo/powerless**, non anti-conservativo. Il meccanismo corretto (il bootstrap ricampiona evento e baseline separatamente, trattando come "incertezza" una componente di varianza che nel dato osservato si cancella per condivisione del regime) è documentato in dettaglio in `vault/01-Trading/NEXUS - Phase 7.4A Dependence Validity Gate.md` e nel campo `interpretation` di `phase7_4_null_calibration_v1.json` (rigenerato). **La conclusione finale resta valida**: appiattire la struttura matched produce un'inferenza mal calibrata - a volte in una direzione, a volte nell'altra, mai in modo prevedibile. Questo file è lasciato intatto per il resto (nessuna riscrittura silenziosa) - solo questa nota è stata aggiunta.

**Baseline:** `c4f96ac` (Phase 7.4A Integrity Patch). Verifica formale del test inferenziale per outcome continui/binari **prima** che i suoi p-value entrino in BH-FDR - **nessuna discovery eseguita, nessun dato NEXUS letto, nessuna soglia ricalibrata sui dati**.

**Conferma esplicita: NO REAL NEXUS OUTCOME DATA ACCESSED. NO SEQUENCE DISCOVERY EXECUTED.** Tutta la simulazione di calibrazione (4000+ repliche) gira su dati sintetici generati in memoria.

---

## 1-2. Bootstrap CI vs p-value valido: la simulazione ha risposto NO

Il metodo `two_sample_block_bootstrap_percentile_p` (Phase 7.4A Integrity Patch) è un test per **inversione di CI sui dati osservati**, non impone esplicitamente H0. **Null-calibration simulation** (1000 repliche × 4 scenari sintetici sotto H0 vera, `phase7_4_null_calibration_v1.json`):

| Scenario | rej@.01 | rej@.05 | rej@.10 | Nominale |
|---|---|---|---|---|
| Gaussian iid | 0.026 | 0.071 | 0.123 | .01/.05/.10 |
| Skewed | 0.043 | 0.107 | 0.184 | .01/.05/.10 |
| Autocorrelato | **0.142** | **0.234** | **0.33** | .01/.05/.10 |
| n sbilanciato (30 vs 300) | 0.039 | 0.092 | 0.153 | .01/.05/.10 |

**Sistematicamente anti-conservativo in tutti e 4 gli scenari** (1.4×-14× il tasso nominale). Per esplicita istruzione: **non difeso, sostituito**.

## 3-4. Nuovo metodo: block sign-flip permutation su coppie matched

Sostituito con **`block_sign_flip_permutation_matched_pair`** (`engine/matched_pair_permutation_test.py`): per ogni osservazione i, `d_i = outcome(event_i) - mean(outcome(matched_controls_i))` (mai un pool evento/baseline appiattito). Sotto H0 il segno di d_i è scambiabile - distribuzione nulla generata capovolgendo il segno di **blocchi contigui** (L=ceil(n^(1/3)), stessa formula già in uso), p-value di permutazione standard. Questo **impone esplicitamente H0:E[d]=0** per costruzione (a differenza del metodo precedente).

**Calibrazione verificata:**

| Scenario | rej@.01 | rej@.05 | rej@.10 |
|---|---|---|---|
| Gaussian iid | 0.004 | **0.049** | 0.097 |
| Skewed | 0.015 | 0.063 | 0.118 |
| Autocorrelato (d_i, φ=0.7) | 0.041 | 0.182 | 0.274 |
| Pochi controlli/rumoroso | 0.012 | **0.051** | 0.109 |

Ben calibrato per iid/skewed/pochi-controlli. **Limite onestamente riportato**: sotto autocorrelazione forte (φ≥0.5-0.7) fra osservazioni GIÀ embargate resta anti-conservativo (~2-4× nominale) - verificato che **aumentare la block length peggiora la situazione** (collassa la risoluzione del test: a L=6/8 il numero di pattern di segno possibili è troppo basso per raggiungere p<.05, dando 0% di rigetto anche sotto vero effetto - testato esplicitamente). È un limite matematico di risoluzione dei test di permutazione a blocchi con n piccolo, non risolvibile per scelta di parametro. **Mitigato da**: (1) l'embargo di 39 barre già rimuove la dipendenza meccanica diretta; (2) il gate `DEPENDENCE_SENSITIVE` esistente resta obbligatorio prima di qualunque promozione oltre `INTERNAL_VALIDATION`.

## 4. Struttura matched preservata - dimostrazione decisiva

Scenario sintetico con shock di regime condiviso fra evento e i suoi 5 controlli matched (H0 esatta, `E[d_i]=0` per costruzione):

| Metodo | rej@.01 | rej@.05 | rej@.10 |
|---|---|---|---|
| **OLD** (pool appiattito, 150 controlli come se i.i.d.) | 0.0 | **0.0** | 0.0 |
| **NEW** (differenza per-evento, regime cancellato) | 0.003 | **0.042** | 0.091 |

Il pooling appiattisce gruppi di 5 controlli che condividono lo stesso shock di regime come se fossero 150 osservazioni indipendenti, producendo un test **catastroficamente mal calibrato** (mai rigetta, anche quando dovrebbe). Il metodo matched-pair **cancella esattamente** il fattore condiviso nella differenza per-evento, restando calibrato per costruzione. Questa è la prova quantitativa che la struttura matched va preservata, non solo un'affermazione.

## 5. Control reuse policy

`server/research_scripts/phase7/engine/control_reuse_ledger.py` (nuovo, enforcement meccanico non solo dichiarato): **`max_control_reuse_per_run=5`** (stesso valore di k, simmetrico, non ottimizzato sui dati). Riuso **ammesso** (non vietato - un pool storico finito lo rende spesso necessario), ma limitato e la cui incertezza residua è coperta dal gate `DEPENDENCE_SENSITIVE`. `control_temporal_overlap_policy`: la sovrapposizione fra i controlli di eventi DIVERSI non è vietata separatamente (richiederebbe un problema di assegnazione globale, fuori scope per questa family "poche dimensioni") - dichiarato come limite esplicito, non nascosto.

## 6. Audit outcome binari

`INDEPENDENT_TWO_SAMPLE_ASSUMPTION` dichiarata **NON valida** per `two_proportion_z_test`: evento e controlli matched non sono campioni indipendenti per costruzione. Unificato: `d_i` binario (0/1) meno media dei controlli (0/1) è già una differenza continua in [-1,1] - **stesso identico metodo matched-pair usato per i continui**, nessuna macchina separata.

## 7. FDR contract ricalcolato

Verificato programmaticamente: **7/7 outcome** hanno un metodo p-value validato (dalla stessa simulazione di calibrazione) - **nessuna demotion a DIAGNOSTIC_ONLY necessaria**. `final_n_inferential_outcomes=7`, `final_n_candidates=3`, **`final_family_size=21`** (invariato nel numero, ma ora genuinamente validato anziché solo dichiarato).

## 8. Correzione: assign_clusters È transitivo

v2 affermava erroneamente che una catena 100→138→176 (passi di 38 barre) **non** sarebbe stata catturata dall'embargo=39. **Falso**: `assign_clusters` collassa transitivamente sui gap consecutivi (38≤39 ad ogni passo) - l'intera catena diventa **un solo** cluster già alla passata di embargo. Corretto in v3: la ragione valida per mantenere un aggiustamento oltre l'embargo è **dipendenza di regime residua nelle realizzazioni dell'outcome** (statistica, non meccanica) fra osservazioni già correttamente de-clusterizzate - un concetto distinto e valido, non lo stesso errato.

## 9. Frozen spec v3

`phase7_4_seq0015_frozen_spec_v3.json`, **v1 e v2 lasciati intatti** (non sovrascritti). `supersedes: v2`. Verificato **programmaticamente**: 0 diff su formula/soglia/direction rispetto a v2, 0 diff su episode_rule/embargo rispetto a v2 (questa patch tocca solo contratto inferenziale/control policy).

- **detector_source_hash (v3)**: `7ed4f8e9443f1a8b77f0455a421fbbcb513b694655aa4d0278378feb7ec4b2bf` (identico a v2 - il file detector non è stato toccato in questa patch)
- **frozen_parameters_hash (v3)**: `6c7c15c8c1756483d3ed3d237e5695c3cdfb5b89e3fbdf538c79db343b4fda33` (identico a v2, stesso motivo)
- Validata al 100% contro lo schema (esteso con l'enum `BLOCK_SIGN_FLIP_PERMUTATION`, aggiunta esplicita e minimale)
- `preregistration_provenance_guard` verificato bloccare v3 finché non committata

## Metodo finale per binary/continuous outcomes

**Un solo metodo unificato**: `block_sign_flip_permutation_matched_pair` per tutti e 7 gli outcome (3 binari + 4 continui) - `seq0015_statistical_test_contract_v2.json` (supersede v1, che usava due metodi diversi e non validati).

## Regression tests - 20/20 PASS

`test_phase7_4a_final_statistical_patch.py`: calibrazione presente e ragionevole, esclusione corretta di eventi senza controlli, tetto di riuso controlli applicato, binari e continui condividono lo stesso metodo, `INDEPENDENT_TWO_SAMPLE_ASSUMPTION` dichiarata non valida, family size ricalcolata=21, detector/soglia identici v2→v3, v1/v2 mai sovrascritti, correzione sec.8 documentata, block_length coerente con la convenzione di progetto. Nessuna regressione: Phase 7.3 (12/12 + 10/10) e Phase 7.4A Integrity Patch (11/11) ancora tutti PASS.

## File prodotti/modificati

Nuovi: `engine/matched_pair_permutation_test.py`, `engine/control_reuse_ledger.py`, `null_calibration_simulation.py` + `phase7_4_null_calibration_v1.json`, `build_seq0015_statistical_test_contract_v2.py` + `seq0015_statistical_test_contract_v2.json`, `build_seq0015_frozen_spec_v3.py` + `phase7_4_seq0015_frozen_spec_v3.json`, `test_phase7_4a_final_statistical_patch.py`.

Modificati: `policies/statistical_methods_policy.json` (metodo precedente marcato SUPERSEDED non cancellato, nuovo metodo aggiunto), `schemas/sequence_family_frozen_spec_v1.schema.json` (enum esteso, backward-compatible).

---

**NO REAL NEXUS OUTCOME DATA ACCESSED. NO SEQUENCE DISCOVERY EXECUTED.**

**Commit/push eseguiti. Il commit di questa patch (frozen spec v3) diventa il vero `preregistration_commit_sha` per Phase 7.4B. Nessuna Phase 7.4B senza nuova autorizzazione.**
