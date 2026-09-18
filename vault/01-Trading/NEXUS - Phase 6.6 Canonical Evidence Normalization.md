# NEXUS - Phase 6.6: Canonical Evidence Normalization & Research Ledger v2

Fase di normalizzazione pura: trasforma le informazioni metodologiche già prodotte in Phase 6/6.5 in artifact JSON canonici, versionati, machine-readable — **senza cambiare alcuna conclusione su H006**. Nessun nuovo edge, nessun H007, nessuna optimization, nessun nuovo backtest, nessuna modifica a frontend/backend applicativo (lavoro riservato a Codex sul Market workspace). Tutto il lavoro vive in `server/research_scripts/phase6_6/`.

**H006 resta**: `BORDERLINE`, evidence grade `E2`, `promoted_to_e3=false`, `execution=NOT_TESTED`. Phase 6.5 resta `METHODOLOGICAL_AUDIT_ONLY`.

---

## 1. Vincolo rispettato

Ogni generatore in questa fase **legge** artifact già esistenti (Phase 5.5/6/6.5) e li riformatta — nessun ricalcolo. Verificato meccanicamente da `validate_integrity.py`: `h006_grade_not_promoted` (grade=E2), `h006_not_at_e3` (decision=RETAIN_E2), `e4_e5_not_authorized` — tutti PASS.

## 2. Canonical Evidence Record v2 — schema

`evidence_record_v2.schema.json`: 8 gruppi di campi (Identity, Evidence classification, Effect, Sample, Uncertainty, Baseline, Integrity, Provenance), tutti con `required` a livello di gruppo — un campo mancante è **sempre presente come `null`**, mai omesso né sostituito con uno zero inventato. Nomi di campo (`hypothesis_id`, `experiment_id`, `dataset_id`, `evidence_id`) scelti per essere direttamente compatibili con il Canonical Research Model introdotto da Codex (Hypothesis/Experiment/Dataset/Evidence/EdgeComponent/DecisionCard) — nessun codice Codex letto o modificato per arrivare a questa scelta, solo convenzione di naming esplicitamente richiesta.

## 3. H006 normalizzato — primary vs audit, nessuna fusione

`h006_evidence_v2.json` contiene **due record separati** sotto la stessa ipotesi:

| | `primary_evidence` | `retroactive_methodological_audit` |
|---|---|---|
| evidence_type | `PRIMARY_EVIDENCE` | `RETROACTIVE_METHODOLOGICAL_AUDIT` |
| evidence_grade | **E2** | `null` (nessun grade proprio) |
| conclusion | `BORDERLINE` | `AUDIT_ONLY` |
| n_nominal / n_effective | 115 / `null` | 115 / {cluster:46, autocorr:115, block-boot:91.1, methods_agree:false} |
| overlap_rate / dependence_flag | `null` / `null` | 0.991 / `HIGH` |
| uncertainty | Wilson + Beta-Binomial (Phase 6) | + iid bootstrap CI + block-bootstrap CI (Phase 6.5) |
| baseline | v2 aggregato, direction-conditioned per-evento | v3 esplicitamente direction-aware (BUY-vs-BUY, SELL-vs-SELL) |

Campo esplicito `authoritative_grade_source: "primary_evidence"` + `authoritative_statement` dichiarano senza ambiguità che l'audit non ha autorità di modificare grade/conclusion. Verificato meccanicamente: `audit_record_has_no_own_grade` = PASS.

## 4. Directional diagnostics → post-hoc observation

`post_hoc_observations_v1.json`: `SELL_SWEEP_RECLAIM_ASYMMETRY` con BUY (P=52.4%, baseline=50.5%, ΔP=+0.019) e SELL (P=67.3%, baseline=56.9%, ΔP=+0.104) — `is_edge=false`, `is_validated=false`, `requires_new_hypothesis=true`, `requires_new_holdout=true`. Nessun `hypothesis_id` proprio (solo `derived_from_hypothesis_id`) — non è un'ipotesi testabile, è un'osservazione. Nessun H007 creato.

## 5. Decision Card v2

`h006_decision_card_v2.json` — JSON puro, nessun Markdown da interpretare: `decision: RETAIN_E2`, `promotion_allowed: false`, `next_stage_allowed: false`, `next_stages_explicitly_not_authorized: [E3, E4, E5]`, con `failed_gates`/`passed_gates`/`unresolved_questions` strutturati.

## 6. Research Ledger

`research_evidence_ledger_v1.json`: 10 transizioni cronologiche da H004 (Phase 5, scoperta) a Phase 6.6 (normalizzazione), ciascuna con timestamp/phase/event_type/from_status/to_status/reason/source_artifact/commit. Logicamente append-only (nuove correzioni si aggiungerebbero come nuova voce `seq`, mai sovrascrivendo una esistente).

## 7. Evidence Relation Model

`research_relations_v1.json`: 10 archi tipizzati (TESTS, DERIVED_FROM, AUDITS, LIMITS usati; SUPPORTS, REFUTES, SUPERSEDES nel vocabolario ma **SUPERSEDES mai usato per H006**, per costruzione). Invariante dichiarato e verificato: `EVD-H006-AUDIT-001 --AUDITS--> EVD-H006-PRIMARY-001`, mai l'inverso, mai un arco SUPERSEDES fra i due.

## 8-9. Registry update + Provenance integrity

Nessun dato storico sovrascritto distruttivamente — tutti i nuovi artifact sono **aggiunte** (nuovi file in `phase6_6/`), i file di Phase 6/6.5 restano invariati. `artifact_manifest.json`: 14 artifact, ciascuno con path relativo (mai assoluto — verificato: `no_absolute_source_paths` PASS), SHA-256, schema_version, generated_from, generator script.

## 10. Determinismo

Ogni artifact è avvolto in `{generated_at (volatile), generation_script, canonical_sha256, payload}` — l'hash copre solo `payload`. Verificato **eseguendo davvero** ogni generatore due volte e confrontando l'hash (`deterministic_regeneration` in `validate_integrity.py`): tutti e 5 i generatori producono hash identico a run ripetuti.

## 11. Integrity tests

`validate_integrity.py`: **12/12 check PASS** — duplicate evidence ID, hypothesis_id mancante/incoerente, relation rotte, path sorgente malformati, hash mismatch (ricalcolo reale, non solo confronto dichiarato), promozione di grade vietata, audit-con-grade-proprio, post-hoc-osservazione-marcata-come-edge, H006-a-E3, E4/E5 non autorizzati, rigenerazione deterministica. Dimostrazione negativa fatta a mano (non persistita come file): forzando `evidence_grade="E3"` su una copia del payload, il check `h006_grade_not_promoted` passa correttamente a FAIL — il validatore rileva davvero la violazione, non solo quando tutto è già corretto.

## 12. Compatibilità con il Canonical Research Model di Codex

Nessun file frontend/backend/`server/app.py` letto o modificato. Naming dei campi (`hypothesis_id`, `experiment_id`, `dataset_id`, `evidence_id`) allineato esplicitamente alle entità Hypothesis/Experiment/Dataset/Evidence dichiarate nella richiesta, per facilitare una futura ingestione senza richiedere una rimappatura dei nomi.

---

## Risposte finali

**1. Qual è ora la fonte canonica del grade E2 di H006?**
`server/research_scripts/phase6_6/h006_evidence_v2.json` → `payload.primary_evidence.evidence_classification.evidence_grade`, con `payload.authoritative_grade_source="primary_evidence"` a disambiguare esplicitamente. La Decision Card (`h006_decision_card_v2.json`) lo rispecchia come `current_grade`.

**2. Come viene distinto il risultato originale dal methodological audit?**
Due oggetti separati (`primary_evidence` / `retroactive_methodological_audit`) nello stesso file, con `evidence_type` diversi, l'audit senza un proprio `evidence_grade` (sempre `null`) e `conclusion` fissa a `AUDIT_ONLY`. Verificato meccanicamente da `validate_integrity.py`, non solo per convenzione documentale.

**3. Come viene rappresentata la SELL asymmetry senza promuoverla a edge?**
Come voce in `post_hoc_observations_v1.json` con `status=POST_HOC_OBSERVATION`, `is_edge=false`, `is_validated=false`, nessun `hypothesis_id` proprio (solo `derived_from_hypothesis_id`), e relazione `DERIVED_FROM` (mai `TESTS`/`SUPPORTS`) nel modello di relazioni.

**4. Quali dati mancavano per rendere H006 completamente machine-readable?**
Prima di questa fase: nessun `evidence_id` stabile, nessuna separazione esplicita primary/audit in un formato interrogabile, nessun modello di relazioni, nessun ledger di transizioni, nessun manifest con hash di provenance, e i numeri di Phase 6.5 vivevano in JSON con schemi diversi fra loro (non un unico schema canonico condiviso). Tutto ora popolato — resta un limite dichiarato: `dataset_id` (`DUKASCOPY_HOLDOUT_2022H2_2023H1_V1`) è un'etichetta assegnata qui, non ancora backed da un registro Dataset formale con proprio schema/hash indipendente.

**5. Quali relation sono ora disponibili per Explain Path?**
`TESTS` (esperimento→ipotesi, evidence→ipotesi), `DERIVED_FROM` (H006→H004, osservazione→evidence), `AUDITS` (Phase 6.5→Phase 6, a livello sia di esperimento sia di evidence record), `LIMITS` (audit→primary, H006→H004). `SUPPORTS` e `SUPERSEDES` sono nel vocabolario ma non hanno archi reali per H006 — dichiarato esplicitamente, non nascosto.

**6. Il ledger è deterministico?**
Sì, verificato eseguendo il generatore due volte e confrontando `canonical_sha256` (identico), incluso dentro la suite `validate_integrity.py` (`deterministic_regeneration`, PASS).

**7. Quali artifact legacy restano ancora non normalizzati?**
Le altre 13 ipotesi del batch Phase 5 (H001-H003, H005, H007[Phase5]-H014, più H015/SAR — numerazione storica di `hypothesis_registry_v1.json`, non lo stesso H007 esplicitamente vietato in questa fase) non hanno ancora un proprio `evidence_record_v2`. I report narrativi di Phase 4/5 (Market Intelligence Foundation, Quantitative Edge Discovery Engine v1) restano markdown + JSON eterogenei, non ancora passati per questo schema. `EC-LIQUIDITY_SWEEP_RECLAIM` (l'Edge Component di Phase 5) non è ancora espresso in un formato compatibile con l'entità EdgeComponent di Codex. Nessun registro Dataset formale indipendente esiste ancora.

---

## Artifact prodotti

`server/research_scripts/phase6_6/`: `evidence_record_v2.schema.json`, `h006_evidence_v2.json`, `h006_decision_card_v2.json`, `post_hoc_observations_v1.json`, `research_evidence_ledger_v1.json`, `research_relations_v1.json`, `artifact_manifest.json`, `integrity_test_report.json`, `canonical_utils.py` + 5 script generatori + `validate_integrity.py`.
