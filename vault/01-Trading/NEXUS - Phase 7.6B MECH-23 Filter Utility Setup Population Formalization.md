# NEXUS - Phase 7.6B MECH-23 Filter Utility (SEQ-0014B) Setup Population Formalization

**Baseline:** `206938c` (SEQ-0014A/SEQ-0014B separate, SEQ-0014A `FEASIBLE`, SEQ-0014B `NEEDS_DIRECTIONAL_SETUP_POPULATION_SPECIFICATION`). Riguarda **solo** SEQ-0014B - SEQ-0014A resta invariato.

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.** Nessun structural preflight eseguito, nessuna discovery autorizzata.

---

## Esito: popolazione trovata, nessun hard stop

| | |
|---|---|
| **MECH23_FILTER_CLAIM_STATUS** | `SETUP_POPULATION_SPECIFIED_AWAITING_STRUCTURAL_PREFLIGHT` |
| **Famiglie eleggibili** | 6 di 9 |
| **Architettura decisa** | Pooled, stratificata per `setup_family_id` |

## 1. Inventario canonico (9 famiglie, `build_events.py`/`build_events_p71.py`)

Regola di eleggibilita' congelata **prima** di guardare qualunque risultato (6 criteri strutturali/causali: direzionale, causalmente osservabile a `bar_close` immediato, timing univoco, detector gia' congelato, nessun gap dati per il calcolo raw H4, non duplicato) - **esplicitamente vietato** usare PF/win rate/deltaP/risultato storico/probabilita' attesa che il filtro funzioni.

| Famiglia | Osservazione | Esito |
|---|---|---|
| VOLATILITY_EXPANSION, DISPLACEMENT, BREAKOUT, SWEEP, COMPRESSION_RELEASE, PULLBACK | `bar_close` immediato, direzione univoca | **ELEGGIBILI (6)** come unita' di setup |
| FAILED_BREAKOUT, RETEST, RECLAIM | `bar_close_delayed` - la loro esistenza e' nota solo in retrospettiva | **RICLASSIFICATE come outcome-label** dei rispettivi setup genitori (BREAKOUT/SWEEP), non setup indipendenti - includerle avrebbe duplicato l'entrata e violato il timing causale |

## 2. Scoperta concreta durante l'audit: la discrepanza RECLAIM

Il registry (`market_sequence_registry_v1.json`) descrive RECLAIM come **"REFUTED_AT_DISCOVERY in Phase 7.1"**. Verificando l'artifact frozen originale (`phase7_1_run_results.json`): `final_lifecycle_states` per tutti e 3 i candidati (BOTH/BUY/SELL) e' **`INSUFFICIENT_SAMPLE`**, `overall_verdict="NO_SUPPORTED_CANDIDATE"` - **mai "REFUTED"**. L'`EVENT_VIEW` mostrava un delta_p negativo apparente, ma `EPISODE_VIEW` (179→72, 102→40, 77→34) mostra il segno invertito e sotto soglia di materialita' (`dependence_sensitive=true` per tutti e 3) - l'effetto negativo era un artefatto di eventi dipendenti/clusterizzati, non un test robusto poi refutato. Discrepanza **documentata**, non corretta silenziosamente nel registry (fuori scope).

## 3. Failure-memory policy

Distinzione esplicita: **`REFUTED_AS_AUTONOMOUS_EDGE`** (un test ha rifiutato l'effetto marginale medio) vs **`NOT_USABLE_AS_FILTER_TEST_UNIT`** (problema strutturale). **Policy:** uno status REFUTED_AS_AUTONOMOUS_EDGE **non disqualifica automaticamente** - il claim filter-utility e' condizionato/moderato, logicamente distinto dal claim marginale gia' rifiutato (un effetto medio nullo e' compatibile con un effetto condizionale reale che si annulla in media). Riattivare un'idea refutata sarebbe vietato (FAIL-002/sec.24) **solo se** il moderatore fosse inventato per salvare quella famiglia specifica - qui il moderatore (LOW_INFORMATION_STATE) e' **gia' congelato** in Phase 7.5C e applicato **identico** a tutte le 6 famiglie, mai scelto per farne funzionare una.

Tutte e 6 le famiglie eleggibili hanno uno storico `REFUTED_AS_AUTONOMOUS_EDGE` (Phase 5.5, dataset 2019-2022, `event_alone`) - **nessuna e' disqualificata**, con scetticismo proporzionale esplicitamente richiamato (stesso principio gia' usato per SEQ-0011).

## 4. Architettura: pooled, stratificata (decisione ex-ante)

Valutate esplicitamente **entrambe** le opzioni (single-family: piu' semplice ma risponde a una domanda piu' stretta del claim originale; pooled: piu' fedele al claim generico "setup direzionali" ma richiede stratificazione). **Decisione: OPTION_B - pooled, stratificata per `setup_family_id`** - motivata dalla formulazione generica del claim MECH-23 originale, presa **prima** di calcolare qualunque geometria per nessuna famiglia. `setup_family_id` e' un campo obbligatorio - nessun pooling ingenuo (mai trattare setup di famiglie diverse come osservazioni intercambiabili).

## 5. Regime contract

**CHOPPY**: `directional_efficiency` in terzile LOW - **stessi cutpoints gia' congelati in Phase 7.5C, non ri-fittati**. **TRENDING**: terzile HIGH (stessa feature, candidato naturale complementare). **MED: ESCLUSO** - il claim originale contrappone esplicitamente due regimi nominati (choppy/trending), non un continuum; nessuna forte giustificazione trovata per includerlo.

## 6. Timestamp contract - rischio di endogeneita' identificato e risolto

**Rischio reale identificato**: `directional_efficiency[t]` include la barra t stessa nella propria finestra KER di 20 barre, e diverse famiglie eleggibili derivano la propria direzione/innesco dall'OHLC della STESSA barra t - leggere il regime a t creerebbe una sovrapposizione meccanica. **Risoluzione**: il regime e' letto a **t-1** (mai a t) - generalizza lo stesso principio anti-circolarita' gia' usato per le dimensioni di matching in Phase 7.5B/7.5C, applicato qui alla variabile di esposizione primaria.

## 7. Candidate failure/noise outcomes (nessuna selezione)

Elencati senza scegliere: `P_PLUS_*ATR_BEFORE_MINUS_1ATR`, `MAE`, `REVERSAL_PROBABILITY`, `TIME_TO_TARGET`, `PATH_EFFICIENCY` (generici, applicabili a tutte e 6) + `FAILED_BREAKOUT`/`RECLAIM` (nativi ma family-specific, utilizzabili solo come diagnostica secondaria in un disegno pooled).

## 8. Cosa NON e' stato fatto (per istruzione esplicita)

Nessun structural preflight (n setup totali, n CHOPPY/TRENDING/MED, geometria EVENT/EPISODE/INDEPENDENT_VIEW, matching, reuse) e' stato calcolato - rimandato a una fase separata. Nessun outcome scelto/calcolato. `SEQ-0014A` (`seq0014_frozen_structural_spec_v1.json`) non toccato - verificato nessun diff.

## Regressione - 44/44 PASS

`test_seq0014b_setup_population_spec.py`: inventario completo, eleggibilita' non basata su performance, discrepanza RECLAIM verificata contro l'artifact originale, policy failure-memory applicata correttamente, decisione architetturale presa (non lasciata aperta), regime/timestamp contract coerenti con SEQ-0014A, nessun outcome selezionato, hard-stop non attivato. **0 regressioni** sulle altre 14 suite Phase 7 (15 totali).

## Deliverables

`seq0014b_setup_population_spec_v1.json`, `build_seq0014b_setup_population_spec.py`, `test_seq0014b_setup_population_spec.py`. Nessuna modifica a `seq0014_frozen_structural_spec_v1.json` ne' agli artifact Phase 7.6A.

---

**NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.** SEQ-0015 e SEQ-0009 restano chiuse. Nessun structural preflight/discovery eseguito per nessuno dei due esperimenti SEQ-0014.

**Progresso verso demo (invariato): ~68%.** MECH-23 separato correttamente in state phenomenon vs filter utility; popolazione di setup direzionali ora formalizzata ex-ante per il secondo. Non ancora evidenza di edge/filter utility reale.
