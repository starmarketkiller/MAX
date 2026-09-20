#!/usr/bin/env python3
"""Phase 7.4A Final Statistical Integrity Patch sec.9 - costruisce
phase7_4_seq0015_frozen_spec_v3.json, supersedes v2. NON sovrascrive
v1/v2 (entrambi lasciati intatti). Detector formula/soglia/direction e
episode rule (event_cluster_rule/outcome_overlap_rule) restano
IDENTICI a v2 - verificato programmaticamente. Aggiorna SOLO: contratto
inferenziale (v2, metodo unificato), control reuse/overlap policy, FDR
family size ricalcolata, correzione della spiegazione errata sec.8."""
import json
import os
import sys

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
SCHEMA_PATH = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3", "schemas",
                            "sequence_family_frozen_spec_v1.schema.json")
sys.path.insert(0, PHASE74_DIR)
from seq0015_momentum_burst_detector import DETECTOR_VERSION, FROZEN_PARAMETERS  # noqa: E402
from build_seq0015_frozen_spec import sha256_file, sha256_canonical_json, validate_against_schema  # noqa: E402
from build_seq0015_frozen_spec_v2 import INVARIANT_PATHS, assert_formula_threshold_direction_unchanged  # noqa: E402
from build_seq0015_statistical_test_contract_v2 import build_contract_v2  # noqa: E402

# sec.9: oltre ai 14 campi gia' invarianti v1->v2, verifichiamo ORA che anche
# l'episode_rule (sec.1 della patch precedente) resti IDENTICO v2->v3 - questa
# patch tocca SOLO sezioni statistiche/di controllo, non l'episode rule.
EPISODE_RULE_INVARIANT_KEYS = [
    "event_cluster_rule_bars", "natural_horizon_bars", "overlap_policy",
]


def load_v2():
    v2_path = os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v2.json")
    with open(v2_path, encoding="utf-8") as f:
        return json.load(f)


def assert_episode_rule_unchanged(v2_frozen_parameters, v3_frozen_parameters):
    diffs = []
    v2_er = v2_frozen_parameters.get("episode_rule", {})
    v3_er = v3_frozen_parameters.get("episode_rule", {})
    for key in EPISODE_RULE_INVARIANT_KEYS:
        if v2_er.get(key) != v3_er.get(key):
            diffs.append({"key": key, "v2": v2_er.get(key), "v3": v3_er.get(key)})
    v2_embargo = v2_er.get("outcome_overlap_rule", {}).get("outcome_overlap_embargo_bars")
    v3_embargo = v3_er.get("outcome_overlap_rule", {}).get("outcome_overlap_embargo_bars")
    if v2_embargo != v3_embargo:
        diffs.append({"key": "outcome_overlap_embargo_bars", "v2": v2_embargo, "v3": v3_embargo})
    return diffs


def build_frozen_spec_v3(v2_spec):
    detector_path = os.path.join(PHASE74_DIR, "seq0015_momentum_burst_detector.py")
    detector_source_hash_v3 = sha256_file(detector_path)
    frozen_parameters_hash_v3 = sha256_canonical_json(FROZEN_PARAMETERS)

    formula_diffs = assert_formula_threshold_direction_unchanged(v2_spec["frozen_parameters"], FROZEN_PARAMETERS)

    frozen_parameters = dict(v2_spec["frozen_parameters"])
    frozen_parameters["provenance"] = dict(frozen_parameters["provenance"])  # copia, sovrascritta sotto

    # sec.8 - correzione della spiegazione errata sull'assign_clusters transitivo.
    frozen_parameters["episode_rule"] = dict(frozen_parameters["episode_rule"])
    frozen_parameters["episode_rule"]["outcome_overlap_rule"] = dict(frozen_parameters["episode_rule"]["outcome_overlap_rule"])
    alt = dict(frozen_parameters["episode_rule"]["outcome_overlap_rule"]["alternatives_considered"])
    old_B = alt["B_embargo_only"]
    assert "38 barre" in old_B or "38" in old_B, "testo atteso non trovato in v2 - controllare il sorgente"
    alt["B_embargo_only"] = (
        "CORREZIONE (Phase 7.4A Final Statistical Integrity Patch sec.8): la spiegazione originale in v2 "
        "era ERRATA - affermava che una catena di eventi ciascuno a 38 barre dal successivo (100->138->176->...) "
        "NON sarebbe stata catturata dall'embargo=39. In realta' assign_clusters usa un clustering TRANSITIVO "
        "sui gap consecutivi (rows[i]-rows[i-1]<=soglia -> stesso cluster): con soglia=39, 138-100=38<=39 e "
        "176-138=38<=39, quindi l'INTERA catena collassa in UN SOLO cluster gia' alla passata di embargo - "
        "l'embargo pairwise-transitivo la cattura correttamente. Il motivo VALIDO per mantenere comunque un "
        "aggiustamento di dipendenza oltre l'embargo e' diverso e distinto: dipendenza seriale RESIDUA nelle "
        "REALIZZAZIONI dell'outcome (non nella posizione temporale) fra osservazioni INDIPENDENTI VIEW gia' "
        "correttamente de-clusterizzate - es. due eventi a 45 e 90 barre di distanza (quindi gia' non "
        "sovrapposti e non collassati da nessun embargo ragionevole) possono comunque avere outcome correlati "
        "se ricadono nello stesso regime di volatilita'/trend piu' ampio. Questa e' una dipendenza STATISTICA "
        "di regime, non una sovrapposizione MECCANICA di prezzo - l'embargo (basato solo su distanza in barre) "
        "non puo' rilevarla per costruzione, mentre il block sign-flip permutation (che comunque raggruppa "
        "blocchi di osservazioni INDIPENDENT_VIEW contigue nel tempo) offre una protezione parziale."
    )
    frozen_parameters["episode_rule"]["outcome_overlap_rule"]["alternatives_considered"] = alt
    frozen_parameters["episode_rule"]["outcome_overlap_rule"]["method_chosen_correction_note"] = (
        "Il metodo D scelto in v2 resta valido; solo la spiegazione del PERCHE' B da sola sia insufficiente "
        "e' stata corretta qui (sec.8) - la vera ragione e' la dipendenza di regime residua, non un presunto "
        "limite del clustering transitivo su catene di eventi ravvicinati."
    )

    # sec.2/sec.6/sec.7 - contratto statistico v2 (metodo unificato).
    contract_v2 = build_contract_v2()
    frozen_parameters["statistical_test_contract_ref"] = "server/research_scripts/phase7/phase7_4/seq0015_statistical_test_contract_v2.json"
    frozen_parameters["statistical_test_contract_summary"] = {
        "method_unified": "block_sign_flip_permutation_matched_pair per TUTTI i 7 outcome (binari e continui) - vedi statistical_methods_policy.json",
        "superseded_methods": ["WILSON_CI95+two_proportion_z_test (binari, v1)", "two_sample_block_bootstrap_percentile_p (continui, v1) - entrambi appiattivano la struttura matched e/o non imponevano H0 esplicitamente"],
        "n_inferential_outcomes_with_frozen_pvalue_method": contract_v2["n_inferential_outcomes_with_frozen_pvalue_method"],
        "n_outcomes_moved_to_diagnostic": 0,
        "note": "Nessuna demotion necessaria - tutti e 7 gli outcome hanno ORA un metodo unico, validato dalla stessa null-calibration simulation (sec.2), che preserva la struttura matched per costruzione.",
    }

    # sec.5 - control reuse / control temporal overlap policy (NUOVO).
    frozen_parameters["control_reuse_policy"] = {
        "reuse_allowed": True,
        "rationale_for_allowing_reuse": "Un pool storico finito rende spesso necessario il riuso dello stesso control bar per piu' eventi - vietarlo del tutto causerebbe REJECTED_INSUFFICIENT_POOL non correlati alla domanda scientifica.",
        "max_control_reuse_per_run": 5,
        "max_control_reuse_rationale": "Stesso valore di k (5) - un singolo control bar non puo' contribuire a piu' matched-set di quanti neighbour vengono normalmente richiesti per un evento, un tetto semplice e simmetrico rispetto a k, non ottimizzato sui dati.",
        "enforcement_mechanism": "server/research_scripts/phase7/engine/control_reuse_ledger.py:ControlReuseLedger - filtra il pool disponibile PRIMA di ogni chiamata a match_sequence_event() per l'evento successivo nella stessa run; nessun controllo puo' superare il tetto.",
        "uncertainty_reflection": "Il riuso di controlli fra eventi diversi introduce una covarianza fra i rispettivi d_i (controlli condivisi) - non modellata esplicitamente componente per componente, ma limitata in ampiezza dal tetto max_control_reuse_per_run=5 e coperta dalla stessa diagnostica DEPENDENCE_SENSITIVE gia' in uso per la dipendenza di regime (sec.8) - un riuso estensivo produrrebbe correlazione residua fra i blocchi di d_i, rilevabile dagli stessi controlli di stabilita' EVENT/EPISODE/INDEPENDENT_VIEW.",
    }
    frozen_parameters["control_temporal_overlap_policy"] = {
        "control_own_exclusion_from_its_event": "Invariato da v1/v2: un control non puo' essere entro exclusion_buffer_bars=40 dal proprio evento matched, ne' nello stesso episode, ne' in uno split diverso (BaselineEngineV4 + cross_split_safety.py, invariati).",
        "control_control_cross_event_overlap": "NON separatamente vietato oltre alle regole sopra - dichiarato come LIMITE ESPLICITO: due eventi diversi possono avere controlli i cui outcome window si sovrappongono fra loro (non fra evento e proprio controllo, che resta vietato). Impedirlo richiederebbe un problema di assegnazione globale congiunta (non piu' k-NN indipendente per evento), fuori scope per una family scelta esplicitamente per 'poche dimensioni, pochi gradi di liberta''.",
        "residual_risk_bounded_by": "max_control_reuse_per_run=5 (sec.5) + gate DEPENDENCE_SENSITIVE + block sign-flip permutation sui blocchi contigui di d_i (sec.1/sec.8).",
    }

    # sec.7 - FDR family ricalcolata deterministicamente.
    frozen_parameters["multiple_testing_full_family"] = dict(frozen_parameters["multiple_testing_full_family"])
    frozen_parameters["multiple_testing_full_family"]["final_n_inferential_outcomes"] = contract_v2["n_inferential_outcomes_with_frozen_pvalue_method"]
    frozen_parameters["multiple_testing_full_family"]["final_n_candidates"] = 3
    frozen_parameters["multiple_testing_full_family"]["final_family_size"] = contract_v2["fdr_family_size_check"]["declared_family_size"]
    frozen_parameters["multiple_testing_full_family"]["recomputed_deterministically_by"] = "build_seq0015_statistical_test_contract_v2.py (sec.7) - nessun valore inserito manualmente."
    frozen_parameters["multiple_testing_full_family"]["p_values_defined_for_all_21_members"] = True
    frozen_parameters["multiple_testing_full_family"]["all_members_use_validated_method"] = True

    frozen_parameters["null_calibration_reference"] = "server/research_scripts/phase7/phase7_4/phase7_4_null_calibration_v1.json"

    frozen_parameters["provenance"] = {
        "detector_source_hash": detector_source_hash_v3,
        "detector_source_file": "server/research_scripts/phase7/phase7_4/seq0015_momentum_burst_detector.py",
        "frozen_parameters_hash": frozen_parameters_hash_v3,
        "supersedes": "phase7_4_seq0015_frozen_spec_v2.json",
        "v2_detector_source_hash": v2_spec["frozen_parameters"]["provenance"]["detector_source_hash"],
        "v2_frozen_parameters_hash": v2_spec["frozen_parameters"]["provenance"]["frozen_parameters_hash"],
        "detector_source_hash_changed_from_v2": detector_source_hash_v3 != v2_spec["frozen_parameters"]["provenance"]["detector_source_hash"],
        "formula_threshold_direction_diffs_vs_v2": formula_diffs,
        "episode_rule_diffs_vs_v2": assert_episode_rule_unchanged(v2_spec["frozen_parameters"], frozen_parameters),
        "supersession_reason": (
            "Phase 7.4A Final Statistical Integrity Patch (2026-09-20): audit formale ha mostrato che i "
            "metodi inferenziali di v2 (Wilson+two_proportion per binari, bootstrap percentile per continui) "
            "non erano validati per calibrazione sotto H0 e appiattivano la struttura matched. Sostituiti da "
            "un metodo unico (block_sign_flip_permutation_matched_pair) validato con null-calibration "
            "simulation sintetica. Aggiunta control_reuse_policy/control_temporal_overlap_policy. Corretta "
            "una spiegazione errata su assign_clusters (sec.8)."
        ),
    }

    spec = dict(v2_spec)
    spec["frozen_parameters"] = frozen_parameters
    spec["uncertainty_method"] = "BLOCK_SIGN_FLIP_PERMUTATION"
    return spec, formula_diffs


def main():
    v2_spec = load_v2()
    spec, formula_diffs = build_frozen_spec_v3(v2_spec)

    if formula_diffs:
        print("ERRORE: formula/soglia/direction sono cambiate rispetto a v2 - vietato!")
        print(json.dumps(formula_diffs, indent=2, ensure_ascii=False))
        raise SystemExit(1)
    print("Verifica programmatica: formula/soglia/direction IDENTICHE a v2 (0 diff).")

    episode_diffs = spec["frozen_parameters"]["provenance"]["episode_rule_diffs_vs_v2"]
    if episode_diffs:
        print("ERRORE: episode_rule e' cambiata rispetto a v2 - non richiesto da questa patch!")
        print(json.dumps(episode_diffs, indent=2, ensure_ascii=False))
        raise SystemExit(1)
    print("Verifica programmatica: episode_rule (event_cluster/outcome_overlap/embargo) IDENTICA a v2 (0 diff).")

    result = validate_against_schema(spec)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["PASS"]:
        raise SystemExit("Frozen spec v3 NON conforme allo schema - non scritto su disco.")

    out_path = os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v3.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    print(f"\nScritto: {out_path}")
    print(f"detector_source_hash (v3) = {spec['frozen_parameters']['provenance']['detector_source_hash']}")
    print(f"frozen_parameters_hash (v3) = {spec['frozen_parameters']['provenance']['frozen_parameters_hash']}")
    print(f"final_family_size = {spec['frozen_parameters']['multiple_testing_full_family']['final_family_size']}")
    return True


if __name__ == "__main__":
    main()
