# NEXUS - Phase 7.4A: First Sequence Discovery Pre-Registration (SEQ-0015)

**Baseline:** `ddbf2d5` (Phase 7.3, verificata, READY_FOR_FIRST_SEQUENCE_DISCOVERY=true). Questa fase congela il detector e la frozen spec per la PRIMA sequence family che attraverserà il Sequence Discovery Engine v1 - **nessuna discovery viene eseguita**.

**Conferma esplicita: NO OUTCOME DATA ACCESSED. NO SEQUENCE DISCOVERY EXECUTED IN PHASE 7.4A.** Il detector è stato validato solo su barre sintetiche generate in memoria (`seq0015_momentum_burst_detector.py`, self-test in `__main__`); nessun file di dati NEXUS è stato letto per calcolare un evento, una feature di stato o un outcome reale. L'unico riferimento a dataset NEXUS in questa fase è ai metadati di partizione già stabiliti in Phase 7.0B (date/hash), mai al contenuto dei prezzi.

---

## Sequence family scelta

**SEQ-0015 — MOMENTUM_BURST_CONTINUATION** (MECH-25), scelta come *engine qualification family* per motivi tecnici (H4 nativo, causal-safe, NOVEL/pochi gap dati, poche dimensioni), non per un'aspettativa di profittabilità.

## 1-2. Detector formalizzato e soglia

```
TR_t = max(high_t-low_t, abs(high_t-close_{t-1}), abs(low_t-close_{t-1}))
burst_ratio_t = TR_t / ATR_{t-1}          (Wilder ATR(14), causale)
is_burst_t = burst_ratio_t > P90_causale_rolling(burst_ratio, finestra=252, esclusa la barra t)
```

**Verifica esplicita richiesta al punto 1 (ATR_{t-1} vs ATR_t):** confermato leggendo il codice reale - `wilder_atr()` è una EMA(alpha=1/14) che include TR_t nella propria media alla posizione t. `server/research_scripts/phase5/build_events.py:99` (VOLATILITY_EXPANSION, poi `H008_EVENT_VOLATILITY_EXPANSION`) usava esattamente `tr>1.0xATR_t` con questo ATR same-bar - la barra anomala attenua meccanicamente il proprio rapporto di anomalia. **Questo è esattamente il motivo per cui SEQ-0015 risulta metodologicamente imparentata con un fallimento precedente** (vedi sezione Failure Memory sotto). Usando ATR_{t-1} questa attenuazione non può avvenire per costruzione.

**Soglia:** nessun ancoraggio esterno univoco in CLAIM-0042/CLAIM-0043 (descrivono un meccanismo scalato alla volatilità, ma senza un moltiplicatore ATR specifico) - usata quindi una regola distribuzionale causale: **percentile 90, finestra rolling 252 barre H4, warmup minimo 252 barre** (stessa finestra già convenzione di progetto per `atr_percentile`). Nessun test di soglie alternative (85/90/95 o moltiplicatori fissi) eseguito su dati NEXUS prima del freeze.

## 3-4. Direction e observation timing

`BUY` se `close_t>open_t`, `SELL` se `close_t<open_t`, `NO_EVENT` se doji (nessuna dipendenza da t+1). Congelato: `event_a_index=t`, `observation_cutoff=prediction_start=transition_complete=close(t)`, `outcome_window_start=t+1`.

## 5. Episode rule

`episode_gap_rule=3 barre`, `natural_horizon=40 barre` (identico all'orizzonte outcome), `overlap_policy=COLLAPSE_TO_FIRST`. Verificato su dati sintetici con `sequence_episode_engine.py`: 13 eventi rilevati → 9 episodi (2 coppie di burst ravvicinati correttamente collassate in 1 episodio ciascuna).

## 6-8. Domanda scientifica e outcome

**Domanda primaria:** dopo un abnormal true-range burst H4, la distribuzione futura nella direzione del burst differisce da quella di barre matched comparabili senza burst?

- **Primary outcome (congelato):** `P_PLUS_1ATR_BEFORE_MINUS_1ATR`, normalizzato con **ATR_t** (non ATR_{t-1} - motivato esplicitamente: ATR_t è già interamente noto a prediction_start=close(t), nessuna barra futura richiesta, e non c'è incentivo ad attenuare un effetto già realizzato).
- **Secondary pre-registered (6):** MFE, MAE, TIME_TO_MFE, PATH_EFFICIENCY, P_PLUS_0_5ATR, P_PLUS_1_5ATR.
- **Diagnostic-only (6):** P_PLUS_0_25ATR, P_PLUS_2ATR, TIME_TO_TARGET, CONTINUATION_PROBABILITY, REVERSAL_PROBABILITY, REALIZED_VOLATILITY_AFTER_SETUP.

## 9-10. Baseline e control exclusion

**Dimensioni (poche, motivate causalmente):** `direction`, `volatility_state_pre_burst` (terzile atr_percentile a **t-1**), `trend_state_pre_burst` (terzile ema_slope_atr_norm a **t-1**) - mai a t (circolarità). `directional_efficiency` **esclusa deliberatamente**: il meccanismo dichiarato riguarda l'espansione di volatilità, non l'efficienza del movimento pregresso, e trend_state_pre_burst copre già la componente rilevante. `k=5`, `minimum_control_count=20` (default di progetto, invariato).

**Control exclusion window:** esclusi dal pool di un evento a `t`: la barra stessa; qualunque barra a `|r-t|<=40`; qualunque altra barra MOMENTUM_BURST dello stesso episodio; qualunque barra di split diverso (enforcement strutturale esistente, riusato).

## 11-12. Dependence e gates

`DEPENDENCE_SENSITIVE` = segno di ΔP diverso fra EVENT VIEW ed EPISODE VIEW, o `effective_n<20` mentre `n_nominal>=30` (convenzione di progetto invariata). Gates congelati: `n_nominal_minimum=30`, `cluster_count_minimum=20`, `effective_n_minimum=20`, `minimum_controls_per_match=20`, **`minimum_material_delta_p=0.10`** (floor di default - **non** riciclato l'override 0.15 di Phase 7.1/RECLAIM, motivato solo dalla continuità con quella famiglia specifica), `uncertainty_method=WILSON_CI95`.

## 13-14. BUY/SELL e multiple testing

**BOTH/BUY/SELL pre-registrati insieme ORA** come famiglia di 3 candidati (stessa convenzione di Phase 7.1) - nessuno promuovibile individualmente fuori da questa famiglia. Multiple testing: **3 candidati × 7 outcome (1 primary + 6 secondary) = 21 confronti**, Benjamini-Hochberg FDR q=0.10. I 6 diagnostic-only non entrano mai in questa famiglia.

## 15. Failure memory — relazione dichiarata, non nascosta

**`RELATED_TO_PREVIOUS_FAILURE`** (non NOVEL, non DIRECT_REPEAT). Verifica esplicita eseguita come richiesto: `H008_EVENT_VOLATILITY_EXPANSION` e `H010_INTERACTION_BREAKOUT_x_VOLATILITY_EXPANSION` (Phase 5, entrambi REFUTED/NO_EDGE) testavano lo stesso concetto di fondo (barra a range anomalo → continuazione) con soglia fissa `1.0xATR` **same-bar**. SEQ-0015 non è un rename: denominatore ATR_{t-1}, soglia distribuzionale causale, baseline su stato pre-burst con dimensioni dichiarate ora, architettura episode-first - tutte differenze metodologiche reali e motivate indipendentemente. Ma il concetto di fondo resta lo stesso già refutato una volta: dichiarato con piena trasparenza, non mascherato dietro un nome diverso ("NOVEL non deve significare nome diverso"). **Corretto anche il registro** (`market_sequence_registry_v1.json`, che marcava erroneamente SEQ-0015 come NOVEL) e rigenerato di conseguenza `phase7_3_eligible_sequence_families_v1.json`/`phase7_3_engine_readiness_gate_v1.json` (nessun impatto: SEQ-0015 resta eleggibile, READY_FOR_FIRST_SEQUENCE_DISCOVERY resta true - il criterio Phase 7.3 esclude solo DIRECT_REPEAT, non RELATED_TO_PREVIOUS_FAILURE, esattamente come già per SEQ-0009).

## 16. Detector versioning

- `detector_version` = `seq0015_momentum_burst_detector.py@v1`
- `detector_source_hash` (SHA256 del file `.py`) = `7715fd01f2063a521d8988ee9c46ffa3f98d21c577423f71c2ae710dc88d84f4`
- `frozen_parameters_hash` (SHA256 canonico del dict `FROZEN_PARAMETERS`, unica fonte di verità condivisa fra detector e frozen spec) = `6310c1cfc24182d3e9138bb1354363b6254fa3595cda63808f3cfb4d2e1ee2ac`

`sequence_causality_guard.assert_detector_version_unchanged` (Phase 7.3) rifiuterà per costruzione qualunque evento con `detector_version` diverso da quello congelato qui.

## 17. Dataset partitions

Nessun accesso ora. Split dichiarati (Phase 7.0B, `partition_manifest_v1.json`): `discovery=development_discovery` (2023-02-04..2024-08-03), `internal_validation=development_internal_validation` (2024-08-04..2025-05-03, **untouched**), `locked_validation` (2025-05-04..2026-02-03, **untouched**), `final_holdout` (2026-02-04..2026-09-16, **untouched**). Dataset version: `DUKASCOPY_NEWPERIOD_2023H1_ONWARD_V1` (hash `78566884c3304c3d09286558548d446874a576bf607ca38cd86d62771472a18a`).

## 18-19. Frozen spec artifact e verifica pre-registrazione

`phase7_4_seq0015_frozen_spec_v1.json` — validato meccanicamente contro `sequence_family_frozen_spec_v1.schema.json`: **0 campi richiesti mancanti, 0 campi extra non dichiarati**, nessun `TBD`/placeholder nelle parti inferenziali. Verificato anche che `preregistration_provenance_guard.assert_frozen_spec_committed_before_run` **blocchi correttamente ORA** (file non ancora tracciato da git) - la futura Phase 7.4B non potrà partire finché questo commit non esiste.

## File prodotti

`server/research_scripts/phase7/phase7_4/`:
- `seq0015_momentum_burst_detector.py` (detector + `FROZEN_PARAMETERS`, self-test su dati sintetici)
- `build_seq0015_frozen_spec.py`, `phase7_4_seq0015_frozen_spec_v1.json`

Corretti/rigenerati (data quality, non nuova logica):
- `server/research_scripts/phase7/phase7_2/market_sequence_registry_v1.json` (SEQ-0015: NOVEL → RELATED_TO_PREVIOUS_FAILURE)
- `server/research_scripts/phase7/phase7_3/phase7_3_eligible_sequence_families_v1.json`, `phase7_3_engine_readiness_gate_v1.json` (rigenerati, nessun impatto sul verdetto)

---

**NO OUTCOME DATA ACCESSED. NO SEQUENCE DISCOVERY EXECUTED IN PHASE 7.4A.**

**Commit/push eseguiti. Il commit di questa frozen spec diventa il `preregistration_commit_sha` della futura Phase 7.4B. Nessuna Phase 7.4B senza nuova autorizzazione, dopo verifica di spec/hash/detector da parte dell'utente.**
