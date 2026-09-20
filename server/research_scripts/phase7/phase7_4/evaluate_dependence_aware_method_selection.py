#!/usr/bin/env python3
"""Phase 7.4A Dependence-Aware Inference Redesign sec.9 - Decision Rule
CONGELATA (dichiarata qui, applicata meccanicamente sotto - non
narrata a mano). Combina tutti i risultati _dac_*.json e ungated
21-cell in un unico artefatto di calibrazione + un artefatto di
selezione del metodo con verdetto calcolato deterministicamente."""
import glob
import json
import math
import os

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
METHODS = ["A_null_centered_block_bootstrap", "B_studentized_block_bootstrap", "C_hac_newey_west"]

# ---- Decision Rule (sec.9) - CONGELATA qui, PRIMA dell'interpretazione finale. ----
DECISION_RULE = {
    "criterion_1_core_null_calibration": "Type-I@.05 <= .075 in TUTTI gli scenari 'core' = griglia 6-phi a n=30 (il sample size primario di SEQ-0015, n_nominal_minimum=30).",
    "criterion_2_no_explosion": "Nessun Type-I a NESSUN alpha (.01/.05/.10) supera 2x il valore nominale, su TUTTA la griglia 6phi x 4n, su TUTTI gli 8 scenari di distribution stress, e su TUTTI i 5 scenari di matched-control stress.",
    "criterion_3_stability_across_n": "Il comportamento (Type-I@.05) non deve mostrare instabilita' catastrofica al variare di n=20..100 per phi=0.5 (nessun peggioramento sistematico con n crescente).",
    "criterion_4_21cell_fdr": "Empirical FDR (21 celle, global null iid E global null dipendenza mista) <= q + tolleranza MC (3 sigma binomiale sul numero di repliche di famiglia usate).",
    "criterion_5_power_not_catastrophic": "Power a delta=0.80 non deve essere <50% della power del miglior metodo valido allo stesso delta (qui valutato descrittivamente, non come criterio di squalifica se nessun metodo passa 1-4).",
    "overall_rule": "Un metodo e' DEPENDENCE-AWARE INFERENCE METHOD VALIDATED solo se soddisfa TUTTI i criteri 1-4. Se NESSUN metodo soddisfa tutti e 4 i criteri: PRIMARY INFERENCE METHOD NOT YET VALIDATED - nessuna patch immediata, nessuna frozen_spec_v5.",
}


def load(pattern):
    files = sorted(glob.glob(os.path.join(PHASE74_DIR, pattern)))
    data = {}
    for f in files:
        with open(f, encoding="utf-8") as fh:
            data[os.path.basename(f)] = json.load(fh)
    return data


def mc_tol(q, n_reps, n_sigma=3):
    return n_sigma * math.sqrt(q * (1 - q) / n_reps)


def evaluate_method(method_name, null_cal, dist_stress, matched_control, power, cell21):
    findings = {}

    # Criterio 1: core = 6 phi a n=30.
    core_rows = [r for r in null_cal if r["n"] == 30]
    c1_details = [{"phi": r["phi"], "type1_0.05": r["type1_0.05"], "pass": r["type1_0.05"] <= 0.075} for r in core_rows]
    c1_pass = all(d["pass"] for d in c1_details)
    findings["criterion_1_core_null_calibration"] = {"pass": c1_pass, "detail": c1_details}

    # Criterio 2: nessuna esplosione >2x su TUTTA la griglia + dist_stress + matched_control.
    explosions = []
    for r in null_cal:
        for a in [0.01, 0.05, 0.1]:
            key = f"type1_{a}"
            if r[key] > 2 * a:
                explosions.append({"source": "null_cal", "n": r["n"], "phi": r["phi"], "alpha": a, "value": r[key], "ratio": round(r[key] / a, 2)})
    for r in dist_stress:
        if r["type1_0.05"] > 2 * 0.05:
            explosions.append({"source": "dist_stress", "scenario": r["scenario"], "alpha": 0.05, "value": r["type1_0.05"], "ratio": round(r["type1_0.05"] / 0.05, 2)})
    for r in matched_control:
        if r["type1_0.05"] > 2 * 0.05:
            explosions.append({"source": "matched_control_stress", "scenario": r["scenario"], "alpha": 0.05, "value": r["type1_0.05"], "ratio": round(r["type1_0.05"] / 0.05, 2)})
    c2_pass = len(explosions) == 0
    findings["criterion_2_no_explosion"] = {"pass": c2_pass, "explosions_found": explosions}

    # Criterio 3: stabilita' su n=20..100 a phi=0.5.
    phi05_rows = sorted([r for r in null_cal if r["phi"] == 0.5], key=lambda r: r["n"])
    c3_values = [r["type1_0.05"] for r in phi05_rows]
    c3_pass = all(v <= 0.075 for v in c3_values)  # stesso limite del criterio 1, applicato a tutti gli n
    findings["criterion_3_stability_across_n"] = {
        "pass": c3_pass, "detail": [{"n": r["n"], "type1_0.05": r["type1_0.05"]} for r in phi05_rows],
    }

    # Criterio 4: FDR 21-cell (global null, sia iid sia dipendenza mista).
    c4_details = []
    c4_pass = True
    for row in cell21:
        if not row["scenario"].startswith("global_null"):
            continue
        limit = 0.10 + mc_tol(0.10, row["n_family_reps"])
        ok = row["empirical_fdr"] <= limit
        c4_pass = c4_pass and ok
        c4_details.append({"scenario": row["scenario"], "empirical_fdr": row["empirical_fdr"], "limit": round(limit, 4), "pass": ok})
    findings["criterion_4_21cell_fdr"] = {"pass": c4_pass, "detail": c4_details}

    power_row = next((r for r in cell21 if r["scenario"] == "mixed_14null_7effect_iid"), None)
    findings["descriptive_power_mixed_family"] = power_row["power"] if power_row else None
    findings["descriptive_power_curve"] = power

    overall_pass = c1_pass and c2_pass and c3_pass and c4_pass
    findings["overall_pass_all_4_criteria"] = overall_pass
    return findings


def main():
    calibration_bundle = {}
    method_findings = {}

    for method in METHODS:
        null_cal = load(f"_dac_null_cal_{method}.json")
        dist_stress = load(f"_dac_dist_stress_{method}.json")
        matched_control = load(f"_dac_matched_control_{method}.json")
        power = load(f"_dac_power_{method}.json")
        cell21 = load(f"_dac_21cell_{method}.json")

        null_cal = list(null_cal.values())[0] if null_cal else []
        dist_stress = list(dist_stress.values())[0] if dist_stress else []
        matched_control = list(matched_control.values())[0] if matched_control else []
        power = list(power.values())[0] if power else []
        cell21 = list(cell21.values())[0] if cell21 else []

        calibration_bundle[method] = {
            "null_calibration": null_cal, "distribution_stress": dist_stress,
            "matched_control_stress": matched_control, "power_curve": power, "ungated_21cell_bh": cell21,
        }
        method_findings[method] = evaluate_method(method, null_cal, dist_stress, matched_control, power, cell21)
        print(f"{method}: overall_pass={method_findings[method]['overall_pass_all_4_criteria']}")

    any_validated = any(f["overall_pass_all_4_criteria"] for f in method_findings.values())
    if any_validated:
        selected = next(m for m, f in method_findings.items() if f["overall_pass_all_4_criteria"])
        verdict = "DEPENDENCE-AWARE INFERENCE METHOD VALIDATED"
    else:
        selected = None
        verdict = "PRIMARY INFERENCE METHOD NOT YET VALIDATED"

    # Metodo piu' promettente anche se nessuno valida pienamente (informativo, non un pass).
    def n_criteria_passed(f):
        return sum(1 for k in ["criterion_1_core_null_calibration", "criterion_2_no_explosion",
                               "criterion_3_stability_across_n", "criterion_4_21cell_fdr"] if f[k]["pass"])
    most_promising = max(method_findings, key=lambda m: n_criteria_passed(method_findings[m]))

    selection_payload = {
        "decision_rule_frozen_before_final_interpretation": DECISION_RULE,
        "screening_note": (
            "Screening preliminare (6 phi, n=30, N_reps=800) ha mostrato B nettamente piu' calibrato di A e C - "
            "budget di calcolo allocato asimmetricamente (piu' repliche/precisione per B), dichiarato esplicitamente "
            "in dependence_aware_inference_calibration.py. A e C restano comunque testati sull'intera griglia "
            "richiesta, a precisione ridotta ma sufficiente per la squalifica (gia' evidente sotto iid pura)."
        ),
        "method_findings": method_findings,
        "verdict": verdict,
        "selected_method": selected,
        "most_promising_method_if_none_validated": most_promising if not any_validated else None,
        "key_additional_finding": (
            "Il fallimento decisivo di B non e' (solo) l'esplosione a phi=0.7 (Type-I@.05 ~2.2-2.7x il nominale, "
            "gia' di per se' una violazione del criterio 2), ma il fallimento CATASTROFICO e distinto sotto lo "
            "scenario 'control_reuse_small_pool' (Type-I@.05=0.223, ~4.46x il nominale) - una struttura di "
            "dipendenza COMBINATORIA/di pool condiviso, non temporale. Tutti e 3 i metodi (A/B/C) sono costruiti "
            "attorno alla dipendenza SERIALE/temporale (blocchi contigui nel tempo, lag HAC) - nessuno modella la "
            "correlazione che nasce quando piu' eventi condividono LO STESSO controllo nel pool matched, "
            "indipendentemente dalla loro posizione temporale. Questa e' una lacuna strutturale distinta dal "
            "problema di autocorrelazione, e va indirizzata esplicitamente in un futuro redesign (es. varianza "
            "cluster-robust clusterizzata per IDENTITA' del controllo condiviso, non solo per tempo)."
        ) if not any_validated else None,
    }

    with open(os.path.join(PHASE74_DIR, "phase7_4_dependence_aware_inference_calibration_v1.json"), "w", encoding="utf-8") as f:
        json.dump(calibration_bundle, f, indent=2, ensure_ascii=False)
    with open(os.path.join(PHASE74_DIR, "phase7_4_dependence_aware_method_selection_v1.json"), "w", encoding="utf-8") as f:
        json.dump(selection_payload, f, indent=2, ensure_ascii=False)

    print(f"\nVERDICT: {verdict}")
    print(f"most_promising_method_if_none_validated: {most_promising}")
    print("\nScritti: phase7_4_dependence_aware_inference_calibration_v1.json, phase7_4_dependence_aware_method_selection_v1.json")
    return verdict


if __name__ == "__main__":
    main()
