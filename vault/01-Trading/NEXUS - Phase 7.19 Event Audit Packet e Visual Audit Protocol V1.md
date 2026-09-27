# NEXUS - Phase 7.19 — Event Audit Packet + Visual Audit Protocol V1

**Baseline:** HEAD disponibile all'esecuzione (successivo a `8590f63`, Phase 7.17/7.18). **Task esplicitamente ortogonale al lavoro TSI concorrente (Phase 7.18)**, ancora in corso al momento di questa fase (istrumentazione diagnostica temporanea presente ma non committata in `MQL5/Include/NEXUS_v1/NXS_Strategies.mqh`). Nessuna modifica a EA, sito, logging runtime, registry, Product Platform o artifact TSI. Nessun deploy, nessun backtest lungo. Questa fase è di **sola specifica e validazione metodologica** — non giudica se una qualunque strategia NEXUS abbia edge.

**Obiettivo**: definire uno standard NEXUS-wide, machine-readable, per la cattura, l'audit visivo e la revisione a posteriori di ogni evento/trade generato da qualunque strategia — indipendente dalla forma strutturale della strategia (filtro ricorsivo, zona discreta, cooldown, state machine) — cosicché quando l'implementazione tornerà disponibile abbia uno standard preciso da seguire.

---

## 1. EVENT_AUDIT_PACKET_V1

Schema JSON (`schemas/event_audit_packet_v1.schema.json`, draft-07) con 10 sezioni top-level required: `identity` (inclusi campi riservati multi-tenant `tenant_id`/`ea_instance_id`/`account_scope_id`, oggi `NOT_APPLICABLE`), `environment`, `timeline` (6 timestamp causali distinti, ciascuno con source/timezone/precision/confidence), `prices` (9 prezzi distinti, ciascuno con value+source+timestamp+fidelity+is_proxy — **mai un prezzo nudo, mai un proxy silenzioso**), `strategy_state` (generico, `state_before`/`state_after` con `strategy_state_kind` enumerato: RECURSIVE_FILTER/DISCRETE_ZONE/COOLDOWN_TIMER/STATE_MACHINE/STATELESS/OTHER — non hardcoded su una strategia), `decision_time_features`, `multi_timeframe_context`, `source_of_truth`, `fidelity`.

## 2. Separazione anti-leakage obbligatoria

Ogni `feature_value` porta `available_at_decision_time`/`depends_on_future_data`/`causality_verified`/`causality_verification_method` come campi strutturali, non convenzionali. `ANTI_LEAKAGE_SPECIFICATION_V1` cita esplicitamente i due precedenti storici del progetto (Phase 7.9J: leakage EMA100 su BREAKOUT_ACC; Phase 7.9K: offset del forward path su ORDER_BLOCK) come motivazione diretta della regola.

## 3. VISUAL_AUDIT_PROTOCOL_V1 (3 stage sequenziali)

Stage A (blind review — 5 domande standard, **"Vincerà?" esplicitamente vietata**, richiede `blind_confirmed`+`data_explicitly_withheld`, deve essere LOCKED prima di sbloccare Stage B) → Stage B (future reveal, precondizione `revealed_after_stage_a_locked`, richiede confronto esplicito con l'aspettativa di Stage A, non una nuova opinione indipendente) → Stage C (outcome review, precondizione `revealed_after_stage_b_locked`, introduce `decision_outcome_matrix` a 4 categorie: GOOD_DECISION_BAD_OUTCOME / BAD_DECISION_GOOD_OUTCOME / GOOD_DECISION_GOOD_OUTCOME / BAD_DECISION_BAD_OUTCOME — la qualità della decisione è giudicata **solo su Stage A**, mai contaminata dall'esito).

## 4. FIDELITY_FRAMEWORK_V1

4 livelli A/B/C/D con criteri precisi (non solo descrittivi): A richiede TUTTI — stesso broker/feed, tick/M1, fill reale, state snapshot live, runtime identity verificata, timezone verificata. **Nessun esempio del progetto raggiunge oggi Fidelity A** (il runtime manifest non esiste ancora). Regola: il tier di un packet è il minimo fra i criteri di ogni sua componente. Vincolo a valle: audit di Fidelity C/D non possono mai essere etichettati `VALIDATED_RESULT`. Principio dichiarato esplicitamente: la fedeltà misura la ricostruzione, **non la strategia** — non è un voto sulla strategia.

## 5. RUNTIME_IDENTITY_MANIFEST_V1

Schema separato: nome/versione EA, git SHA, build fingerprint, hash dell'ex5 (se tecnicamente possibile — nullable con nota di limite tecnico dichiarata, non verificata in questa fase), compile timestamp, terminal build, server, symbol, hash della config di input, strategie abilitate. Esplicitamente: **"non basta il timestamp del file EX5"**.

## 6. Matched non-events, near-miss, sampling

`MATCHED_NON_EVENT_V1` — matching **solo causale**, mai basato sull'esito futuro (`outcome_used_in_selection` è un `const: false` a livello di schema, non solo una convenzione). Include `NEAR_MISS_EVENT`, `BLOCKED_EVENT`, `BROKER_REJECTED_EVENT`, `RANDOM_CONTROL`. `SAMPLING_PROTOCOL_V1`: default 20/20/20/20/20 fra le categorie, adattivo non obbligatorio.

## 7. Gerarchia delle fonti (SOURCE_OF_TRUTH_HIERARCHY_V1)

`execution (MT5 runtime/broker) > event_identity (MT5 canonico) > statistical_analysis (Python) > reconstructed_visual_context > narrative (Claude/Jarvis/umano)`. Incorpora esplicitamente la lezione di Phase 7.16 ("Python non è mai ground truth per strategie stateful/tick-sensitive"): stato attuale del progetto codificato direttamente nello schema — BREAKOUT_ACC = clone Python fedele (autoritativo a livello evento), ORDER_BLOCK = `APPROXIMATION_WITH_KNOWN_GAPS` (non autoritativo), TSI = `PARTIAL_STRUCTURAL_MODEL` (non autoritativo).

## 8. Regole anti-bias (ANTI_BIAS_RULES_V1)

7 regole (AB01-AB07), ciascuna con un meccanismo di enforcement tracciabile a un campo schema o vincolo di protocollo specifico (es. AB02 "no outcome nel matched sampling" → enforced da `outcome_used_in_selection: const false`).

## 9. Esempi reali (nessun dato fabbricato)

3 packet costruiti da artifact **già esistenti e reali**, zero dati inventati:
- **BREAKOUT_ACC** — evento reale `evt_1209b7abca9456d1` (Phase 7.9H), fill reale 1333.51, MFE/MAE/orizzonti reali → **Fidelity B**.
- **ORDER_BLOCK** — evento reale post-fix dal trace diagnostico Phase 7.14 (2023.10.13, SELL retest, zona [1919.63, 1925.17]), molti campi onestamente `NOT_RECORDED` (nessun fill reale, era Research Mode) → **Fidelity B**.
- **SH_BMS_RTO** — puramente strutturale/illustrativo → **Fidelity D**, scelto esplicitamente al posto di TSI con un campo `why_not_tsi` che documenta la ragione di non-interferenza con il lavoro concorrente.

Verificato che ogni campo assente usi uno dei 5 valori tassonomici (`NOT_AVAILABLE`/`NOT_APPLICABLE`/`NOT_RECORDED`/`UNKNOWN`/`CENSORED`), **mai `null` nudo**.

## 10. Gap analysis e roadmap

`GAP_ANALYSIS_V1`: 6 voci `MISSING_BUT_NEEDED` (priorità ALTA: intero `RUNTIME_IDENTITY_MANIFEST_V1` mancante in tutti e 3 gli esempi — il gap trasversale più ricorrente; fill reale per eventi diagnosticati; state snapshot per strategie senza istrumentazione temporanea attiva). `IMPLEMENTATION_ROADMAP_V1`: 5 livelli (MQL5 → Python-backend → Product Platform → Jarvis → Research Engine) con `depends_on`/`blocked_by` espliciti — **nessuna implementazione eseguita in questa fase**.

## 11. Decisione finale

**`AUDIT_STANDARD_READY`** — 8/8 controlli passati (schema rappresenta 3 forme strutturali diverse; nessun `null` nudo; separazione anti-leakage nello schema; fedeltà con criteri precisi; sequenza Stage A→B→C vincolata nello schema; gerarchia fonti incorpora Phase 7.16; gap analysis con esempi reali; roadmap con dipendenze esplicite). `no_edge_claim_made: true`.

## Deliverables

4 JSON Schema (`event_audit_packet_v1`, `runtime_identity_manifest_v1`, `visual_audit_result_v1`, `matched_non_event_v1`), 10 artifact JSON (`visual_audit_protocol_v1`, `fidelity_framework_v1`, `sampling_protocol_v1`, `anti_leakage_specification_v1`, `source_of_truth_hierarchy_v1`, `anti_bias_rules_v1`, `example_packets_v1`, `gap_analysis_v1`, `implementation_roadmap_v1`, `audit_standard_decision_v1`), 10 builder Python, verificatore indipendente (`verify_phase_7_19.py`, VERIFY OK — 0 problemi, incluso il controllo esplicito che l'unica modifica concorrente in `MQL5/` sia riconducibile al marcatore noto dell'istrumentazione TSI Phase 7.18), 29/29 test propri (`test_phase_7_19.py`), questo vault report.

## Vincoli preservati

Nessuna modifica a EA, strategie, registry, Product Platform, artifact TSI (`phase7_17` verificato a diff zero). Nessun deploy, nessun backtest lungo, nessuna optimization. Commit limitato esclusivamente a `server/research_scripts/phase7/phase7_19/**` e a questo vault report — `MQL5/` resta intenzionalmente non toccato da questo commit (appartiene al lavoro TSI Phase 7.18 ancora in corso).

## Regressione

Non eseguita la suite Phase 7 completa in questa fase: lo stato concorrente e non committato di `MQL5/Include/NEXUS_v1/NXS_Strategies.mqh` (istrumentazione diagnostica TSI Phase 7.18, run Tester live in corso al momento della stesura) avrebbe reso un run full-suite non dirimente per questa fase e a rischio di contesa di risorse con il run Tester in corso. Il verificatore indipendente e i 29 test propri di questa fase (isolati, nessuna dipendenza da `MQL5/`) sono stati eseguiti ripetutamente con esito positivo. La suite Phase 7 completa verrà eseguita dopo la chiusura di Phase 7.18.

---

```
7.18: TSI Minimal Fix + Short Live Validation - IN CORSO (concorrente,
  non toccata da questa fase)
7.19: EVENT AUDIT PACKET + VISUAL AUDIT PROTOCOL V1 - COMPLETATO
  schema packet generico: 10 sezioni, rappresenta 3 forme strutturali
    diverse (RECURSIVE_FILTER/DISCRETE_ZONE/COOLDOWN_TIMER/...)
  anti-leakage: separazione AVAILABLE_AT_DECISION_TIME vs FUTURE
    incorporata nello schema, non convenzionale
  visual audit: 3 stage vincolati (A blind -> B reveal -> C outcome),
    "Vincera'?" vietata in Stage A, matrice decisione/esito a 4 categorie
  fedelta': 4 tier A/B/C/D con criteri precisi, nessun esempio del
    progetto raggiunge oggi Fidelity A (manca RUNTIME_IDENTITY_MANIFEST)
  gerarchia fonti: incorpora esplicitamente la lezione Phase 7.16
    (Python mai ground truth per strategie stateful)
  3 esempi reali (zero dati fabbricati): BREAKOUT_ACC=B, ORDER_BLOCK=B,
    SH_BMS_RTO=D (TSI evitato deliberatamente, lavoro concorrente)
  gap piu' ricorrente: RUNTIME_IDENTITY_MANIFEST_V1 assente in TUTTI
    e 3 gli esempi
DECISIONE: AUDIT_STANDARD_READY (no_edge_claim_made: true)
PROSSIMO: chiusura Phase 7.18 (TSI fix), poi implementazione (Codex),
  poi checkpoint shortlist strategie candidate a edge validation
```
