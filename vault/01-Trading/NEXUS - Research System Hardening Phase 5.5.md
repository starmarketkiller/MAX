# NEXUS - Research System Hardening Phase 5.5

Fase infrastrutturale: nessun nuovo edge cercato, nessuna strategia costruita, nessuna optimization, **SWEEP+RECLAIM non ri-validato**. Obiettivo: costruire i guardrail metodologici che Phase 5 non aveva ancora, e applicarli retroattivamente a Phase 5 stessa per vedere cosa avrebbero effettivamente catturato.

Tutti i numeri qui sono calcolati da codice reale eseguito su dati reali (`server/research_scripts/phase5_5/`), non stimati.

---

## 1-2. Hypothesis Registry + Experiment Registry

Implementazione: `build_hypothesis_registry.py` → `hypothesis_registry_v1.json` (15 ipotesi: 9 event-alone + 5 interazioni predefinite di Phase 5, più la validazione SAR). Regola di pre-registrazione dichiarata: il *detector* di ogni ipotesi era congelato ex-ante, ma la *promozione* di un'ipotesi a headline/EDGE_COMPONENT dopo averla vista performare meglio delle altre 13 nel batch è post-hoc nel senso rilevante per il multiple-testing.

**`H004_EVENT_RECLAIM` → status `POST_HOC_CANDIDATE`, non `SUPPORTED_EDGE`**, come richiesto esplicitamente. `pre_registered_detector=true`, `post_hoc_selection_from_batch=true`.

`experiment_registry_v1.json`: 7 esperimenti (dalla costruzione barre H4 fino al backtest SAR su Dukascopy), ciascuno con dataset/codice/feature/detector/baseline version, split, cost model, execution assumptions — sufficiente a ricostruire esattamente ogni run di Phase 5.

## 3. Multiple Testing Ledger

Implementazione: `build_multiple_testing_ledger.py` → `multiple_testing_ledger_v1.json`. **14 ipotesi testate, 107 confronti statistici totali** (8 per ipotesi in media: discovery, validation, BUY, SELL, fino a 4 anni), raggruppati in 4 famiglie comparabili (`FAMILY_DISCOVERY`, `FAMILY_VALIDATION`, `FAMILY_SUBGROUP_DIRECTION` n=28, `FAMILY_SUBGROUP_YEAR` n=51). Correzione Benjamini-Hochberg (q=0.10) applicata per famiglia con p-value reali (two-proportion z-test), non solo con l'overlap di CI usato in Phase 5.

**RECLAIM resta significativo dopo correzione**: p raw discovery ≈3.0e-12, validation ≈4.0e-08; adjusted-BH discovery ≈2.1e-11 (rank 2/14), validation ≈4.2e-07 (rank 1/14) — il guardrail multiple-testing NON refuta RECLAIM. Questo è dichiarato esplicitamente come **non sufficiente**: un p-value corretto per FDR non sostituisce una validazione indipendente pulita (sec.4). Ciò che oggi impedisce a RECLAIM di essere `SUPPORTED` non è la significatività statistica — è la contaminazione del processo di selezione.

## 4. Independent Validation Integrity

Tassonomia + classificazione completa: [[independent_validation_integrity_v1]]. **RECLAIM classificato `CONTAMINATED_VALIDATION`** — la selezione di RECLAIM come headline è avvenuta dopo aver visto i risultati di validazione di tutti e 14 i candidati nello stesso run. SAR (Phase 5.L) classificato `CROSS_FEED_VALIDATION` pulita — il segnale era congelato prima che il dataset Dukascopy esistesse.

## 5. Baseline Engine v2

Implementazione reale: `baseline_engine_v2.py`, dimostrata su RECLAIM (298/300 eventi matchati). Aggiunge nearest-neighbour su feature standardizzate (calibrate solo su discovery) sopra il matching coarsened di v1, con distanza e qualità di match esplicite per ogni osservazione. Distribuzione qualità: 92 GOOD, 197 FAIR, 9 POOR — nessun match POOR domina. Dettaglio: [[baseline_engine_v2_schema]].

## 6. Market Regime Layer

Implementazione reale: `build_regime_layer.py` → `regime_layer_v1.csv`/`regime_schema_v1.json`. 5 stati (HIGH_VOL/LOW_VOL/TRANSITION/TRENDING/RANGING) con priorità dichiarata ex-ante, soglie da quantili calcolati solo su discovery. Puramente descrittivo (non un segnale). Dettaglio: [[market_regime_layer_v1]].

## 7. Feature Provenance & Causality Registry

`feature_provenance_registry_v1.json`: tutte le 29 feature di Phase 5 documentate (formula/input/lookback/observation point/status causale/normalizzazione/missing-data policy/versione). **Tutte risultano `CAUSAL_SAFE`** — nessuna `UNKNOWN`, nessuna usata impropriamente in un test conclusivo.

## 8. Leakage Guard

Implementazione reale: `leakage_guard.py`, eseguita come audit retroattivo. **Verdetto: `LEAKAGE_GUARD_FAIL` — 1 problema confermato**: le soglie di cella per il baseline matching e per 3 delle 5 interazioni (`vol_terc`, `trend_terc`, `EFFICIENCY_TOP_TERCILE`, `VOL_BOTTOM_TERCILE`, `TREND_PERSISTENCE_MEDIAN` in `edge_discovery.py`) sono state calcolate sull'**intero dataset** (discovery+validation), non solo su discovery. Verificato dinamicamente (non solo asserito): scarto ~3-4% fra soglia realmente usata e soglia solo-discovery — piccolo in ampiezza, non corretto in questa fase (richiederebbe ri-eseguire l'edge discovery). Dettaglio: [[leakage_guard_v1]].

## 9. Feature Redundancy Audit

Calcolo reale (Pearson+Spearman) su tutte le 25 feature numeriche. 13 UNIQUE, 5 REDUNDANT (derivazione di formula nota, es. `mean_reversion_score = -lag1_autocorr_rolling`), 4 HIGHLY_CORRELATED (associazione empirica: trend e location nel range risultano correlati 0.79-0.95), 3 KEEP_FOR_INTERPRETABILITY. Nessuna feature rimossa. Dettaglio: [[feature_redundancy_audit_v1]].

## 10. Missing Data Policy

Regole esplicite per 7 tipi di gap, vietato forward-fill/zero-fill/drop silenzioso. Missingness reale calcolata: tutte le colonne con NaN confinate ai primi 75 bar (warmup, 1.56% massimo su `atr_percentile`), zero gap a metà serie. Dettaglio: [[missing_data_policy_v1]].

## 11-12. Execution Feasibility Layer + Signal-to-Fill Gap Audit

Schema PHENOMENON/EXECUTION definito, applicato retroattivamente a EC-LIQUIDITY_SWEEP_RECLAIM: `execution_status: NOT_TESTED` su tutte le dimensioni (spread/slippage/latenza/concorrenza/sessione). Metrica `SIGNAL_TO_FILL_GAP` definita, con i due precedenti diretti del progetto (WICK shadow/live mismatch, Volatility_Breakout entryRef mismatch) come casi di calibrazione. Dettagli: [[execution_feasibility_schema_v1]], [[signal_to_fill_gap_audit_v1]].

## 13. Cross-Market Data Interface

Schema per DXY/yields/silver/vol proxy/COT, nessuna fonte integrata. Regola critica dichiarata: per dati macro/positioning va usato il timestamp di **pubblicazione reale**, mai la data economica nominale (es. COT: venerdì di pubblicazione, non martedì di riferimento). Dettaglio: [[cross_market_data_interface_v1]].

## 14. Dataset Versioning

`dataset_version_v1.json`: `dataset_id` reale calcolato da hash SHA256 di dati e codice sorgente (non un numero incrementato a mano). Qualunque cambiamento a bar construction/feature/detector cambia l'hash automaticamente.

## 15-16. Evidence Grading + Research Decision Card

Scala E0-E6 definita. **RECLAIM assegnato E2 (INTERNAL_VALIDATION)** — non E3 per la contaminazione di sec.4. Research Decision Card compilata come esempio lavorato per RECLAIM. Dettaglio: [[evidence_grading_and_decision_card_v1]].

## 17. Reproducibility Test

Ri-eseguita l'intera pipeline (`build_h4_bars.py → build_market_state.py → build_events.py → build_outcomes.py → edge_discovery.py`) da codice committato, nessuna modifica, stesso dataset tick locale dichiarato (`dataset_version_v1.json`). Confrontati contro una copia dei risultati originali salvata prima del rerun.

**Risultato: `REPRODUCIBLE` — riproducibilità completa, non solo "entro tolleranza".**

| File | Righe orig. | Righe rerun | Byte-identico |
|---|---|---|---|
| `xauusd_h4_bars.csv` | 4810 | 4810 | ✅ (SHA256 identico) |
| `market_state_dataset_v1.csv` | 4810 | 4810 | ✅ |
| `events_v1.csv` | 8619 | 8619 | ✅ |
| `outcomes_v1.csv` | 8618 | 8618 | ✅ |

| Ipotesi | Classificazione orig. | Classificazione rerun | Diff numerici |
|---|---|---|---|
| BREAKOUT (risultato negativo) | NO_EDGE | NO_EDGE | 0 |
| RECLAIM | SUPPORTED_EDGE | SUPPORTED_EDGE | 0 |

Non è stata usata questa ri-esecuzione per ri-validare l'edge (nessuna nuova conclusione tratta) — serve solo a dimostrare che l'infrastruttura è deterministica e ricostruibile end-to-end dal solo codice committato più il dataset tick locale dichiarato (nessuna dipendenza nascosta da stato in memoria, ordine di esecuzione precedente, o file intermedi non tracciati).

---

## Risposte finali

**1. Quali failure modes potevano ancora produrre falsi edge?**
(a) Selezione post-hoc da un batch di ipotesi equivalenti presentata come conferma indipendente (il caso RECLAIM stesso). (b) Soglie di normalizzazione/matching calibrate sull'intero dataset invece che solo su discovery (trovato realmente da Leakage Guard). (c) Un fenomeno statistico reale ma non eseguibile, scambiato per un edge deployabile senza mai testare l'esecuzione (rischio ereditato, non ancora chiuso, per RECLAIM). (d) Un detector di evento mal calibrato che si attiva quasi sempre (PULLBACK, 83% delle barre) e produce risultati "NO_EDGE" non informativi ma che sembrano un test valido.

**2. Quali sono ora automaticamente bloccabili?**
Il Leakage Guard può bloccare (ha già bloccato in audit retroattivo) `center=True`, `.shift(-N)`, feature-che-vedono-outcome, e soglie fittate fuori dalla finestra di discovery dichiarata — questi diventano controlli meccanici, non revisioni umane a campione. Il Multiple Testing Ledger rende impossibile ignorare silenziosamente quante ipotesi/subgroup sono stati testati.

**3. Quali restano human-review only?**
La decisione se una promozione è avvenuta "prima o dopo" aver visto risultati di validazione (Independent Validation Integrity) richiede giudizio umano sul PROCESSO seguito, non è meccanicamente verificabile dal solo codice. La classificazione REDUNDANT vs HIGHLY_CORRELATED vs KEEP_FOR_INTERPRETABILITY nell'audit di ridondanza richiede giudizio di dominio (una correlazione alta non dice da sola se due feature "significano la stessa cosa" concettualmente). La valutazione di plausibilità economica di una nuova interazione predefinita (sec.F di Phase 5) resta intrinsecamente umana.

**4. Quali feature Phase 5 sono ridondanti?**
5 per derivazione di formula esatta: `ema_slope_atr_norm` (da `ema_slope_raw`), `dist_from_rolling_high_atr`, `dist_from_prev_day_high_atr`, `dist_from_prev_week_high_atr` (lati opposti degli equivalenti "low"), `mean_reversion_score` (da `lag1_autocorr_rolling`). Nessuna rimossa.

**5. Quanto è migliorata la qualità del baseline matching?**
Da "pool intero di cella, nessuna misura di similarità" (v1) a "distanza euclidea esplicita su feature standardizzate calibrate solo su discovery, classificazione di qualità per ogni osservazione" (v2) — su RECLAIM, 97% dei match sono GOOD o FAIR, nessuna dominanza di match POOR. Il miglioramento è di **osservabilità/auditabilità**, non ha cambiato il risultato numerico di Phase 5 (non ri-validato qui).

**6. SWEEP+RECLAIM che evidence grade riceve ORA?**
**E2 — INTERNAL_VALIDATION.** Non E3 perché la validazione è `CONTAMINATED_VALIDATION` (sec.4): la selezione è avvenuta dopo aver visto i risultati di validazione di tutti i 14 candidati del batch.

**7. Quali requisiti deve ancora superare prima di poter essere chiamato validated edge?**
In ordine, senza saltare passaggi: (1) **E3** — un vero test TRUE_HOLDOUT, ipotesi congelata singolarmente su un periodo mai osservato nemmeno in aggregato; (2) **E4** — conferma su fonte dati/simbolo indipendenti; (3) **E5** — `SIGNAL_TO_FILL_GAP` con modello di esecuzione realistico, data la storia diretta di un fenomeno gemello (WICK_SWEEP_RECLAIM) refutato esattamente su questo punto; (4) **E6** — solo dopo E5, conferma forward/demo.

---

## Artifact prodotti

- `server/research_scripts/phase5_5/hypothesis_registry_v1.json`
- `server/research_scripts/phase5_5/experiment_registry_v1.json`
- `server/research_scripts/phase5_5/multiple_testing_ledger_v1.json`
- `server/research_scripts/phase5_5/feature_provenance_registry_v1.json`
- `server/research_scripts/phase5_5/regime_schema_v1.json` + `regime_layer_v1.csv`
- `server/research_scripts/phase5_5/baseline_engine_v2_reclaim_demo.json`
- `server/research_scripts/phase5_5/leakage_guard_report_v1.json`
- `server/research_scripts/phase5_5/feature_redundancy_audit_v1.json`
- `server/research_scripts/phase5_5/dataset_version_v1.json`
- `server/research_scripts/phase5_5/reproducibility_report_v1.json`
- Documentazione: [[independent_validation_integrity_v1]], [[baseline_engine_v2_schema]], [[market_regime_layer_v1]], [[leakage_guard_v1]], [[feature_redundancy_audit_v1]], [[missing_data_policy_v1]], [[execution_feasibility_schema_v1]], [[signal_to_fill_gap_audit_v1]], [[cross_market_data_interface_v1]], [[evidence_grading_and_decision_card_v1]]
