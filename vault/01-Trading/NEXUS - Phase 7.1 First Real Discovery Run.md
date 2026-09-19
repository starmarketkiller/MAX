# NEXUS - Phase 7.1: First Real Discovery Run

**Baseline:** `5e3f726` (Phase 7.0B, READY_FOR_PHASE_7_1=true). Autorizzata esplicitamente dall'utente con vincoli precisi (vedi sotto). Obiettivo dichiarato: **validare il processo di discovery v2 su dati reali, non massimizzare il numero di edge trovati.**

**Verdetto finale: `NO_SUPPORTED_CANDIDATE`.**

Nessun candidato ha superato le gate minime nemmeno allo stadio di discovery screening - **nessuna lettura di internal_validation, locked_validation o final_holdout e' stata consumata** in questa run (verificabile: `validation_access_log_p71.json` e' vuoto, e da questa revisione anche tramite `phase7_1_validation_access_evidence_v1.json`, artifact versionato indipendente da quel file locale). Questo e', per esplicita dichiarazione dell'utente, il risultato corretto quando nessun candidato regge.

> **Integrity & Provenance Patch (post-review, 2026-09-19)** applicata dopo la prima stesura di questo report - vedi sezione dedicata in fondo. Tre correzioni: (1) provenance della pre-registrazione dichiarata esplicitamente (non provabile solo da Git in questo commit), (2) evidenza di accesso alla validazione resa un artifact versionato indipendente dal ledger locale, (3) stato lifecycle dei 3 candidati corretto da `INSUFFICIENT_SAMPLE` a **`REFUTED`** (nessun numero, ΔP, o verdetto complessivo modificato).

**declared_frozen_before_outcomes = true** · **git_independently_proves_pre_registration_order = false** (vedi sezione Integrity Patch)

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

| Candidato | n eventi | ΔP | CI95 non sovrapposte | Dependence-sensitive | Stato lifecycle finale |
|---|---|---|---|---|---|
| CAND-P71-RECLAIM-BOTH | 179 | **-0.0682** | No | Si' (diagnostico) | **REFUTED** |
| CAND-P71-RECLAIM-BUY | 102 | **-0.0706** | No | Si' (diagnostico) | **REFUTED** |
| CAND-P71-RECLAIM-SELL | 77 | **-0.0649** | No | Si' (diagnostico) | **REFUTED** |

Stato lifecycle corretto dall'Integrity & Provenance Patch (vedi sezione dedicata): tutti e 3 i candidati sono `REFUTED` per DeltaP<=0 - la dependence-sensitivity resta un fatto diagnostico rilevante (vedi sotto) ma non e' la ragione primaria della classificazione, per la regola di precedenza in `engine/discovery_gate_precedence.py`.

Tutti e tre i candidati mostrano **ΔP negativo** (RECLAIM leggermente sotto il baseline matched, non sopra) e **CI95 Wilson sovrapposte** - due gate hard fallite indipendentemente da qualunque considerazione di dipendenza. Il segno e' **coerente fra BUY e SELL** (entrambi negativi, come l'aggregato) - nessuna asimmetria direzionale da "salvare": la SELL asymmetry storica (H006/Phase 6.5) semplicemente non e' ricomparsa su questo nuovo periodo, e non e' stata cercata per essere forzata a comparire.

**Nota metodologica di rilievo** (candidato BOTH, il piu' dettagliato): EVENT VIEW ΔP=-0.068, ma **EPISODE VIEW ΔP=+0.0098** (179 eventi nominali collassano a 72 episodi indipendenti) - un vero **cambio di segno** fra le due viste, esattamente il fenomeno per cui `dependence_diagnostics_v2.py` e' stato costruito in Phase 7.0. Senza questo controllo, un'analisi ingenua sull'EVENT VIEW avrebbe concluso "leggermente negativo, ma vicino a zero" senza sapere che la vista corretta (episodi indipendenti) e' leggermente positiva ma comunque troppo debole (+0.0098, ben sotto la soglia di materialita' 0.15) per contare come segnale. Il gate DEPENDENCE_SENSITIVE ha funzionato esattamente come progettato.

Multiple testing (BH-FDR, q=0.10, famiglia di 3): nessun candidato risulta `significant_at_q` (p-value grezzi 0.096/0.192/0.298, tutti sopra le soglie critiche BH) - conferma indipendente che nessuno dei tre supera nemmeno il filtro di significativita' grezza, prima ancora delle gate di materialita'/dipendenza.

**Nessun candidato e' avanzato a internal_validation.** Fasi 2 (internal_validation), 3 (locked_validation) e 4 (final_holdout) non sono state eseguite - `validation_access_log_p71.json` e' vuoto, verificabile direttamente.

## Failure memory check

Ciascuno dei 3 candidati e' stato verificato meccanicamente contro i pattern noti in `failure_memory_registry_v1.json` (SELECTION_AFTER_VALIDATION_RESULTS_VISIBLE, NORMALIZATION_FITTED_OUTSIDE_DISCOVERY_WINDOW, N_NOMINAL_FAR_ABOVE_CLUSTER_COUNT, BASELINE_NOT_DIRECTION_SEGMENTED_WHEN_DIRECTION_MATTERS, EVENT_FIRING_RATE_ABOVE_INFORMATIVE_THRESHOLD) - **nessun match**, con motivazione esplicita per ciascuno (vedi `phase7_1_evidence_records_v1.json`, campo `failure_memory_check`).

## Integrity & Provenance Patch (post-review, 2026-09-19)

Una revisione diretta di `f9bfd68` (commit della stesura originale di Phase 7.1) ha trovato 3 problemi, corretti come segue - **nessuna nuova discovery, nessuna nuova event family, nessun accesso a validation/locked/final holdout**.

### 1. Provenance della pre-registrazione

`phase7_1_frozen_spec_v1.json` e i risultati sono stati committati nello **stesso commit** (`f9bfd68`). La dichiarazione "congelato prima di guardare i dati" resta vera (verificabile dal contenuto del file e dalla sequenza di esecuzione reale), ma **Git da solo non puo' provare indipendentemente l'ordine temporale** quando i due oggetti condividono un commit. Distinzione ora esplicita, riportata in evidence/decision card e in cima a questo report:

- `declared_frozen_before_outcomes = true`
- `git_independently_proves_pre_registration_order = false`

**Regola obbligatoria per tutte le future discovery run**: `PRE-REGISTRATION COMMIT -> RUN -> RESULT COMMIT`. Implementata tecnicamente in `engine/preregistration_provenance_guard.py` (`assert_frozen_spec_committed_before_run`) - una futura run deve rifiutarsi di partire se il proprio frozen spec non e' gia' un file tracciato e pulito (nessuna modifica non committata) rispetto a HEAD. Non e' una prova crittografica del "quando" (Git non registra quello) - e' un vincolo procedurale che forza strutturalmente il frozen spec in un commit separato e antecedente. Verificato con 3 casi (positivo: file gia' committato passa e ritorna uno SHA; negativo: file mai committato bloccato; negativo: file con modifiche non committate bloccato).

### 2. Evidenza di accesso alla validazione, resa verificabile dal commit

`validation_access_log_p71.json` vive sotto `phase7_1/data/`, esclusa da `.gitignore` - non verificabile dal solo repository. Prodotto `phase7_1_validation_access_evidence_v1.json` (versionato, committato), derivato meccanicamente dal ledger reale locale (mai inventato): run_id, candidate_ids, riepilogo accesso discovery (ITERABLE, non tracciato per policy), conteggio accessi per candidato per internal_validation/locked_validation/final_holdout (tutti **0**), hash del contenuto del ledger locale (`4f53cda1...`, hash di una lista vuota), verdetto **`NO_VALIDATION_SPLIT_CONSUMED`** calcolato (non dichiarato) dal conteggio.

### 3. Semantica del lifecycle

Bug: `candidate_lifecycle.py` non ammetteva transizioni dirette `DISCOVERY_SIGNAL -> REFUTED` ne' `-> DEPENDENCE_SENSITIVE` - la Fase 1 originale usava quindi `INSUFFICIENT_SAMPLE` per QUALUNQUE fallimento di discovery, anche con campione ampiamente adeguato (n=77-179) che falliva per ΔP<=0. Corretto:

- Aggiunte le uscite dirette `REFUTED`, `DEPENDENCE_SENSITIVE`, `BORDERLINE` da `DISCOVERY_SIGNAL` (e `BORDERLINE` anche da `INTERNAL_VALIDATION`, per coerenza).
- Nuovo modulo `engine/discovery_gate_precedence.py` con una regola di **precedenza esplicita** (dal motivo piu' fondamentale al meno): pool di controllo insufficiente > n sotto il minimo > ΔP<=0 (**REFUTED**) > dependence-sensitive (**DEPENDENCE_SENSITIVE**) > sotto la soglia di materialita' o CI sovrapposte (**BORDERLINE**). Verificata con 6 casi + 1 caso negativo (chiamata su un candidato che non fallisce nulla -> `ValueError`, mai un default silenzioso).
- **Per questa run**: tutti e 3 i candidati hanno ΔP negativo -> la precedenza assegna **REFUTED** a tutti e 3 (non `INSUFFICIENT_SAMPLE`), indipendentemente dalla dependence-sensitivity osservata (che resta un fatto diagnostico riportato, non la causa della classificazione).
- Corretti retroattivamente `phase7_1_evidence_records_v1.json` e `phase7_1_decision_card_v1.json` (script `apply_lifecycle_correction_p71.py`, idempotente - rifiuta una seconda applicazione) usando **gli stessi numeri gia' calcolati** (ΔP, n, CI, dependence_flag) - nessun ricalcolo statistico, nessun accesso a dati. Verificato che ogni nuova transizione sia meccanicamente valida nel grafo esteso (non solo asserita) e che il verdetto complessivo resti `NO_SUPPORTED_CANDIDATE`.
- Corretta anche la precedenza nel codice sorgente di `run_phase7_1_discovery.py` (Fase 1/2/3, per le run future - il bug di precedenza nella Fase 2 originale, mai esercitata in questa run, e' stato corretto senza essere mai stato eseguito su dati reali).

### Regression test aggiunti

- `engine/discovery_gate_precedence.py`: n adeguato+ΔP<0 -> REFUTED; fallimento solo-dipendenza -> DEPENDENCE_SENSITIVE; n genuinamente basso -> INSUFFICIENT_SAMPLE; pool insufficiente -> INSUFFICIENT_SAMPLE; ΔP positivo sotto materialita' -> BORDERLINE; CI sovrapposte -> BORDERLINE; chiamata senza gate fallite -> `ValueError`.
- `engine/preregistration_provenance_guard.py`: file committato e pulito -> OK con SHA; file mai committato -> bloccato; file con modifiche non committate -> bloccato (verifica ripristinata immediatamente, nessuna modifica lasciata sul repo).
- `phase7_1/build_validation_access_evidence.py`: ledger vuoto -> `NO_VALIDATION_SPLIT_CONSUMED`; ledger sintetico non vuoto -> conteggi corretti e `VALIDATION_SPLIT_ACCESSED` (prova che la logica conta davvero, non restituisce sempre "vuoto").
- `engine/candidate_lifecycle.py`: dimostrazioni dirette `DISCOVERY_SIGNAL -> REFUTED` e `DISCOVERY_SIGNAL -> DEPENDENCE_SENSITIVE`, piu' l'invariante generale su tutti gli stati (gia' presente, riverificata).

**Numeri, ΔP, n, CI, verdetto complessivo (`NO_SUPPORTED_CANDIDATE`) - tutti invariati.** Solo le etichette di stato e la loro motivazione sono cambiate.

## Deliverables

- `server/research_scripts/phase7/phase7_1/phase7_1_frozen_spec_v1.json` - pre-registrazione
- `server/research_scripts/phase7/phase7_1/build_h4_bars_p71.py`, `build_market_state_p71.py`, `build_events_p71.py` - riuso frozen code, path portabili
- `server/research_scripts/phase7/phase7_1/fit_frozen_baseline_params_p71.py` - fit discovery-only, test negativo incluso
- `server/research_scripts/phase7/phase7_1/candidate_stats_p71.py`, `run_phase7_1_discovery.py` - orchestratore reale (Baseline v4 + dependence v2 + multiple testing v2 + lifecycle + access ledger persistito su disco)
- `server/research_scripts/phase7/phase7_1/data/phase7_1_run_results.json` - risultati completi per fase/candidato
- `server/research_scripts/phase7/phase7_1/data/validation_access_log_p71.json` - **vuoto**, prova diretta che nessuno split di validazione e' stato letto
- `server/research_scripts/phase7/phase7_1/phase7_1_evidence_records_v1.json` - Evidence Record v2-compatibili per i 3 candidati (grade E1, conclusion REFUTED_AT_DISCOVERY, corretto dall'Integrity Patch)
- `server/research_scripts/phase7/phase7_1/phase7_1_decision_card_v1.json` - decision card sintetica (corretta dall'Integrity Patch)
- `server/research_scripts/phase7/phase7_1/phase7_1_validation_access_evidence_v1.json` - evidenza di accesso alla validazione, versionata (Integrity Patch)
- `server/research_scripts/phase7/engine/discovery_gate_precedence.py` - regola di precedenza per la classificazione dei fallimenti (Integrity Patch)
- `server/research_scripts/phase7/engine/preregistration_provenance_guard.py` - enforcement PRE-REGISTRATION COMMIT -> RUN -> RESULT COMMIT per le run future (Integrity Patch)
- `server/research_scripts/phase7/phase7_1/apply_lifecycle_correction_p71.py` - script di correzione retroattiva (idempotente), applicato una volta (Integrity Patch)

## Vincoli rispettati

Una sola discovery family congelata (RECLAIM); candidate generation policy gia' definita (Level 0, nessuna nuova dimensione); nessun nuovo H007 (nomenclatura v2 nativa); nessun accesso a FINAL_HOLDOUT (mai raggiunto); nessuna modifica a soglie/outcome dopo aver visto risultati (no-rescue clause rispettata); nessun post-hoc finding promosso; dependence diagnostics obbligatori (eseguiti, e determinanti - hanno rivelato il cambio di segno EVENT/EPISODE); matched baseline v4 obbligatoria (usata); multiple testing/FDR applicati; failure memory attiva (verificata, nessun match); nessuna parameter optimization (k=5 e soglie fissati a priori); nessuna SELL asymmetry rescue (SELL testata onestamente insieme a BUY/BOTH fin dall'inizio, risultato negativo come gli altri due).

## Conclusione

Il Discovery Engine v2 ha funzionato esattamente come progettato: ha testato una famiglia pre-registrata con rigore statistico completo (baseline matched, dipendenza, FDR), ha rilevato un fenomeno metodologicamente interessante (inversione di segno EVENT/EPISODE view) invece di ignorarlo, e si e' fermato correttamente PRIMA di consumare risorse di validazione preziose su un segnale che non le meritava. **NO_SUPPORTED_CANDIDATE** e' il risultato onesto di questa run - non un fallimento del processo, ma la dimostrazione che il processo sa dire "no" quando i dati non sostengono un effetto, invece di trovare sempre qualcosa da promuovere.
