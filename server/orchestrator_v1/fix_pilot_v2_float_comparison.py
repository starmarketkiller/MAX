#!/usr/bin/env python3
"""Fix mirato: il verificatore di pilot_run_v2_result_v1.json usava dict
equality stretta (==), che su float derivati da SOMME fatte in ordini
diversi (accumulo incrementale nel codice del modello vs sum() su lista nel
riferimento indipendente) produce falsi negativi per rumore di
arrotondamento (~1e-14/1e-15), non per errori di logica reali - verificato
manualmente per BREAKOUT_ACC/temporal_concentration (42.61999999999999 vs
42.62, differenza 7.1e-15). Questo script RICALCOLA il confronto con
tolleranza (math.isclose) sui dati GIA' salvati, senza richiamare il
modello - correzione dell'harness di verifica, non della logica del worker.

NON modifica il file originale (pilot_run_v2_result_v1.json resta il record
grezzo/primo-passaggio, con la propria provenance/hash intatta) - scrive un
nuovo artifact separato con provenance propria, per non invalidare l'hash
canonico del file originale."""
import json
import math
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def _deep_isclose(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a.keys()) == set(b.keys()) and all(_deep_isclose(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_deep_isclose(x, y) for x, y in zip(a, b))
    return a == b


def main():
    path = os.path.join(ORCH_DIR, "pilot_run_v2_result_v1.json")
    payload = load_json(path)["payload"]
    corrections = []

    for strat, tasks in payload["attempts"].items():
        for task_name, a in tasks.items():
            if a["parsed_output"] is not None:
                tolerant_match = _deep_isclose(a["parsed_output"], a["expected_output"])
                if tolerant_match != a["matches_independent_verification"]:
                    corrections.append(f"{strat}/{task_name}")
                    a["matches_independent_verification_strict_equality"] = a["matches_independent_verification"]
                    a["matches_independent_verification"] = tolerant_match
                    a["pilot_task_passed"] = (a["execution"]["returncode"] == 0) and tolerant_match
                    a["verification_note"] = ("Corretto con confronto float tollerante "
                                             "(math.isclose, rel_tol=1e-9) - il valore originale "
                                             "era un falso negativo da rumore di arrotondamento "
                                             "(~1e-15) dovuto a ordine di somma diverso fra il "
                                             "codice del modello e il riferimento indipendente, "
                                             "non un errore di logica del modello.")

    payload["overall_pilot_passed"] = all(
        a["temporal_concentration"]["pilot_task_passed"] and a["exit_efficiency"]["pilot_task_passed"]
        for a in payload["attempts"].values())
    payload["float_comparison_corrections_applied"] = corrections
    payload["correction_methodology_note"] = ("File derivato da pilot_run_v2_result_v1.json - "
                                              "stessi dati grezzi (raw_model_response, "
                                              "extracted_code, execution), SOLO il confronto di "
                                              "verifica per i campi float e' stato reso "
                                              "tollerante (era troppo rigido nell'originale). "
                                              "Nessuna chiamata al modello ripetuta.")

    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "pilot_run_v2_result_CORRECTED_v1.json")
    save_json(out_path, doc)
    print(f"Correzioni applicate a: {corrections}")
    print(f"overall_pilot_passed (dopo correzione): {payload['overall_pilot_passed']}")
    print(f"Scritto {out_path}")


if __name__ == "__main__":
    main()
