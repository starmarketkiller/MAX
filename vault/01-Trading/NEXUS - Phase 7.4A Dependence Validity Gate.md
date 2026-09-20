# NEXUS - Phase 7.4A Dependence Validity Gate

**Baseline:** `14911a6` (Phase 7.4A Final Statistical Integrity Patch). Patch circoscritta: trasforma la null-calibration simulation in una **guardia automatica del motore** - nessuna discovery eseguita, nessun dato NEXUS letto, detector/P90/252/direction/episode gap/embargo 39/matched baseline/control reuse cap/outcome definitions **tutti invariati** (verificato programmaticamente).

**Conferma esplicita: NO REAL NEXUS OUTCOME DATA ACCESSED. NO SEQUENCE DISCOVERY EXECUTED.**

---

## 1-2. Dependence Validity State + diagnostica congelata ex-ante

Tre stati (`engine/dependence_validity_gate.py`): **`INFERENCE_VALID`**, **`DEPENDENCE_SENSITIVE`**, **`INFERENCE_INVALID_DEPENDENCE`**, classificati sulla serie `d_i = outcome(event_i) - mean(matched_controls_i)` della INDEPENDENT_VIEW. Diagnostica congelata **prima** di guardare qualunque dato NEXUS: ACF lag 1, Ljung-Box su h=3 lag (formula chiusa, nessuna libreria esterna), Effective Sample Size (rapporto varianza block-vs-iid bootstrap, riuso di `block_bootstrap.py`), skewness campionaria (per il flag `ASYMMETRY_SENSITIVE`, sec.7).

## 3. Calibration curve φ=0.0→0.7

| φ | Type-I@.01 | Type-I@.05 | Type-I@.10 | mean\|ACF1\| | mean LB-p | mean ESS/n | Gate (maggioranza) |
|---|---|---|---|---|---|---|---|
| 0.0 | .005 | **.048** | .100 | 0.137 | 0.505 | 1.294 | INFERENCE_VALID (68%) |
| 0.1 | .007 | **.048** | .096 | 0.146 | 0.492 | 1.118 | INFERENCE_VALID (66%) |
| 0.2 | .012 | **.060** | .114 | 0.183 | 0.417 | 0.984 | INFERENCE_VALID (51%) |
| 0.3 | .016 | **.062** | .118 | 0.247 | 0.324 | 0.841 | DEPENDENCE_SENSITIVE (57%) |
| 0.5 | .036 | **.096** | .166 | 0.403 | 0.144 | 0.648 | DEPENDENCE_SENSITIVE (46%) |
| 0.7 | .058 | **.155** | .224 | 0.577 | 0.037 | 0.492 | INFERENCE_INVALID_DEPENDENCE (82%) |

Relazione **monotona e coerente**: il gate diventa via via più severo esattamente dove il Type-I error empirico si allontana dal nominale. A φ=0.3 (inflazione ancora modesta, ~1.24×) il gate **già** segnala prevalentemente `DEPENDENCE_SENSITIVE` - postura deliberatamente cauta (fail-closed preferisce falsi allarmi a falsi negativi). Nota di trasparenza: il gate è valutato **una volta sola** sulla serie osservata reale, non mediato su repliche - a φ=0.0 c'è comunque una probabilità non nulla (~31%) che il gate segnali cautela anche su dati davvero iid, per via del rumore campionario della diagnostica stessa a n=30; è il prezzo di una policy fail-closed, dichiarato esplicitamente.

## 4. Regola fail-closed congelata

```
INFERENCE_VALID              -> p-value grezzo entra in BH-FDR, può produrre un verdetto di discovery
DEPENDENCE_SENSITIVE          -> p-value sostituito con 1.0 in BH-FDR; resta riportato come diagnostica,
                                  MAI un verdetto di discovery
INFERENCE_INVALID_DEPENDENCE  -> stesso trattamento numerico (p=1.0) + blocco esplicito della cella,
                                  nessuna ulteriore valutazione di quell'outcome per quel candidato
```

Applicato da `engine/dependence_gated_bh_family.py:build_gated_bh_family` **prima** di chiamare `multiple_testing_v2.benjamini_hochberg` (riusato senza modifiche). `eligible_for_discovery_verdict` è vero **solo se** `INFERENCE_VALID AND significant_at_q` - verificato con un caso sintetico dove una cella fortemente autocorrelata con un apparente effetto forte **non risulta mai** eligible, indipendentemente dal suo p-value grezzo.

## 5. Granularità: candidate × outcome

Il gate è applicato a **ciascuna delle 21 celle** (3 candidati × 7 outcome) indipendentemente - la dipendenza in MFE può differire da quella in un outcome binario o in TIME_TO_MFE, ciascuna ha la propria classificazione.

## 6. FDR denominator - nessuna riduzione opportunistica

**`family_size = 21` sempre**, mai ridotta dopo aver visto quali celle falliscono il gate. Le celle non `INFERENCE_VALID` ricevono `p=1.0` (mai rimosse dalla lista passata a `benjamini_hochberg`) - verificato con un test che asserisce `m_family` restituito coincide sempre con la family_size dichiarata, su un mix eterogeneo di 21 celle sintetiche.

## 7. Sign-flip assumption

Documentata esplicitamente: sotto H0 la distribuzione di `d_i` deve essere **sufficientemente simmetrica/scambiabile** rispetto al cambio di segno, non solo avere media zero. La simulazione "skewed" mostra una lieve anti-conservatività (rej@.05=0.063, rej@.10=0.118 - non grave come φ=0.7 ma reale, riportata correttamente). Aggiunto flag `ASYMMETRY_SENSITIVE` (skewness campionaria ≥0.75) riportato accanto allo stato principale.

## 8. Correzione shared-regime

**Errore precedente**: il report descriveva `rejection_rate=0%` del metodo OLD come possibile effetto di "varianza sottostimata... che può rendere il test anti-conservativo" - è l'esatto opposto. **Corretto**: 0% di rigetto è fortemente **conservativo/powerless**. Il bootstrap ricampiona evento e baseline separatamente, trattando come incertezza una componente di varianza (lo shock di regime condiviso) che nel dato osservato si cancella per costruzione - producendo un CI troppo ampio, mai troppo stretto in questo scenario specifico. **La conclusione valida resta invariata**: appiattire la struttura matched produce un'inferenza mal calibrata, a volte anti-conservativa (i 4 scenari base) a volte fortemente conservativa/powerless (shared-regime) - non prevedibile a priori in quale direzione, il che la rende inaffidabile in entrambi i casi. Corretto in `null_calibration_simulation.py` (rigenerato) e con una nota di trasparenza (non riscrittura silenziosa) nel report della patch precedente.

## 9. Frozen spec v4

`phase7_4_seq0015_frozen_spec_v4.json`, **v1/v2/v3 lasciati intatti**. `supersedes: v3`. Verificato **programmaticamente**: 0 diff su formula/soglia/direction, 0 diff su episode_rule/embargo, 0 diff su control_reuse_policy/outcome contract rispetto a v3 (questa patch tocca solo il gate di dipendenza).

- **detector_source_hash (v4)**: `7ed4f8e9443f1a8b77f0455a421fbbcb513b694655aa4d0278378feb7ec4b2bf` (identico a v3 - file non toccato)
- **frozen_parameters_hash (v4)**: `6c7c15c8c1756483d3ed3d237e5695c3cdfb5b89e3fbdf538c79db343b4fda33` (identico a v3, stesso motivo)
- Validata al 100% contro lo schema esistente (nessuna modifica allo schema necessaria)
- `preregistration_provenance_guard` verificato bloccare v4 finché non committata

## Regression tests - 26/26 PASS

`test_phase7_4a_dependence_validity_gate.py`: calibration curve monotona e presente, gate classifica correttamente iid=valido/AR(1) forte=non-valido, DEPENDENCE_SENSITIVE/INFERENCE_INVALID_DEPENDENCE→p=1.0, family_size mai ridotta, v1/v2/v3 mai toccati, v4 supersede v3 con tutti gli invarianti verificati, correzione shared-regime confermata nel testo. Nessuna regressione: Phase 7.3 (12/12+10/10), Phase 7.4A Integrity Patch (11/11), Phase 7.4A Final Statistical Patch (20/20) tutti ancora PASS.

## File prodotti/modificati

Nuovi: `engine/dependence_validity_gate.py`, `engine/dependence_gated_bh_family.py`, `dependence_validity_gate_calibration.py` + `phase7_4_dependence_gate_calibration_v1.json`, `build_seq0015_frozen_spec_v4.py` + `phase7_4_seq0015_frozen_spec_v4.json`, `test_phase7_4a_dependence_validity_gate.py`.

Modificati: `null_calibration_simulation.py` + `phase7_4_null_calibration_v1.json` (interpretazione shared-regime corretta, numeri invariati nella sostanza), nota di correzione aggiunta al report della patch precedente.

---

**NO REAL NEXUS OUTCOME DATA ACCESSED. NO SEQUENCE DISCOVERY EXECUTED.**

**Commit/push eseguiti. Il commit di questa patch (frozen spec v4) diventa il vero `preregistration_commit_sha` per Phase 7.4B. Nessuna Phase 7.4B senza nuova autorizzazione.**
