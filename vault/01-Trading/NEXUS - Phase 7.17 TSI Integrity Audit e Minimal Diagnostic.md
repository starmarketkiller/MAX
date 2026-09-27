# NEXUS - Phase 7.17 — TSI Integrity Audit + Minimal Diagnostic

**Baseline:** `9d674e6` (Phase 7.16). Nessun lavoro concorrente rilevato. **Nessun nuovo run Tester pluriennale né breve lanciato** — la quantificazione riusa dati M15 reali già scaricati e disponibili localmente (Phase 7.13). Nessuna optimization, nessun confronto PF/WR, nessuna modifica a `MQL5/`, nessuna promozione live.

**Obiettivo**: determinare se il difetto già identificato su TSI (Phase 7.10, doppio smoothing EMA ricorsivo) altera materialmente l'identità della strategia e l'evidenza storica, con scope stretto.

---

## 1. Identità TSI congelata

`NXS_Strat_TSI()` (`NXS_Strategies.mqh:1366-1414`), selettore 5, profilo `PERIOD_D1`, stato globale singolo `g_tsiState` (non una coppia buy/sell come ORDER_BLOCK). **Nessuna guardia TF presente** — stessa forma strutturale di difetto di BREAKOUT_ACC/ORDER_BLOCK pre-fix. **Nessun wrapper/riuso** trovato (a differenza di OB_MIT per ORDER_BLOCK). Nessun gate a valle oltre SL/TP — il segnale contato è già quello finale pre-esecuzione. Motore Python (`backtest.py::sig_tsi/tsi_series`) dichiarato "fedele riga-per-riga" — single-TF per costruzione, quindi strutturalmente equivalente alla ricostruzione TF-scoped.

## 2. Meccanismo formalizzato matematicamente

TSI è un **filtro ricorsivo continuo** (IIR, doppio EMA), qualitativamente diverso dallo stato discreto "ricreabile" di ORDER_BLOCK: ogni evento di mutazione, anche non canonico, resta nella memoria del filtro **per sempre** (peso esponenziale mai nullo). Con ~450 eventi di mutazione/giorno contro il singolo evento D1 inteso, la "memoria di 25 periodi" (che dovrebbe coprire settimane) si comprime a **meno di un'ora** in tempo di calendario — un indicatore qualitativamente diverso, non solo perturbato. Predizione formale: la contaminazione deve essere **universale** (ogni lettura D1, non solo alcune date) — a differenza di ORDER_BLOCK.

## 3. Casi minimi

Valori attesi calcolati con **aritmetica razionale esatta** (`fractions.Fraction`, non la funzione sotto test). Sulla stessa barra D1 di chiusura (2020.0), con lo stesso prezzo: Stream A (2 eventi H4 contaminanti intermedi) produce TSI=41.390219; Stream B (TF-scoped) produce TSI=39.670850 — una divergenza del **valore dell'indicatore stesso**, non solo del segnale. L'implementazione float (`tsi_update()`) combacia con la reference esatta entro 1e-9.

## 4. Misura di materialità (dati reali già disponibili, nessun nuovo run)

Riusata la serie M15 reale 2023-10-02→2026-08-25 (Phase 7.13, 759 barre D1) — **nessun nuovo download/run Tester**, scelta esplicita giustificata dalla natura puramente matematica del meccanismo (già dimostrata deterministica con aritmetica esatta al punto 3, a differenza del branching su soglie di prezzo di ORDER_BLOCK).

- **68.407 mutazioni non canoniche** su 124.943 eventi totali (contro 60 raw trigger sul passaggio D1).
- **685/685 barre D1 (100%)** mostrano un TSI numericamente diverso fra Stream A e B — **conferma empirica esatta della predizione teorica di universalità**.
- Segnali generati: 60 (A) vs 61 (B), solo **3** coincidono su data+direzione — divergenza molto più estesa di quella di ORDER_BLOCK.

## 5. Fedeltà Python (nuova regola metodologica applicata)

Non presunta parity. Confronto leggero (dati già caricati, nessuna nuova campagna) fra il motore Python e la ricostruzione MQL5-fedele TF-scoped di questa fase: **100% delle barre D1 con TSI vicino** (entro 0.5), **tutti** i 61 segnali TF-scoped contenuti nei 67 segnali Python (6 extra, verosimilmente casi limite da differenza di seeding). Classificato **`PARTIAL_STRUCTURAL_MODEL`** (non `EVENT_LEVEL_PARITY_VALIDATED`) perché il confronto è Python-vs-Python, non contro un trace EA live reale (non raccolto in questa fase). Valido per mechanism research; mai valido per PF/redditività.

## 6. Evidenza storica

3 riferimenti MT5 reali trovati, tutti classificati **`POSSIBLY_CONTAMINATED`** (configurazione esatta non verificabile): sweep37 S05 (839 trade, PF 0.76, qualità dati "30% tick reali" — più bassa di quella usata per i diagnostici ORDER_BLOCK), `results/phase2_baseline_20260705` (15 trade, PF 0.51), `results/phase_partB_silent_diagnostic` (3874 pattern_fired). Motore Python: `UNAFFECTED_BUT_NOT_REPRESENTATIVE_OF_LIVE`. Nessun artifact cancellato, nessun PF reinterpretato economicamente.

## 7. Decisione finale

**`DEFECT_CONFIRMED_MATERIAL_IMPACT`**. **distortion_direction: `BOTH`** (sopprime e crea segnali, magnitudo quasi identica nelle due direzioni — a differenza di ORDER_BLOCK dove la creazione spuria dominava). **historical_evidence_integrity: `PARTIALLY_COMPROMISED_FOR_MT5_REAL_TICK_RESULTS`**. **confidence: `HIGH`** — meccanismo interamente deterministico/matematico, dimostrato con aritmetica esatta, effetto universale (100%) confermato su dati reali; unica riserva: nessun trace EA live reale raccolto (a differenza di ORDER_BLOCK).

## 8. Fix minimale proposto (NON applicato)

`if(tf != NXS_Profile_TF("TSI")) return s;` in `NXS_Strat_TSI()`, stessa forma di BREAKOUT_ACC/ORDER_BLOCK — nessun'altra identità da propagare (nessun wrapper). Invarianti, test, piano di parity e criteri di rollback documentati nell'artifact, stesso schema già usato per ORDER_BLOCK.

## Deliverables

`tsi_semantic_map_v1.json`, `tsi_mechanism_formalization_v1.json`, `nxs_tsi_replica.py`, `tsi_minimal_cases_v1.json`, `tsi_impact_comparison_v1.json`, `tsi_python_fidelity_v1.json`, `tsi_historical_evidence_map_v1.json`, `tsi_decision_card_v1.json`, 7 builder, verificatore indipendente (VERIFY OK), 31/31 test propri, questo vault report.

## Vincoli preservati

Nessun run Tester lanciato (né lungo né breve — la quantificazione riusa dati già disponibili). Nessuna modifica a `MQL5/`. Nessuna optimization, PF/WR o ricerca economica. Nessuna promozione live.

## Regressione

(compilata dopo l'esecuzione della suite completa)

---

```
7.16: ORDER_BLOCK CHIUSO (APPROXIMATION_WITH_KNOWN_GAPS)
7.17: TSI INTEGRITY AUDIT COMPLETATO
  meccanismo: filtro ricorsivo continuo, MAI autoriparante (diverso da
    ORDER_BLOCK) - formalizzato matematicamente
  caso minimo (aritmetica esatta): divergenza REALE del valore TSI,
    non solo del segnale
  dati reali gia' disponibili (nessun nuovo run): 100% delle barre D1
    con TSI diverso fra A e B - contaminazione UNIVERSALE, confermata
  Python: PARTIAL_STRUCTURAL_MODEL (non validato contro trace EA live)
DECISIONE: DEFECT_CONFIRMED_MATERIAL_IMPACT
DISTORSIONE: BOTH | CONFIDENCE: HIGH
FIX: proposto (stessa forma di BREAKOUT_ACC/ORDER_BLOCK), NON applicato
PROSSIMO: decisione dell'utente - autorizzare trace EA live reale
  (schema Phase 7.14) prima del fix, oppure procedere direttamente
```
