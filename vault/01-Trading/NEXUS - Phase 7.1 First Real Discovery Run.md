# NEXUS - Phase 7.1: First Real Discovery Run

**Baseline:** `5e3f726` (Phase 7.0B, READY_FOR_PHASE_7_1=true). Autorizzata esplicitamente dall'utente con vincoli precisi (vedi sotto). Obiettivo dichiarato: **validare il processo di discovery v2 su dati reali, non massimizzare il numero di edge trovati.**

**Verdetto finale: `NO_SUPPORTED_CANDIDATE`.**

Nessun candidato ha superato le gate minime nemmeno allo stadio di discovery screening - **nessuna lettura di internal_validation, locked_validation o final_holdout e' stata consumata** in questa run (verificabile: `validation_access_log_p71.json` e' vuoto). Questo e', per esplicita dichiarazione dell'utente, il risultato corretto quando nessun candidato regge.

---

## Limitazione dichiarata (riportata, non nascosta)

Come segnalato nella verifica di Phase 7.0B: il `dataset_version_hash` protegge manifest/versioni/provenance ma non e' un hash crittografico diretto di ogni file tick grezzo; il FINAL_HOLDOUT e' sigillato logicamente/proceduralmente, non a livello filesystem. Non ha bloccato questa run (il FINAL_HOLDOUT non e' comunque stato toccato), ma resta una limitazione aperta per fasi future.

## Pre-registrazione (frozen PRIMA di guardare il nuovo periodo)

File: `server/research_scripts/phase7/phase7_1/phase7_1_frozen_spec_v1.json`, scritto e congelato prima di calcolare qualunque outcome sul periodo 2023-02-04..2026-09-16.

- **Event family**: RECLAIM (detector di Phase 5, `build_events.py`, CFG identico, zero drift semantico - riusato letteralmente per la terza volta dopo Phase 5 e H006/Phase 6). Firing rate NORMAL (7.4% sul nuovo periodo, 6.2% storicamente) - non PATHOLOGICAL.
- **Primary outcome**: P(+1.0xATR before -1.0xATR), orizzonte 40 barre H4, ATR-normalizzato - identico a Phase 5/H006, riusando direttamente `phase5/edge_discovery.py:atr_outcome_for_bar` (nessuna reimplementazione).
- **Famiglia di candidati** (`RECLAIM_FAMILY_P71`, size=3, TUTTI pre-registrati insieme prima di guardare i dati - nessuna SELL asymmetry rescue possibile per costruzione): `CAND-P71-RECLAIM-BOTH`, `CAND-P71-RECLAIM-BUY`, `CAND-P71-RECLAIM-SELL`. Nessun nuovo "H007" creato - nomenclatura nativa v2 (candidate_id/family_id).
- **Baseline**: Baseline Engine v4 (reale, Phase 7.0B) - match_dimensions = 2 dimensioni coarsened (volatility_state/trend_state, terzili) + 3 numeriche standardizzate (directional_efficiency, position_in_rolling_range, roc), k=5, tutto fittato **solo** su development.discovery e congelato (verificato con test negativo: `FitIsolationViolation` su una riga di internal_validation).
- **Gate minime**: n>=30, ΔP>0 e >=0.15 (override pre-registrato, continuita' con H006), CI95 Wilson non sovrapposte, nessun evento con pool di controllo insufficiente, stabilita' EVENT/EPISODE view (dependence diagnostics v2).
- **Sequenza congelata**: discovery screening -> internal_validation (accesso LIMITED) -> locked_validation (accesso ONE-SHOT) -> final_holdout (ONE-SHOT, **solo se** un candidato raggiunge PASS su locked_validation).
- **No-rescue clause**: questi criteri non sono stati modificati dopo aver visto alcun risultato.

## Dati e infrastruttura riusati (Phase 5/6/7.0B, nessuna modifica)

- H4 bars: `phase7_1/build_h4_bars_p71.py` (copia del pattern Phase 6, path portabili) - 6179 barre (396 di buffer da Phase 6 holdout tail 2022-11-04..2023-02-03, contiguo senza gap; 5783 nel periodo 2023-02-04..2026-09-16).
- Market state: `phase7_1/build_market_state_p71.py` - copia verbatim di `phase5/build_market_state.py` (stessi parametri P, stesse garanzie causali).
- Eventi: `phase7_1/build_events_p71.py` - copia verbatim di `phase5/build_events.py` (stesso CFG). Tutte e 9 le famiglie rilevate (429 RECLAIM totali), ma **solo RECLAIM analizzata** in questa run.

## Risultati - Discovery Screening (development.discovery, 2023-02-04..2024-08-03, 2393 barre)

| Candidato | n eventi | ΔP | CI95 non sovrapposte | Dependence-sensitive | Esito |
|---|---|---|---|---|---|
| CAND-P71-RECLAIM-BOTH | 179 | **-0.0682** | No | **Si'** | Gate fallite |
| CAND-P71-RECLAIM-BUY | 102 | **-0.0706** | No | **Si'** | Gate fallite |
| CAND-P71-RECLAIM-SELL | 77 | **-0.0649** | No | **Si'** | Gate fallite |

Tutti e tre i candidati mostrano **ΔP negativo** (RECLAIM leggermente sotto il baseline matched, non sopra) e **CI95 Wilson sovrapposte** - due gate hard fallite indipendentemente da qualunque considerazione di dipendenza. Il segno e' **coerente fra BUY e SELL** (entrambi negativi, come l'aggregato) - nessuna asimmetria direzionale da "salvare": la SELL asymmetry storica (H006/Phase 6.5) semplicemente non e' ricomparsa su questo nuovo periodo, e non e' stata cercata per essere forzata a comparire.

**Nota metodologica di rilievo** (candidato BOTH, il piu' dettagliato): EVENT VIEW ΔP=-0.068, ma **EPISODE VIEW ΔP=+0.0098** (179 eventi nominali collassano a 72 episodi indipendenti) - un vero **cambio di segno** fra le due viste, esattamente il fenomeno per cui `dependence_diagnostics_v2.py` e' stato costruito in Phase 7.0. Senza questo controllo, un'analisi ingenua sull'EVENT VIEW avrebbe concluso "leggermente negativo, ma vicino a zero" senza sapere che la vista corretta (episodi indipendenti) e' leggermente positiva ma comunque troppo debole (+0.0098, ben sotto la soglia di materialita' 0.15) per contare come segnale. Il gate DEPENDENCE_SENSITIVE ha funzionato esattamente come progettato.

Multiple testing (BH-FDR, q=0.10, famiglia di 3): nessun candidato risulta `significant_at_q` (p-value grezzi 0.096/0.192/0.298, tutti sopra le soglie critiche BH) - conferma indipendente che nessuno dei tre supera nemmeno il filtro di significativita' grezza, prima ancora delle gate di materialita'/dipendenza.

**Nessun candidato e' avanzato a internal_validation.** Fasi 2 (internal_validation), 3 (locked_validation) e 4 (final_holdout) non sono state eseguite - `validation_access_log_p71.json` e' vuoto, verificabile direttamente.

## Failure memory check

Ciascuno dei 3 candidati e' stato verificato meccanicamente contro i pattern noti in `failure_memory_registry_v1.json` (SELECTION_AFTER_VALIDATION_RESULTS_VISIBLE, NORMALIZATION_FITTED_OUTSIDE_DISCOVERY_WINDOW, N_NOMINAL_FAR_ABOVE_CLUSTER_COUNT, BASELINE_NOT_DIRECTION_SEGMENTED_WHEN_DIRECTION_MATTERS, EVENT_FIRING_RATE_ABOVE_INFORMATIVE_THRESHOLD) - **nessun match**, con motivazione esplicita per ciascuno (vedi `phase7_1_evidence_records_v1.json`, campo `failure_memory_check`).

## Nota di processo (limite del lifecycle graph, osservato per la prima volta su dati reali)

`candidate_lifecycle.py` (Phase 7.0) non ammette una transizione diretta `DISCOVERY_SIGNAL -> DEPENDENCE_SENSITIVE` (solo `INSUFFICIENT_SAMPLE/CONTAMINATED/INTERNAL_VALIDATION` sono raggiungibili da li'). Un fallimento di discovery causato *specificamente* da dependence-sensitivity e' stato quindi registrato come `INSUFFICIENT_SAMPLE` con il motivo esplicito conservato nel testo della transizione, non come uno stato dedicato. Questo e' un limite di granularita' del grafo, non un bug che abbia falsato il risultato (il candidato falliva comunque su ΔP<=0 e CI sovrapposte, indipendentemente dalla dependence-sensitivity) - riportato qui per trasparenza, da considerare in un'eventuale Phase 7.1B/estensione del lifecycle.

## Deliverables

- `server/research_scripts/phase7/phase7_1/phase7_1_frozen_spec_v1.json` - pre-registrazione
- `server/research_scripts/phase7/phase7_1/build_h4_bars_p71.py`, `build_market_state_p71.py`, `build_events_p71.py` - riuso frozen code, path portabili
- `server/research_scripts/phase7/phase7_1/fit_frozen_baseline_params_p71.py` - fit discovery-only, test negativo incluso
- `server/research_scripts/phase7/phase7_1/candidate_stats_p71.py`, `run_phase7_1_discovery.py` - orchestratore reale (Baseline v4 + dependence v2 + multiple testing v2 + lifecycle + access ledger persistito su disco)
- `server/research_scripts/phase7/phase7_1/data/phase7_1_run_results.json` - risultati completi per fase/candidato
- `server/research_scripts/phase7/phase7_1/data/validation_access_log_p71.json` - **vuoto**, prova diretta che nessuno split di validazione e' stato letto
- `server/research_scripts/phase7/phase7_1/phase7_1_evidence_records_v1.json` - Evidence Record v2-compatibili per i 3 candidati (grade E1, conclusion REFUTED_AT_DISCOVERY)
- `server/research_scripts/phase7/phase7_1/phase7_1_decision_card_v1.json` - decision card sintetica

## Vincoli rispettati

Una sola discovery family congelata (RECLAIM); candidate generation policy gia' definita (Level 0, nessuna nuova dimensione); nessun nuovo H007 (nomenclatura v2 nativa); nessun accesso a FINAL_HOLDOUT (mai raggiunto); nessuna modifica a soglie/outcome dopo aver visto risultati (no-rescue clause rispettata); nessun post-hoc finding promosso; dependence diagnostics obbligatori (eseguiti, e determinanti - hanno rivelato il cambio di segno EVENT/EPISODE); matched baseline v4 obbligatoria (usata); multiple testing/FDR applicati; failure memory attiva (verificata, nessun match); nessuna parameter optimization (k=5 e soglie fissati a priori); nessuna SELL asymmetry rescue (SELL testata onestamente insieme a BUY/BOTH fin dall'inizio, risultato negativo come gli altri due).

## Conclusione

Il Discovery Engine v2 ha funzionato esattamente come progettato: ha testato una famiglia pre-registrata con rigore statistico completo (baseline matched, dipendenza, FDR), ha rilevato un fenomeno metodologicamente interessante (inversione di segno EVENT/EPISODE view) invece di ignorarlo, e si e' fermato correttamente PRIMA di consumare risorse di validazione preziose su un segnale che non le meritava. **NO_SUPPORTED_CANDIDATE** e' il risultato onesto di questa run - non un fallimento del processo, ma la dimostrazione che il processo sa dire "no" quando i dati non sostengono un effetto, invece di trovare sempre qualcosa da promuovere.
