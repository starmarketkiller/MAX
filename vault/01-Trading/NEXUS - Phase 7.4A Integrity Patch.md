# NEXUS - Phase 7.4A Integrity Patch (before real discovery)

**Baseline:** `bd02268` (Phase 7.4A, pre-registrazione SEQ-0015 v1). Chiude i 3 problemi identificati nella frozen spec **prima** di qualunque run reale - **nessuna discovery eseguita, nessun dato NEXUS letto, nessuna soglia ricalibrata sui dati**.

**Conferma esplicita: NO REAL NEXUS OUTCOME DATA ACCESSED. NO SEQUENCE DISCOVERY EXECUTED.** Tutti i test di questa patch girano su dati sintetici generati in memoria; l'unica lettura di file reali è del codice sorgente (per hash/verifica di invarianza) e dei metadati già stabiliti in fasi precedenti.

---

## 1. Episode dependence vs outcome overlap

Distinti due concetti prima confusi: **`event_cluster_rule`** (3 barre - "è la stessa espansione fisica locale?", usato per EPISODE_VIEW, invariato) e **`outcome_overlap_rule`** (nuovo - "le finestre di misura dell'outcome si sovrappongono, anche se le espansioni fisiche sono diverse?").

**Soluzione scelta: D (combinazione predefinita)**, motivata ex-ante:
- **Embargo di decluster** (=natural_horizon-1=**39 barre**) applicato in una SECONDA passata sui rappresentanti di EPISODE_VIEW → produce la **INDEPENDENT_VIEW**, il conteggio realmente usato per Wilson CI / two-proportion test / bootstrap.
- **Moving block bootstrap** come diagnostica di dipendenza residua quando il candidato risulta `DEPENDENCE_SENSITIVE` anche dopo l'embargo (cattura dipendenza seriale più sottile che un embargo a larghezza fissa non elimina - catene di burst a distanza appena sotto l'embargo).

A/B/C valutate e scartate come soluzioni **uniche** (motivazione completa in `frozen_parameters.episode_rule.outcome_overlap_rule.alternatives_considered` del v2) - la combinazione D è l'unica che risolve sia la pseudo-indipendenza pairwise esatta sia la dipendenza residua a catena.

Nuova funzione **`build_outcome_independent_view()`** aggiunta a `sequence_episode_engine.py` (Phase 7.3, estensione puramente additiva - nessuna funzione esistente modificata, re-testato: 12/12 synthetic suite + 10/10 red-team Phase 7.3 ancora PASS senza regressioni).

**Test sintetici richiesti - tutti verificati:**
| Caso | event_cluster (gap=3) | outcome_overlap (embargo=39) |
|---|---|---|
| t=100, t=102 | 1 episodio | — |
| t=100, t=105 | 2 episodi | **1 osservazione indipendente** (collassati) |
| t=100, t=141 | 2 episodi | 2 osservazioni indipendenti (nessun overlap) |

## 2. Statistical contract per outcome type

Creato **`seq0015_statistical_test_contract_v1.json`** - per ciascuno dei 7 outcome inferenziali: `variable_type`, `estimand`, `event_statistic`, `baseline_statistic`, `effect_definition`, `uncertainty_method`, `hypothesis_test`, `p_value_method`, `dependence_adjustment`, `missing_censored_handling`.

- **3 outcome binari** (P+0.5/1/1.5 ATR): **WILSON_CI95 + two_proportion_z_test** (invariato, già coerente).
- **4 outcome continui** (MFE, MAE, TIME_TO_MFE, PATH_EFFICIENCY): Wilson **non applicabile** → nuovo metodo **`two_sample_block_bootstrap_percentile_p`**, estensione esplicita e testata di `statistical_methods_policy.json` (composizione di due primitive già ammesse: `moving_block_bootstrap_ci` sulla serie evento + `iid_bootstrap_ci` sul pool di baseline, entrambe da `phase6_5/block_bootstrap.py`, mai reimplementate). Implementato in `engine/two_sample_bootstrap_test.py`, self-testato (nessuna vera differenza → p non significativo; differenza ampia e reale → p<0.05).
- Missing/censored: riusata la convenzione già stabilita `atr_outcome_for_bar` (Phase 5) - CENSORED per race non risolta entro l'orizzonte, esclusione piena per finestra troncata da fine split.

## 3. BH-FDR family eseguibile, non solo contata

Verificato **programmaticamente** (non solo dichiarato): **7/7** outcome inferenziali hanno un `hypothesis_test`/`p_value_method` congelato e definito. **Nessun outcome è stato spostato a DIAGNOSTIC_ONLY** - tutti e 6 i secondary avevano già un test appropriato disponibile fra i metodi ammessi dal progetto. `family_size = 3 candidati × 7 outcome = 21`, invariato ma ora verificabilmente eseguibile.

## 4. Correzione terminologica ATR_t

Corretta la frase (`novelty_note` del frozen spec, `failure_memory_relation_note` del registro) che descriveva l'ATR same-bar di H008 come **"non causale"**. Formulazione corretta: *ATR_t è causale al momento della decisione (disponibile a close(t), nessun dato futuro) ma self-normalized/endogeno rispetto alla propria anomalia (TR_t contribuisce ad ATR_t e ne attenua meccanicamente il rapporto burst_ratio)*. **Il detector congelato non è cambiato**: `TR_t / ATR_{t-1}` resta invariato - verificato **programmaticamente** confrontando 14 campi invarianti (formula/soglia/direction) fra v1 e v2: **0 differenze**.

## 5. Frozen spec v2

`phase7_4_seq0015_frozen_spec_v2.json` creata, **`v1` lasciata intatta e non sovrascritta** (nessuna modifica al file già committato in `bd02268`). v2 dichiara `supersedes: phase7_4_seq0015_frozen_spec_v1.json`, riporta gli hash di v1 per confronto diretto, e spiega esclusivamente le 3 correzioni di questa patch.

- **detector_source_hash (v2)**: `7ed4f8e9443f1a8b77f0455a421fbbcb513b694655aa4d0278378feb7ec4b2bf` (cambiato da v1 - **solo commenti/docstring**, verificato)
- **frozen_parameters_hash (v2)**: `6c7c15c8c1756483d3ed3d237e5695c3cdfb5b89e3fbdf538c79db343b4fda33`
- Validata al 100% contro `sequence_family_frozen_spec_v1.schema.json` (0 campi mancanti, 0 extra).
- Verificato che `preregistration_provenance_guard` blocchi correttamente v2 finché non è committata.

## 6. Regression tests - 11/11 PASS

`test_phase7_4a_integrity_patch.py`: i 3 casi sintetici di clustering/overlap, nessuna coppia pseudo-indipendente residua nella INDEPENDENT_VIEW, Wilson rifiutato su outcome continuo (positivo e negativo), ogni outcome inferenziale con metodo p-value congelato, family_size FDR = numero reale di p-value generabili (21), nessun diagnostic-only nella famiglia BH, **comportamento del detector identico a v1** su fixture sintetica congelata nonostante l'hash del file sia cambiato (solo commenti), embargo non dichiarato correttamente rifiutato.

## File prodotti/modificati

Nuovi: `sequence_episode_engine.build_outcome_independent_view()` (estensione additiva), `engine/two_sample_bootstrap_test.py`, `build_seq0015_statistical_test_contract.py` + `seq0015_statistical_test_contract_v1.json`, `build_seq0015_frozen_spec_v2.py` + `phase7_4_seq0015_frozen_spec_v2.json`, `test_phase7_4a_integrity_patch.py`.

Modificati: `seq0015_momentum_burst_detector.py` (solo commenti/docstring), `policies/statistical_methods_policy.json` (nuova voce esplicita), `market_sequence_registry_v1.json` (terminologia corretta), `phase7_3_engine_readiness_gate_v1.json`/`phase7_3_red_team_v1.json` (rigenerati, nessun impatto - ancora READY_FOR_FIRST_SEQUENCE_DISCOVERY=true).

---

**NO REAL NEXUS OUTCOME DATA ACCESSED. NO SEQUENCE DISCOVERY EXECUTED.**

**Commit/push eseguiti. Il commit di questa patch (frozen spec v2) diventa il vero `preregistration_commit_sha` per Phase 7.4B. Nessuna Phase 7.4B senza nuova autorizzazione.**
