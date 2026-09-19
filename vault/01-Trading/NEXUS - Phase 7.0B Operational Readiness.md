# NEXUS - Phase 7.0B: Operational Readiness for Discovery Engine v2

**Baseline:** `a2eb10e` (Phase 7.0 Architecture + Integrity Patch, chiusa). Questa fase trasforma il design in un motore operativamente pronto - **non** ha eseguito alcuna discovery run, nessun H007, nessun nuovo edge, nessun backtest strategico, nessuna parameter optimization. Il nuovo dataset (2023-02-04 → 2026-09-16) e' stato trattato SOLO come infrastruttura da acquisire e validare, mai come occasione per guardare risultati di edge (sec.19).

---

## 1. Baseline Engine v4 e' realmente implementato o ancora solo contrattuale?

**Realmente implementato.** `server/research_scripts/phase7/engine/baseline_engine_v4.py` - non piu' solo il contratto (`baseline_contract_v4.json`, Phase 7.0). Rispetta tutte e sei le proprieta' obbligatorie: direction-aware (un evento riceve solo controlli della stessa direzione - verificato nel preflight, check `baseline_v4_direction_mismatch_blocked`), temporally/split-safe (filtro interno + difesa in profondita' via `cross_split_safety.validate_baseline_matches` chiamata realmente dentro `match()`, non lasciata come utility separata - sec.15), state-matched su dimensioni dichiarate esplicitamente (mai aggiunte automaticamente), discovery-fitted-only (`fit_normalization()` solleva `FitIsolationViolation` se chiamato su righe fuori dal discovery split), auditabile (ogni match registra event/control id, split, direzione, distanza standardizzata, qualita', versione feature, versione contratto). `baseline_quality_report_v4.json` prodotto su fixture sintetiche: 128/128 eventi matchati, 640 match tutti GOOD (nessuna dimensione numerica dichiarata in questa demo, quindi distanza triviale - il preflight esercita separatamente uno scenario con dimensione numerica dispersa per forzare e verificare la rilevazione di match POOR, check `baseline_v4_poor_match_overload_flagged`).

## 2. Come viene impedito il cross-split matching?

Doppio livello: (1) `BaselineEngineV4.match()` filtra il pool di controllo allo split dell'evento PRIMA di calcolare qualunque distanza; (2) come difesa in profondita', ogni set di match risultante viene ri-verificato chiamando `cross_split_safety.validate_baseline_matches()`, che solleverebbe `CrossSplitViolation` se, nonostante il filtro, un controllo cross-split fosse presente. Il preflight dimostra entrambi i livelli: `baseline_v4_cross_split_blocked` passa un pool "contaminato" con righe di altri split e verifica che NESSUN match risultante le contenga; il red-team finale attacca direttamente `cross_split_safety.validate_baseline_matches()` e conferma il blocco (`CrossSplitViolation`).

## 3. Come viene classificato e bloccato un detector patologicamente permissivo?

`engine/event_firing_rate_guard.py` classifica ogni event family in SPARSE/NORMAL/HIGH/PATHOLOGICAL in base al firing_rate (soglie dichiarate `POLICY_THRESHOLD`: <2% SPARSE, <15% NORMAL, <40% HIGH, altrimenti PATHOLOGICAL). Applicato ai detector REALI di Phase 5 (`build_event_detector_health_v1.py`, solo conteggi/row_index da `events_v1.csv` - **zero outcome/ΔP calcolato**, conforme a sec.19): **PULLBACK risulta PATHOLOGICAL (firing_rate=82.9%, `allowed_for_discovery=False`)** - conferma quantitativa esatta del problema gia' osservato qualitativamente in Phase 5.5 (FAIL-004, "83% delle barre"). VOLATILITY_EXPANSION (37.1%) e BREAKOUT (15.1%) risultano HIGH (ammessi ma segnalati per revisione); SWEEP, RECLAIM e gli altri 5 detector risultano NORMAL. Il blocco e' meccanico, non solo descrittivo: `assert_allowed_for_discovery()` solleva `DetectorNotAllowedForDiscovery` per PULLBACK - dimostrato sia nel preflight sia nel red-team finale (attacco `pathological_detector_used_for_discovery`, BLOCKED).

## 4. Come viene impedito il riuso di locked validation e holdout?

`engine/validation_access_ledger.py` legge `policies/validation_access_policy_v1.json` (unica fonte di verita', mai duplicata a mano nel codice - lezione diretta dell'Integrity Patch di Phase 7.0) e applica enforcement REALE, non solo logging: `locked_validation` e `final_holdout` sono `ONE_SHOT` (max 1 lettura per candidate_id), `internal_validation` e' `LIMITED` (max 3), `discovery` e' `ITERABLE` (nessun limite). Un secondo accesso oltre il limite solleva `ValidationAccessViolation`, salvo un'eccezione esplicita e motivata (`allow_contaminated_reentry=True` + `prior_state` in `{CONTAMINATED,REUSED}` + `reentry_reason` scritta - mai un'eccezione silenziosa). Verificato nel preflight (check 22-23) e nel red-team finale (`holdout_second_read`, `validation_reuse_beyond_limit`, entrambi BLOCKED).

## 5. Come viene rilevato il dataset drift?

`engine/dataset_version_guard.py`: l'hash di un dataset e' calcolato da componenti dichiarati (hash del manifest sorgente, date range, strumento, timeframe, versione di trasformazione) - MAI dal contenuto grezzo dei tick. `DatasetVersionRegistry.register_or_check()` confronta l'hash appena calcolato con quello registrato per lo stesso `dataset_id`: se un componente cambia (es. il manifest sorgente e' stato alterato), lo stato risulta `DATASET_VERSION_DRIFT` invece di essere trattato silenziosamente come lo stesso dataset. `assert_no_drift()` solleva `DatasetVersionDriftError` per un uso "fail-hard". Testato con un rebuild identico (stesso hash, PASS) e un rebuild con `transform_version`/`source_manifest_hash` alterato (drift rilevato, PASS) - sia nel modulo stesso, sia nel preflight, sia nel red-team finale (`dataset_file_modification_undetected`, BLOCKED nonostante il nome dell'attacco).

## 6. Qual e' l'hash/versione del nuovo dataset?

`dataset_id`: **`DUKASCOPY_NEWPERIOD_2023H1_ONWARD_V1`**
`hash`: **`78566884c3304c3d09286558548d446874a576bf607ca38cd86d62771472a18a`**
Registrato in `server/research_scripts/phase7/dataset_version_registry_v2.json`, componenti: manifest sorgente (1321 giorni), date range `2023-02-04..2026-09-16`, strumento XAUUSD, timeframe TICK, transform_version = downloader Phase 7 (identico a Phase 4/6, solo confini temporali diversi).

## 7. Il nuovo periodo e' integro?

**Si', verdetto `PASS_WITH_NOTES`** (`new_dataset_integrity_report_v1.json`). Copertura: 1321/1321 giorni attesi presenti, 0 mancanti, 0 incomplete dopo il retry (il fetch iniziale ha incontrato errori transitori HTTP 503/timeout su ~86 giorni, tutti risolti da una seconda passata idempotente dello stesso downloader). Controlli tick-level su **226.482.290 tick reali**: 0 timestamp non monotoni, 0 tick duplicati, 0 prezzi fuori dal range plausibile [500,6000], 0 anomalie di spread. Unica nota (soft concern, non hard failure): 4 giorni feriali a zero tick - **verificati come Venerdi' Santo** (2023-04-07, 2024-03-29, 2025-04-18, 2026-04-03), festivita' di mercato reali, non un errore di acquisizione. Timezone (UTC) e simbolo (XAUUSD) coerenti per costruzione del downloader, non per scansione.

## 8. Gli split sono materializzati?

**Si', logicamente** (nessuna duplicazione fisica dei tick - i segmenti sono intervalli di date sul manifest esistente). Confini **identici a quelli gia' dichiarati in Phase 7.0** (`partition_contract_v2.json`, `proposed_future_split_NOT_YET_EXECUTED`) - copiati verbatim, non ricalcolati guardando i dati ora disponibili:

| Segmento | Periodo | Giorni | Tick |
|---|---|---|---|
| development.discovery | 2023-02-04 → 2024-08-03 | 547 | 61.404.484 |
| development.internal_validation | 2024-08-04 → 2025-05-03 | 273 | 50.636.469 |
| locked_validation | 2025-05-04 → 2026-02-03 | 276 | 58.428.170 |
| final_holdout | 2026-02-04 → 2026-09-16 | 225 | 56.013.167 |

Tutti i segmenti hanno giorni disponibili (nessuno split vuoto forzato) - `partition_manifest_v1.json`.

## 9. Il FINAL_HOLDOUT e' realmente sigillato?

**Si'.** `final_holdout_seal_v1.json`: manifest separato limitato al sottoinsieme di date del holdout, hash congelato del sottoinsieme (`c24fb59f7a53d6e0...`), `sealed_status: SEALED`, regole esplicite (nessun fit di scaler/soglia ammesso - enforcement reale via `FitIsolationViolation`; accesso one-shot per candidate_id via `ValidationAccessLedger`). Il codice di sviluppo non ha un percorso legittimo per leggere il holdout senza passare dall'access guard - non esiste una funzione "leggi i tick del holdout direttamente" nell'infrastruttura Phase 7.

## 10. Quali red-team attack sono stati bloccati?

**Tutti e 8, nessun blocker residuo** (`red_team_final_v1.json`): cross-split baseline match (`CrossSplitViolation`), holdout second read (`ValidationAccessViolation`), validation reuse oltre il limite (`ValidationAccessViolation`), modifica del dataset sorgente (`DatasetVersionDriftError`), fit dello scaler su validation (`FitIsolationViolation`), uso di un detector patologico per discovery (`DetectorNotAllowedForDiscovery`), candidato duplicato con rappresentazione diversa - casing/ordine/numerico (`DuplicateCandidateSignature`), baseline con pool insufficiente forzato (`REJECTED_INSUFFICIENT_POOL`, zero match prodotti). Ogni attacco chiama l'azione pericolosa REALE contro il modulo reale, non uno scenario simulato a parte.

## 11. Quali blocker restano?

**Nessun blocker HARD.** Due gap dichiarati esplicitamente, fuori dallo scope di questo readiness gate (riguardano la qualita' futura della discovery, non l'infrastruttura):
- **CANDIDATE_SURVIVORSHIP** - rischio di processo (idee scartate mentalmente prima di essere formalizzate), non chiudibile con solo codice.
- **feed_robustness / market_transferability** restano `UNTESTED` - un solo feed (Dukascopy) e un solo simbolo (XAUUSD), vedi `cross_market_readiness_policy.json` (gia' dichiarato in Phase 7.0, invariato).

## 12. READY_FOR_PHASE_7_1 = true/false?

## **TRUE**

`phase7_1_readiness_gate_v1.json`: tutte le 13 gate hard verificate PASS (`baseline_engine_v4_implemented`, `baseline_split_safe`, `baseline_direction_aware`, `event_firing_rate_guard_pass`, `validation_access_guard_pass`, `holdout_one_shot_enforced`, `dataset_version_guard_pass`, `dataset_drift_guard_pass`, `new_dataset_integrity_pass`, `partition_materialized`, `final_holdout_sealed`, `fit_isolation_pass`, `preflight_pass` con **38/38 check PASS**), `unresolved_blockers: []`. Nessuna media pesata - regola binaria, tutte o niente.

**Questo NON autorizza l'esecuzione di Phase 7.1.** Come esplicitamente richiesto: nessuna Phase 7.1 e' stata eseguita in questa fase. Mi fermo e aspetto autorizzazione esplicita prima di qualunque discovery run reale sul nuovo periodo.

---

## Deliverables prodotti

**Motore (nuovo):**
- `engine/baseline_engine_v4.py`, `engine/event_firing_rate_guard.py`, `engine/validation_access_ledger.py`, `engine/dataset_version_guard.py`
- Estensioni: `engine/candidate_signature.py` (+`assert_not_duplicate`), `engine/event_firing_rate_guard.py` (+`assert_allowed_for_discovery`) - enforcement reale, non solo funzioni di rilevamento passive.

**Policy/contratti:**
- `policies/validation_access_policy_v1.json`

**Artifact operativi (dati reali, non sintetici):**
- `acquisition_freeze_declaration_v1.json`, `phase7_dukascopy_downloader.py`
- `event_detector_health_v1.json` (9 famiglie reali di Phase 5)
- `new_dataset_integrity_report_v1.json` (226M tick verificati)
- `dataset_version_registry_v2.json`
- `partition_manifest_v1.json`, `final_holdout_seal_v1.json`
- `discovery_run_manifest_v2.json` (operativo, mode=OPERATIONAL_READINESS_ONLY)
- `phase7_1_readiness_gate_v1.json`
- `red_team_final_v1.json`
- `baseline_quality_report_v4.json` (su fixture sintetiche - nessun dato di mercato usato per calcolare un effetto)

**Preflight esteso:** 14 (Phase 7.0) → 23 (Integrity Patch) → **38 check (Phase 7.0B)**, 38/38 PASS, zero regressioni sui check precedenti.

## Vincoli rispettati

Nessun H007, nessuna ricerca di edge, nessuna analisi della SELL asymmetry, nessun ranking di setup, nessuna ottimizzazione di parametri, FINAL_HOLDOUT mai usato per esplorazione, nessun risultato storico modificato, nessun file frontend/backend applicativo Codex toccato.
