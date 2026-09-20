#!/usr/bin/env python3
"""Phase 7.4A Dependence-Aware Inference Redesign sec.10 - famiglia
BH-FDR SENZA alcun gate selettivo: tutte le 21 celle (candidate x
outcome) restano nella famiglia, ciascuna con il proprio p-value
grezzo dal metodo dependence-aware scelto - MAI un p=1.0 sostituito
per 'non fidarsi' di una cella (quell'architettura e' stata abbandonata,
vedi phase7_4_dependence_gated_inference_validation_v1.json)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from multiple_testing_v2 import benjamini_hochberg  # noqa: E402


def build_ungated_bh_family(cells: list, method_fn, method_kwargs: dict, q: float = 0.10) -> dict:
    """cells: lista di dict {'cell_id':str, 'd_values': list, '_true_effect': bool (solo per simulazione)}.
    Calcola il p-value con method_fn per OGNI cella e applica benjamini_hochberg
    SENZA rimuovere o sostituire nessuna cella - family_size = len(cells) sempre."""
    if not cells:
        raise ValueError("cells non puo' essere vuota.")
    enriched = []
    for c in cells:
        r = method_fn(c["d_values"], **method_kwargs) if method_kwargs else method_fn(c["d_values"])
        enriched.append({**c, "raw_p_value": r["p_value"]})
    bh_input = [(c["cell_id"], c["raw_p_value"]) for c in enriched]
    bh_result = benjamini_hochberg(bh_input, q=q)
    assert bh_result and next(iter(bh_result.values()))["m_family"] == len(cells), (
        "family_size in BH non coincide con il numero di celle dichiarate - nessuna cella deve essere rimossa."
    )
    for c in enriched:
        c["bh_result"] = bh_result[c["cell_id"]]
    return {"declared_family_size": len(cells), "cells": enriched}
