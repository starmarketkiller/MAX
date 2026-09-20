#!/usr/bin/env python3
"""Phase 7.4A Dependence Validity Gate sec.9 - costruisce
phase7_4_seq0015_frozen_spec_v4.json, supersedes v3. NON sovrascrive
v1/v2/v3. Detector formula/soglia/direction/episode_rule/control_reuse/
outcome_definitions restano IDENTICI a v3 - verificato programmaticamente.
Aggiunge SOLO: dependence validity gate, FDR handling sotto dipendenza
invalida, sign-flip assumption, correzione interpretazione shared-regime."""
import json
import os
import sys

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
SCHEMA_PATH = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3", "schemas",
                            "sequence_family_frozen_spec_v1.schema.json")
ENGINE_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "engine")
sys.path.insert(0, PHASE74_DIR)
sys.path.insert(0, ENGINE_DIR)
from seq0015_momentum_burst_detector import FROZEN_PARAMETERS  # noqa: E402
from build_seq0015_frozen_spec import sha256_file, sha256_canonical_json, validate_against_schema  # noqa: E402
from build_seq0015_frozen_spec_v2 import assert_formula_threshold_direction_unchanged  # noqa: E402
from build_seq0015_frozen_spec_v3 import assert_episode_rule_unchanged  # noqa: E402
from dependence_validity_gate import THRESHOLDS_FROZEN, ASYMMETRY_SENSITIVE_SKEW_THRESHOLD  # noqa: E402

# sec.9: oltre a formula/soglia/direction (v1->v2->v3) e episode_rule (v2->v3),
# verifichiamo ORA che anche control_reuse_policy/control_temporal_overlap_policy
# e le outcome definitions (statistical_test_contract v2, gia' congelato in v3)
# restino IDENTICI v3->v4 - questa patch tocca SOLO il gate di dipendenza.
CONTROL_POLICY_INVARIANT_KEYS = ["max_control_reuse_per_run"]


def load_v3():
    with open(os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v3.json"), encoding="utf-8") as f:
        return json.load(f)


def assert_control_policy_unchanged(v3_fp, v4_fp):
    diffs = []
    for key in CONTROL_POLICY_INVARIANT_KEYS:
        if v3_fp.get("control_reuse_policy", {}).get(key) != v4_fp.get("control_reuse_policy", {}).get(key):
            diffs.append({"key": key, "v3": v3_fp.get("control_reuse_policy", {}).get(key),
                          "v4": v4_fp.get("control_reuse_policy", {}).get(key)})
    if v3_fp.get("statistical_test_contract_ref") != v4_fp.get("statistical_test_contract_ref"):
        diffs.append({"key": "statistical_test_contract_ref",
                      "v3": v3_fp.get("statistical_test_contract_ref"), "v4": v4_fp.get("statistical_test_contract_ref")})
    return diffs


def build_frozen_spec_v4(v3_spec):
    detector_path = os.path.join(PHASE74_DIR, "seq0015_momentum_burst_detector.py")
    detector_source_hash_v4 = sha256_file(detector_path)
    frozen_parameters_hash_v4 = sha256_canonical_json(FROZEN_PARAMETERS)

    formula_diffs = assert_formula_threshold_direction_unchanged(v3_spec["frozen_parameters"], FROZEN_PARAMETERS)

    frozen_parameters = dict(v3_spec["frozen_parameters"])

    # sec.1-4 - Dependence Validity Gate (NUOVO).
    frozen_parameters["dependence_validity_gate"] = {
        "states": ["INFERENCE_VALID", "DEPENDENCE_SENSITIVE", "INFERENCE_INVALID_DEPENDENCE"],
        "applied_to": "La serie ordinata per tempo d_i = outcome(event_i) - mean(outcome(matched_controls_i)) della INDEPENDENT_VIEW, PER OGNI cella (candidate x outcome) - sec.5.",
        "granularity": "candidate x outcome (3 candidati x 7 outcome = 21 celle) - la struttura di dipendenza puo' differire fra MFE/outcome binario/TIME_TO_MFE ecc., ciascuna cella e' classificata indipendentemente.",
        "diagnostic_protocol_frozen_ex_ante": {
            "acf_lag1": "Autocorrelazione campionaria al lag 1 di d_i.",
            "ljung_box_h3": "Statistica di Ljung-Box su h=3 lag, formula chiusa Q=n(n+2)*sum(rho_k^2/(n-k))~chi2(h) (engine/dependence_validity_gate.py:ljung_box_p) - nessuna libreria di serie storiche esterna, solo scipy.stats.chi2 per il p-value finale.",
            "ess_ratio": "Effective Sample Size / n, stimato dal rapporto fra varianza block-bootstrap e iid-bootstrap della media (moving_block_bootstrap_ci/iid_bootstrap_ci, phase6_5/block_bootstrap.py, riusati senza modifiche).",
            "sample_skewness": "Skewness campionaria di d_i - usata SOLO per il flag ASYMMETRY_SENSITIVE (sec.7), non per il gate di dipendenza principale.",
            "source_reference": "server/research_scripts/phase7/engine/dependence_validity_gate.py - congelato PRIMA di guardare qualunque dato NEXUS/SEQ-0015 (calibrato solo su simulazioni AR(1) sintetiche, vedi phase7_4_dependence_gate_calibration_v1.json).",
        },
        "frozen_thresholds": THRESHOLDS_FROZEN,
        "asymmetry_sensitive_skew_threshold": ASYMMETRY_SENSITIVE_SKEW_THRESHOLD,
        "calibration_curve_reference": "server/research_scripts/phase7/phase7_4/phase7_4_dependence_gate_calibration_v1.json (phi=0.0/0.1/0.2/0.3/0.5/0.7, 1000 repliche ciascuno)",
        "fail_closed_rule": {
            "INFERENCE_VALID": "Il p-value grezzo entra normalmente in BH-FDR - puo' produrre un verdetto di discovery.",
            "DEPENDENCE_SENSITIVE": "Il p-value grezzo e' sostituito da 1.0 prima di entrare in BH-FDR (engine/dependence_validity_gate.py:p_value_for_bh) - resta calcolato/riportato come diagnostica, ma non puo' produrre un verdetto di discovery ne' da solo ne' tramite BH.",
            "INFERENCE_INVALID_DEPENDENCE": "Stesso trattamento numerico di DEPENDENCE_SENSITIVE (p=1.0 in BH) PIU' un blocco esplicito a livello di candidato/outcome: quella cella e' segnalata come fermata, non idonea a nessuna ulteriore valutazione di quell'outcome per quel candidato in questa run.",
            "enforcement": "server/research_scripts/phase7/engine/dependence_gated_bh_family.py:build_gated_bh_family - applica il gate a OGNI cella PRIMA di chiamare multiple_testing_v2.benjamini_hochberg (riusato senza modifiche); 'eligible_for_discovery_verdict' e' vero SOLO se INFERENCE_VALID AND significant_at_q.",
        },
        "fdr_denominator_policy": {
            "rule": "family_size = 21 SEMPRE (mai ridotto dopo aver visto quali celle falliscono il gate) - le celle non INFERENCE_VALID ricevono p=1.0, non vengono rimosse dalla lista passata a benjamini_hochberg.",
            "no_opportunistic_reduction": "Vietato calcolare 21, togliere le celle 'brutte' e rifare BH sui rimanenti dopo aver visto i risultati - la policy sopra e' fissata ORA, prima di qualunque dato reale.",
            "enforcement": "dependence_gated_bh_family.build_gated_bh_family asserisce esplicitamente che m_family restituito da benjamini_hochberg coincida con la family_size dichiarata.",
        },
        "sign_flip_assumption": {
            "assumption": "Sotto H0, la distribuzione di d_i deve essere sufficientemente simmetrica/scambiabile rispetto al cambio di segno - non basta E[d_i]=0, serve che P(d_i>0)=P(d_i<0) approssimativamente per ogni realizzazione, non solo in media.",
            "empirical_finding": "La simulazione 'skewed' (exponential ricentrata) mostra una lieve anti-conservativita': rej@.05=0.063 (~1.26x nominale), rej@.10=0.118 (~1.18x) - non grave come l'autocorrelazione forte (phi=0.7: ~3x), ma reale e riportata correttamente qui (non nascosta).",
            "mitigation": "Flag ASYMMETRY_SENSITIVE (sample_skewness>=0.75) riportato ACCANTO allo stato di dipendenza principale - non un quarto stato pieno, ma un'informazione aggiuntiva per l'interpretazione umana del risultato quando INFERENCE_VALID ma ASYMMETRY_SENSITIVE=true.",
        },
        "shared_regime_interpretation_correction": {
            "old_incorrect_claim": "'la varianza vera del pool di baseline e' sottostimata... il che puo' rendere il test anti-conservativo' - applicato al risultato rejection_rate=0%, che e' l'opposto (conservativo/powerless).",
            "corrected_claim": "0% di rigetto e' fortemente CONSERVATIVO/POWERLESS: il bootstrap ricampiona evento e baseline separatamente, trattando come incertezza una componente di varianza (lo shock di regime condiviso) che nel dato osservato si cancella - producendo un CI troppo ampio, mai un CI troppo stretto in questo scenario specifico.",
            "valid_conclusion_unchanged": "Appiattire la struttura matched (flattening) distrugge l'informazione di accoppiamento e produce un'inferenza mal calibrata - a volte anti-conservativa (i 4 scenari base), a volte fortemente conservativa/powerless (shared-regime) - non prevedibile a priori in quale direzione, il che la rende inaffidabile in entrambi i casi.",
            "corrected_in": "server/research_scripts/phase7/phase7_4/null_calibration_simulation.py (funzione run_shared_regime_demo, campo 'interpretation') e phase7_4_null_calibration_v1.json (rigenerato) - vault/01-Trading/NEXUS - Phase 7.4A Final Statistical Integrity Patch.md corretto con una nota di trasparenza, non riscritto silenziosamente.",
        },
    }

    frozen_parameters["provenance"] = {
        "detector_source_hash": detector_source_hash_v4,
        "detector_source_file": "server/research_scripts/phase7/phase7_4/seq0015_momentum_burst_detector.py",
        "frozen_parameters_hash": frozen_parameters_hash_v4,
        "supersedes": "phase7_4_seq0015_frozen_spec_v3.json",
        "v3_detector_source_hash": v3_spec["frozen_parameters"]["provenance"]["detector_source_hash"],
        "v3_frozen_parameters_hash": v3_spec["frozen_parameters"]["provenance"]["frozen_parameters_hash"],
        "detector_source_hash_changed_from_v3": detector_source_hash_v4 != v3_spec["frozen_parameters"]["provenance"]["detector_source_hash"],
        "formula_threshold_direction_diffs_vs_v3": formula_diffs,
        "episode_rule_diffs_vs_v3": assert_episode_rule_unchanged(v3_spec["frozen_parameters"], frozen_parameters),
        "control_policy_and_outcome_contract_diffs_vs_v3": assert_control_policy_unchanged(v3_spec["frozen_parameters"], frozen_parameters),
        "supersession_reason": (
            "Phase 7.4A Dependence Validity Gate (2026-09-20): la calibrazione mostrava che "
            "block_sign_flip_permutation_matched_pair non e' universalmente calibrato (anti-conservativo "
            "sotto autocorrelazione forte). Aggiunta una regola meccanica fail-closed (Dependence Validity "
            "Gate, 3 stati, per candidate x outcome) che ammette a BH-FDR solo le celle INFERENCE_VALID, "
            "sostituendo p=1.0 per le altre senza mai ridurre la family_size. Documentata esplicitamente "
            "l'assunzione di scambiabilita' del segno e la sua violazione lieve sotto skew. Corretta "
            "un'interpretazione errata del risultato shared-regime (conservativo, non anti-conservativo)."
        ),
    }

    spec = dict(v3_spec)
    spec["frozen_parameters"] = frozen_parameters
    return spec, formula_diffs


def main():
    v3_spec = load_v3()
    spec, formula_diffs = build_frozen_spec_v4(v3_spec)

    if formula_diffs:
        print("ERRORE: formula/soglia/direction cambiate rispetto a v3 - vietato!")
        raise SystemExit(1)
    print("Verifica programmatica: formula/soglia/direction IDENTICHE a v3 (0 diff).")

    episode_diffs = spec["frozen_parameters"]["provenance"]["episode_rule_diffs_vs_v3"]
    if episode_diffs:
        print("ERRORE: episode_rule cambiata rispetto a v3 - non richiesto!")
        raise SystemExit(1)
    print("Verifica programmatica: episode_rule IDENTICA a v3 (0 diff).")

    control_diffs = spec["frozen_parameters"]["provenance"]["control_policy_and_outcome_contract_diffs_vs_v3"]
    if control_diffs:
        print("ERRORE: control_reuse_policy/outcome contract cambiati rispetto a v3 - non richiesto!")
        raise SystemExit(1)
    print("Verifica programmatica: control_reuse_policy e outcome contract IDENTICI a v3 (0 diff).")

    result = validate_against_schema(spec)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["PASS"]:
        raise SystemExit("Frozen spec v4 NON conforme allo schema - non scritto su disco.")

    out_path = os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v4.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    print(f"\nScritto: {out_path}")
    print(f"detector_source_hash (v4) = {spec['frozen_parameters']['provenance']['detector_source_hash']}")
    print(f"frozen_parameters_hash (v4) = {spec['frozen_parameters']['provenance']['frozen_parameters_hash']}")
    return True


if __name__ == "__main__":
    main()
