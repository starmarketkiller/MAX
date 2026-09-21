#!/usr/bin/env python3
"""Phase 7.6A - MECH-23 Estimand Identity Audit.

NON legge outcome. NON esegue discovery. NON modifica il control pool.
NON crea una nuova structural spec. Solo un audit CONCETTUALE:
l'esperimento state-entry gia' congelato (Phase 7.5C, FEASIBLE) e la
preregistrazione gia' congelata (Phase 7.6A) stanno davvero testando
lo STESSO oggetto scientifico del claim MECH-23 originale (Phase 7.2),
o un fenomeno correlato ma distinto?

Nessun file frozen esistente e' toccato da questo script - ne'
seq0014_frozen_structural_spec_v1.json ne' seq0014_statistical_
preregistration_v1.json vengono riscritti. Questo e' un NUOVO artifact
che li contestualizza, stesso stile gia' usato in Phase 7.4A
(correzioni pubblicate come nuovo documento, mai riscrittura silenziosa
di un artifact congelato)."""
import os
import sys

PHASE76A_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE76A_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE76A_DIR, "..", "..", "..", ".."))

sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

REGISTRY_PATH = os.path.join(PHASE7_DIR, "phase7_2", "market_sequence_registry_v1.json")
FROZEN_SPEC_PATH = os.path.join(PHASE7_DIR, "phase7_5c", "seq0014_frozen_structural_spec_v1.json")
PREREG_PATH = os.path.join(PHASE76A_DIR, "seq0014_statistical_preregistration_v1.json")
OUTCOME_SURFACE_PATH = os.path.join(PHASE7_DIR, "phase7_3", "outcome_surface_v3.py")


def load_mech23_registry_entry():
    registry = load_json(REGISTRY_PATH)
    for s in registry["payload"]["sequences"] if "payload" in registry else registry["sequences"]:
        if s["sequence_id"] == "SEQ-0014":
            return s
    raise RuntimeError("SEQ-0014 non trovata in market_sequence_registry_v1.json")


def main():
    mech23 = load_mech23_registry_entry()
    frozen_spec = load_json(FROZEN_SPEC_PATH)["payload"]
    prereg = load_json(PREREG_PATH)["payload"]

    payload = {
        "phase": "Phase 7.6A - MECH-23 Estimand Identity Audit",
        "trigger": "Review di 6b0c916: la preregistrazione SEQ-0014 (state-entry vs barra comparabile, "
                   "outcome=range/path-efficiency futuri) potrebbe non testare lo stesso oggetto scientifico "
                   "del claim MECH-23 originale (Phase 7.2), che parla esplicitamente di SETUP DIREZIONALI "
                   "condizionati dal regime choppy/trending, non di barre/eventi di stato.",
        "canonical_source": {
            "file": "server/research_scripts/phase7/phase7_2/market_sequence_registry_v1.json",
            "sequence_id": "SEQ-0014", "mechanism_id": "MECH-23",
            "falsification_definition_verbatim": mech23["falsification_definition"],
            "event_a_verbatim": mech23["event_a"],
            "terminal_state_conditions_verbatim": mech23["terminal_state_conditions"],
            "expected_outcome_family_verbatim": mech23["expected_outcome_family"],
            "failure_memory_relation_note_verbatim": mech23["failure_memory_relation_note"],
            "note": "failure_memory_relation_note (Phase 7.2, PRIMA di qualunque test strutturale) dichiara "
                    "esplicitamente: 'l'obiettivo e' identificare QUANDO NON tradare' - un obiettivo di "
                    "FILTRO/MODERAZIONE su altre decisioni di trading, non uno studio del prezzo della barra "
                    "di stato in se'.",
        },

        # =================================================================
        # SEZIONE 2 - Confronto formale dei due oggetti scientifici
        # =================================================================
        "estimand_comparison": {
            "current_state_entry_experiment": {
                "name": "SEQ-0014A - LOW_INFORMATION_STATE_ENTRY_PHENOMENON",
                "unit_of_analysis": "una barra H4 - specificamente lo state-entry event (prima barra della "
                                     "transizione False->True di in_state), dopo declustering episodio+embargo.",
                "exposure": "l'ingresso stesso in LOW_INFORMATION_STATE, contro una barra comparabile "
                            "(match su volatility_state_pre_entry).",
                "outcome": "comportamento del PREZZO nei 20 bar successivi ALLA STESSA barra/serie storica "
                           "(range realizzato, spostamento assoluto, path efficiency) - una proprieta' del "
                           "mercato in se', non di alcuna decisione di trading.",
                "scientific_question": "Il mercato si comporta diversamente (in termini di range/movimento "
                                        "futuro) dopo essere entrato in un regime a bassa informazione, "
                                        "rispetto a una condizione comparabile?",
                "frozen_in": "server/research_scripts/phase7/phase7_5c/seq0014_frozen_structural_spec_v1.json "
                             "(formalization) + server/research_scripts/phase7/phase7_5c/"
                             "seq0014_structural_feasibility_result_v1.json (result, FEASIBLE).",
            },
            "original_mech23_claim": {
                "name": "SEQ-0014B - LOW_INFORMATION_STATE_FILTER_UTILITY (claim originale MECH-23, Phase 7.2)",
                "unit_of_analysis": "un SETUP DIREZIONALE (es. un breakout, uno sweep, un pullback - una "
                                     "decisione di trading candidata generata da un ALTRO meccanismo) che "
                                     "nasce mentre il mercato si trova in un certo regime.",
                "exposure_moderator": "il regime prevalente AL MOMENTO DEL SETUP - CHOPPY (LOW_INFORMATION_"
                                       "STATE attivo) vs TRENDING (regime complementare, non ancora definito "
                                       "operativamente - vedi sec.7).",
                "outcome": "tasso di FALLIMENTO/RUMORE di QUEL setup direzionale (verbatim registry: 'tasso di "
                           "fallimento/rumore') - una proprieta' della PERFORMANCE DI UNA DECISIONE DI "
                           "TRADING, non del prezzo del mercato in se'.",
                "scientific_question": "I setup direzionali generati durante il regime choppy falliscono/"
                                        "producono piu' rumore rispetto a quelli generati durante il regime "
                                        "trending?",
                "frozen_in": "NESSUN artifact - mai formalizzato oltre la frase in market_sequence_registry_"
                             "v1.json (Phase 7.2).",
            },
            "classification": "RELATED_BUT_DISTINCT",
            "rationale": "NON sono lo stesso estimand: differiscono nell'UNITA' DI ANALISI (barra di stato vs "
                "setup direzionale di un altro meccanismo) e nell'OUTCOME (comportamento del prezzo in se' vs "
                "performance di una decisione di trading specifica). L'ingresso in stato-entry vs barra "
                "non-choppy (l'estimand B discusso nella preregistrazione precedente, 6b0c916) NON dimostra "
                "automaticamente il claim filter-utility: anche se il prezzo si comportasse diversamente dopo "
                "un ingresso in chop (SEQ-0014A), questo non implica ne' esclude che I SETUP DIREZIONALI DI "
                "ALTRI MECCANISMI falliscano piu' spesso quando nascono durante quel regime (SEQ-0014B) - "
                "sono proprieta' logicamente indipendenti del sistema. "
                "NON sono nemmeno INCOMPATIBILI: condividono la STESSA classificazione di stato sottostante "
                "(directional_efficiency in tercile LOW, gia' congelata in Phase 7.5C) come fondamento comune, "
                "e un risultato di SEQ-0014A potrebbe informare (mai dimostrare) l'ipotesi di SEQ-0014B (es. "
                "se il prezzo si muove poco dopo un ingresso in chop, e' plausibile - ma non provato - che "
                "setup direzionali nati in quel regime abbiano meno spazio per raggiungere un target).",
            "not_forced_equivalence_check": "Verificato esplicitamente (sec.3 della richiesta): "
                "'state-entry vs barra non-choppy' NON e' logicamente equivalente a 'setup direzionali in "
                "choppy vs setup direzionali in trending' - il primo confronta il comportamento futuro di DUE "
                "TIPI DI BARRE, il secondo confronta la performance di DUE POPOLAZIONI DI SETUP (che "
                "potrebbero non esistere affatto durante alcune barre di alcuni regimi, introducendo un "
                "problema di composizione campionaria assente nel primo).",
        },

        # =================================================================
        # SEZIONE 4-5 - Definizioni formali + validita' del lavoro gia' fatto
        # =================================================================
        "seq0014a_definition": {
            "sequence_family_id_reference": frozen_spec["sequence_family_id"],
            "status": "STRUCTURALLY_FEASIBLE",
            "structural_result_scope_note": "Il risultato 189(EVENT_VIEW)->128(EPISODE_VIEW)->49"
                "(INDEPENDENT_VIEW), matching 49/49, verdetto FEASIBLE (Phase 7.5C, commit 844f852) resta "
                "VALIDO e INVARIATO - ma SOLO come risultato del fenomeno state-entry (SEQ-0014A). NON deve "
                "essere reinterpretato, ora o in futuro, come evidenza strutturale a favore del claim "
                "filter-utility (SEQ-0014B), che e' un esperimento diverso non ancora nemmeno formalizzato.",
            "preregistration_status": "Ereditato da 6b0c916, ora esplicitamente scoped a SEQ-0014A: "
                "STRUCTURALLY_FEASIBLE_PREREGISTRATION_BLOCKED_ON_CONTROL_POOL_VARIANT (rinominato da "
                "'estimand A/B' per evitare collisione col nuovo A/B di identita' - vedi "
                "control_pool_variant_naming_correction sotto). Non risolto qui - fuori scope di questo audit.",
            "control_pool_variant_naming_correction": "La preregistrazione precedente (6b0c916) usava le "
                "lettere 'A'/'B' per due VARIANTI DI CONTROL POOL all'interno dello STESSO esperimento "
                "state-entry (barra generica vs barra specificamente non-low-info). Questo audit introduce "
                "'SEQ-0014A'/'SEQ-0014B' per due ESPERIMENTI DIVERSI. Per evitare confusione, le varianti di "
                "control pool sono rinominate qui: CONTROL_POOL_VARIANT_GENERIC (ex 'estimand A') e "
                "CONTROL_POOL_VARIANT_NON_LOW_INFO (ex 'estimand B') - nessun cambiamento di sostanza, solo "
                "di etichetta, per chiarezza.",
        },
        "seq0014b_definition": {
            "sequence_family_id_reference": None,
            "status": "NEEDS_DIRECTIONAL_SETUP_POPULATION_SPECIFICATION",
            "note": "MAI formalizzato oltre la frase originale del registry Phase 7.2 - nessun detector, "
                    "nessuna structural spec, nessun preflight creati per SEQ-0014B in questa fase (ne' in "
                    "alcuna fase precedente).",
        },

        # =================================================================
        # SEZIONE 7 - Cosa manca per operazionalizzare SEQ-0014B (nessuna risposta inventata)
        # =================================================================
        "seq0014b_missing_specification": {
            "status": "NEEDS_DIRECTIONAL_SETUP_POPULATION_SPECIFICATION",
            "open_questions": [
                {"question": "Quale popolazione di 'setup direzionali' costituisce l'unita' di analisi?",
                 "not_specified_in_registry": True,
                 "existing_raw_material_not_a_decision": "Il progetto ha gia' 6 famiglie di eventi "
                     "potenzialmente 'direzionali' in server/research_scripts/phase5/build_events.py/"
                     "phase7_1/build_events_p71.py: BREAKOUT, DISPLACEMENT, VOLATILITY_EXPANSION, PULLBACK, "
                     "COMPRESSION_RELEASE, SWEEP(+RECLAIM) - elencate qui SOLO come inventario di cio' che "
                     "esiste gia', NON come scelta gia' fatta per SEQ-0014B."},
                {"question": "Come si opera zionalizza 'TRENDING' come regime complementare a "
                              "LOW_INFORMATION_STATE?",
                 "not_specified_in_registry": True,
                 "note": "Il terzile HIGH di directional_efficiency (complementare al terzile LOW gia' "
                         "congelato per SEQ-0014A) e' un candidato naturale MA non ancora congelato - "
                         "resterebbe da decidere se MED va escluso, incluso in TRENDING, o trattato come "
                         "terza categoria."},
                {"question": "Quale definizione di 'entry/trigger' identifica il momento t in cui un setup "
                              "direzionale 'nasce', da cui leggere il regime prevalente?",
                 "not_specified_in_registry": True},
                {"question": "Quale outcome operazionalizza 'tasso di fallimento/rumore' del setup?",
                 "not_specified_in_registry": True,
                 "existing_candidates_not_a_decision": "outcome_surface_v3.py:ALL_OUTCOME_DEFINITIONS ha gia' "
                     "REVERSAL_PROBABILITY, MAE, e le famiglie P_PLUS_*ATR_BEFORE_MINUS_1ATR (tutte "
                     "direzionali, adatte per costruzione a un setup CON una direzione propria, a differenza "
                     "di SEQ-0014A che e' NON_DIRECTIONAL) - elencate come possibilita' esistenti, non come "
                     "scelta."},
                {"question": "Quale baseline/contrasto accoppiato confronta 'stesso setup in choppy' con "
                              "'stesso setup in trending' (matched su quali dimensioni)?",
                 "not_specified_in_registry": True},
            ],
            "explicit_non_action": "Nessuna di queste domande e' stata risolta arbitrariamente in questo "
                                    "audit - richiederebbero una futura Phase 7.6B (o successiva) dedicata, "
                                    "con formalizzazione minima e freeze ex-ante, stesso workflow gia' "
                                    "rispettato per SEQ-0009/SEQ-0014A.",
        },

        # =================================================================
        # SEZIONE 6 - Outcome naming audit (nessuna rinominazione globale)
        # =================================================================
        "outcome_naming_audit": {
            "file": "server/research_scripts/phase7/phase7_3/outcome_surface_v3.py",
            "outcome_id": "REALIZED_VOLATILITY_AFTER_SETUP",
            "legacy_registry_definition_verbatim": "Volatilita' realizzata nell'orizzonte post-setup "
                                                    "(ALL_OUTCOME_DEFINITIONS, generico - non fissa una "
                                                    "formula specifica).",
            "formula_frozen_for_seq0014a_preregistration": "(max(high[t+1..t+20]) - min(low[t+1..t+20])) / ATR_t"
                " (server/research_scripts/phase7/phase7_6a/seq0014_statistical_preregistration_v1.json, "
                "outcome_contract.primary_outcome).",
            "metric_classification": "Questa formula e' metricamente un RANGE FUTURO ATR-normalizzato "
                "(FORWARD_RANGE_ATR), non una volatilita' realizzata in senso statistico classico (es. somma "
                "di rendimenti al quadrato/assoluti, o deviazione standard dei rendimenti nella finestra).",
            "action_taken": "L'ID di sistema 'REALIZED_VOLATILITY_AFTER_SETUP' RESTA INVARIATO (nome legacy "
                "gia' congelato in outcome_surface_v3.py, riusato per coerenza con ALL_OUTCOME_DEFINITIONS - "
                "nessuna rinominazione globale in questa fase, per istruzione esplicita). In qualunque report "
                "scientifico/prosa futuro su questo outcome, va chiamato esplicitamente 'FORWARD_RANGE_ATR "
                "(ID di sistema legacy: REALIZED_VOLATILITY_AFTER_SETUP)' per evitare l'ambiguita' con la "
                "volatilita' realizzata in senso statistico classico.",
        },

        # =================================================================
        # SEZIONE 8 - Stato aggiornato
        # =================================================================
        "updated_status": {
            "SEQ0014A_STATUS": "STRUCTURALLY_FEASIBLE_PREREGISTRATION_BLOCKED_ON_CONTROL_POOL_VARIANT",
            "MECH23_FILTER_CLAIM_STATUS": "NEEDS_DIRECTIONAL_SETUP_POPULATION_SPECIFICATION",
            "discovery_authorized_for_seq0014a": False,
            "discovery_authorized_for_seq0014b": False,
            "note": "Nessuna discovery autorizzata per nessuno dei due esperimenti finche' (A) la variante di "
                    "control pool di SEQ-0014A non e' risolta con una nuova structural spec/preflight "
                    "esplicito, E (B) SEQ-0014B non e' operazionalizzato con la sua propria formalizzazione "
                    "minima e freeze ex-ante.",
        },

        "no_control_pool_modified": True,
        "no_new_structural_spec_created": True,
        "no_new_detector_created": True,
        "frozen_structural_spec_untouched": "server/research_scripts/phase7/phase7_5c/"
                                             "seq0014_frozen_structural_spec_v1.json - nessuna modifica.",
        "frozen_preregistration_untouched": "server/research_scripts/phase7/phase7_6a/"
                                             "seq0014_statistical_preregistration_v1.json - nessuna modifica.",
        "no_nexus_outcome_data_accessed": True,
        "no_edge_discovery_performed": True,
        "seq0015_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
        "seq0009_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
    }

    out_path = os.path.join(PHASE76A_DIR, "seq0014_estimand_identity_audit_v1.json")
    save_json(out_path, wrap_with_provenance(payload, "phase7/phase7_6a/build_seq0014_estimand_identity_audit.py"))
    print(f"Scritto {out_path}")
    print(f"classification: {payload['estimand_comparison']['classification']}")
    print(f"SEQ0014A_STATUS: {payload['updated_status']['SEQ0014A_STATUS']}")
    print(f"MECH23_FILTER_CLAIM_STATUS: {payload['updated_status']['MECH23_FILTER_CLAIM_STATUS']}")


if __name__ == "__main__":
    main()
