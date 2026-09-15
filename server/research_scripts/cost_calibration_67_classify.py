#!/usr/bin/env python3
"""
NEXUS Cost Calibration Final - Reclassification, ranking, promotion gate.

Legge results/cost_calibration_67_rerun/rerun_results.json (prodotto da
cost_calibration_67_rerun.py) e applica classificazione/ranking/gate. Nessuna
strategia modificata, nessun parametro ottimizzato qui.
"""
import json
import os

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                             "results", "cost_calibration_67_rerun", "rerun_results.json")
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                         "results", "cost_calibration_67_rerun", "classification.json")

MIN_SAMPLE = 30
MAX_DD_ACCEPTABLE = 25.0   # soglia dichiarata per il promotion gate, non ottimizzata


def classify(strat, profiles):
    zero = profiles["ZERO_COST"]
    base = profiles["BROKER_BASELINE"]
    cons = profiles["CONSERVATIVE"]
    stress = profiles["STRESS"]

    if "error" in zero or "error" in base:
        return "ERROR", "run fallito"
    n = base.get("n") or 0
    if n < MIN_SAMPLE:
        return "INSUFFICIENT_SAMPLE", f"n={n} < {MIN_SAMPLE}"

    gross_pf = base.get("gross_pf")
    pf_base = base.get("pf")
    pf_cons = cons.get("pf")
    pf_stress = stress.get("pf")

    if gross_pf is None or gross_pf <= 1.0:
        return "NEGATIVE_EVEN_ZERO_COST", f"gross_pf={gross_pf}"
    if pf_base is None or pf_base <= 1.0:
        return "GROSS_EDGE_COST_SENSITIVE", f"gross_pf={gross_pf} ma pf_baseline={pf_base}"
    if pf_stress is None or pf_stress <= 1.0:
        if pf_cons is not None and pf_cons > 1.0:
            return "BROKER_BASELINE_PASS_STRESS_FAIL", f"pf_baseline={pf_base} pf_conservative={pf_cons} pf_stress={pf_stress}"
        return "BORDERLINE", f"pf_baseline={pf_base} pf_conservative={pf_cons} pf_stress={pf_stress}"
    return "ROBUST_POSITIVE", f"pf_baseline={pf_base} pf_stress={pf_stress}"


def promotion_gate(strat, profiles, classification):
    if classification != "ROBUST_POSITIVE":
        return False, "non ROBUST_POSITIVE"
    base = profiles["BROKER_BASELINE"]
    cons = profiles["CONSERVATIVE"]
    n = base.get("n") or 0
    if n < MIN_SAMPLE:
        return False, f"sample insufficiente n={n}"
    if (base.get("expectancy_r") or 0) <= 0:
        return False, "expectancy non positiva"
    if (cons.get("pf") or 0) <= 1.0:
        return False, "collassa CONSERVATIVE"
    if (base.get("dd") or 999) > MAX_DD_ACCEPTABLE:
        return False, f"DD baseline {base.get('dd')}% > {MAX_DD_ACCEPTABLE}%"
    return True, "tutti i criteri soddisfatti"


def main():
    with open(RESULTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    results = data["results"]

    classified = {}
    for strat, info in results.items():
        cls, reason = classify(strat, info["profiles"])
        promoted, promo_reason = promotion_gate(strat, info["profiles"], cls)
        classified[strat] = {
            "tf": info["tf"], "classification": cls, "reason": reason,
            "promoted": promoted, "promotion_reason": promo_reason,
            "profiles": info["profiles"],
        }

    from collections import Counter
    counts = Counter(v["classification"] for v in classified.values())
    print("=== CLASSIFICAZIONE (67 strategie) ===")
    for k, v in counts.most_common():
        print(f"  {k}: {v}")

    # 8. false-negative audit: OLD_COST_MODEL (approssimato con CONSERVATIVE/
    #    STRESS piu' vicini ai vecchi preset retail_standard/ecn, MA qui usiamo
    #    il vero OLD_COST_MODEL = retail_standard, ricalcolato a parte se serve).
    # Qui: usiamo ZERO_COST come riferimento "gross" e BROKER_BASELINE come nuovo,
    # il confronto vero con OLD_COST_MODEL (retail_standard) e' fatto nel report
    # con i 3 casi gia' noti + questa lista ampliata a tutte le 67.
    print("\n=== TOP per PF_BASELINE (tra ROBUST_POSITIVE) ===")
    robust = [(s, v) for s, v in classified.items() if v["classification"] == "ROBUST_POSITIVE"]
    robust.sort(key=lambda x: -(x[1]["profiles"]["BROKER_BASELINE"].get("pf") or 0))
    for s, v in robust[:15]:
        b = v["profiles"]["BROKER_BASELINE"]
        print(f"  {s:<34}{v['tf']:<5} PF={b.get('pf')} net={b.get('net')} n={b.get('n')} "
              f"DD={b.get('dd')} exp_r={b.get('expectancy_r')} promoted={v['promoted']}")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(classified, f, indent=2, default=str)
    print(f"\nSalvato in {OUT_PATH}")
    return classified


if __name__ == "__main__":
    main()
