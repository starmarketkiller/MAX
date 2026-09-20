#!/usr/bin/env python3
"""Phase 7.4A Dependence Validity Gate sec.5-6 - applica il Dependence
Validity Gate a OGNI cella (candidate x outcome) di una famiglia BH-FDR
PRIMA di passare i p-value a multiple_testing_v2.benjamini_hochberg
(riusato senza modifiche). Regola congelata (sec.6): family_size e'
SEMPRE il numero di celle pre-registrate (mai ridotto dopo aver visto
quali p-value sono 'brutti') - le celle non INFERENCE_VALID ricevono
p=1.0 (mai rimosse, mai None)."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from multiple_testing_v2 import benjamini_hochberg  # noqa: E402
from dependence_validity_gate import (  # noqa: E402
    compute_dependence_diagnostics, classify_dependence_validity, p_value_for_bh,
    INFERENCE_VALID, DEPENDENCE_SENSITIVE, INFERENCE_INVALID_DEPENDENCE,
)


def build_gated_bh_family(cells: list, q: float = 0.10, n_boot_diagnostics: int = 1000) -> dict:
    """cells: lista di dict {'cell_id': str, 'candidate_id': str, 'outcome_id': str,
    'd_values': list, 'raw_p_value': float}. Ritorna, per OGNI cella (family_size
    fisso = len(cells), mai ridotto), lo stato di dipendenza, il p-value
    effettivamente ammesso a BH e il risultato BH completo."""
    if not cells:
        raise ValueError("cells non puo' essere vuota - la famiglia deve essere dichiarata prima della run.")
    declared_family_size = len(cells)

    enriched = []
    for c in cells:
        diag = compute_dependence_diagnostics(c["d_values"], n_boot=n_boot_diagnostics)
        cls = classify_dependence_validity(diag)
        bh_p = p_value_for_bh(c["raw_p_value"], cls["state"])
        enriched.append({**c, "dependence_diagnostics": diag, "dependence_state": cls["state"],
                         "dependence_reason": cls["reason"], "asymmetry_sensitive": cls["asymmetry_sensitive"],
                         "bh_input_p_value": bh_p})

    bh_input = [(c["cell_id"], c["bh_input_p_value"]) for c in enriched]
    bh_result = benjamini_hochberg(bh_input, q=q)
    assert bh_result and next(iter(bh_result.values()))["m_family"] == declared_family_size, (
        "family_size effettiva in BH non coincide con family_size dichiarata - violazione sec.6"
    )

    n_by_state = {INFERENCE_VALID: 0, DEPENDENCE_SENSITIVE: 0, INFERENCE_INVALID_DEPENDENCE: 0}
    for c in enriched:
        n_by_state[c["dependence_state"]] += 1

    for c in enriched:
        c["bh_result"] = bh_result[c["cell_id"]]
        # sec.4 fail-closed: anche un adjusted_p_bh "significativo" non e' una discovery
        # se la cella non era INFERENCE_VALID (il p=1.0 gia' lo impedisce numericamente,
        # ma il flag esplicito rende il divieto verificabile senza ricalcolare BH a mano).
        c["eligible_for_discovery_verdict"] = c["dependence_state"] == INFERENCE_VALID and c["bh_result"]["significant_at_q"]

    return {
        "declared_family_size": declared_family_size,
        "n_by_dependence_state": n_by_state,
        "cells": enriched,
        "rule": "family_size non e' mai stato ridotto - le celle non INFERENCE_VALID hanno ricevuto p=1.0 prima di entrare in benjamini_hochberg (sec.6).",
    }


if __name__ == "__main__":
    import numpy as np
    rng = np.random.default_rng(5)

    def gen_ar1(rng, phi, n=30, mean_shift=0.0):
        eps = rng.normal(0.0, 1.0, n)
        x = np.empty(n)
        x[0] = eps[0] + mean_shift
        for t in range(1, n):
            x[t] = phi * x[t - 1] + eps[t] * np.sqrt(1 - phi ** 2) + mean_shift * (1 - phi)
        return x

    # Cella 1: pulita (iid, nessun effetto) -> INFERENCE_VALID, p non significativo.
    d1 = list(rng.normal(0.0, 1.0, 30))
    # Cella 2: pulita (iid, effetto forte) -> INFERENCE_VALID, p significativo, eligible.
    d2 = list(rng.normal(0.8, 1.0, 30))
    # Cella 3: fortemente autocorrelata -> deve degradare, MAI eligible anche se "sembra" un effetto.
    d3 = list(gen_ar1(rng, 0.8, mean_shift=0.8))

    from matched_pair_permutation_test import block_sign_flip_permutation_p
    cells = [
        {"cell_id": "BOTH::CLEAN_NO_EFFECT", "candidate_id": "BOTH", "outcome_id": "CLEAN_NO_EFFECT",
         "d_values": d1, "raw_p_value": block_sign_flip_permutation_p(d1, seed=1)["p_value"]},
        {"cell_id": "BOTH::CLEAN_EFFECT", "candidate_id": "BOTH", "outcome_id": "CLEAN_EFFECT",
         "d_values": d2, "raw_p_value": block_sign_flip_permutation_p(d2, seed=2)["p_value"]},
        {"cell_id": "BOTH::DEPENDENT_APPARENT_EFFECT", "candidate_id": "BOTH", "outcome_id": "DEPENDENT_APPARENT_EFFECT",
         "d_values": d3, "raw_p_value": block_sign_flip_permutation_p(d3, seed=3)["p_value"]},
    ]

    result = build_gated_bh_family(cells, q=0.10)
    print(f"declared_family_size={result['declared_family_size']}  n_by_state={result['n_by_dependence_state']}")
    for c in result["cells"]:
        print(f"  {c['cell_id']}: state={c['dependence_state']}  raw_p={c['raw_p_value']:.4f}  "
              f"bh_input_p={c['bh_input_p_value']:.4f}  adjusted_p={c['bh_result']['adjusted_p_bh']:.4f}  "
              f"eligible_for_discovery_verdict={c['eligible_for_discovery_verdict']}")

    assert result["declared_family_size"] == 3, "family_size non deve mai cambiare"
    clean_effect_cell = next(c for c in result["cells"] if c["cell_id"] == "BOTH::CLEAN_EFFECT")
    dependent_cell = next(c for c in result["cells"] if c["cell_id"] == "BOTH::DEPENDENT_APPARENT_EFFECT")
    assert dependent_cell["dependence_state"] != INFERENCE_VALID, "la cella fortemente autocorrelata non deve risultare INFERENCE_VALID"
    assert dependent_cell["eligible_for_discovery_verdict"] is False, "una cella non-valid non puo' MAI essere eligible, indipendentemente dal p-value grezzo"
    print(f"\nVerificato: cella pulita con effetto reale eligible={clean_effect_cell['eligible_for_discovery_verdict']}, "
          f"cella dipendente MAI eligible anche con un apparente effetto forte.")
    print("\nSelf-test dependence_gated_bh_family completato su dati SINTETICI.")
