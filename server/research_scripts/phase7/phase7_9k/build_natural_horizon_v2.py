#!/usr/bin/env python3
"""Phase 7.9K - Natural Horizon V2 (misurazione B, bar semantics
corretta). Stessa cautela epistemica di Phase 7.9J (finestre
sovrapposte, dipendenza entro-evento) - qui SOLO la correzione del
bar-offset, non una nuova validazione statistica del CI."""
import math
import os
import statistics
import sys
from datetime import datetime

PHASE79K_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

sys.path.insert(0, PHASE79K_DIR)
import nxs_forward_path_v2 as fp  # noqa: E402

MAX_H = fp.MAX_H


def _mean_ci(values):
    values = [v for v in values if v is not None]
    n = len(values)
    if n == 0:
        return {"n": 0, "mean": None, "se": None, "ci95_low": None, "ci95_high": None}
    mean = statistics.mean(values)
    if n < 2:
        return {"n": n, "mean": round(mean, 4), "se": None, "ci95_low": None, "ci95_high": None}
    se = statistics.stdev(values) / math.sqrt(n)
    return {"n": n, "mean": round(mean, 4), "se": round(se, 4),
           "ci95_low": round(mean - 1.96 * se, 4), "ci95_high": round(mean + 1.96 * se, 4)}


def build():
    dataset = load_json(os.path.join(PHASE79K_DIR, "breakout_acc_intended_d1_v2_dataset.json"))["payload"]
    events = [e for e in dataset["events"] if e["funnel_terminal_stage"] == "OPENED"]
    d1_bars = fp.load_d1_bars()

    curves = []
    for e in events:
        ref_time, ref_price = fp.measurement_b_reference(e)
        fc = fp.build_forward_curve_v2(d1_bars, ref_time, ref_price, e["direction"])
        if fc["status"] == "NO_BARS_AVAILABLE":
            continue
        curves.append(fc["curve"])

    per_bar = []
    for t in range(1, MAX_H + 1):
        rets = [next((p["close_to_close_return"] for p in c if p["bar"] == t), None) for c in curves]
        per_bar.append({"bar_d1": t, "close_to_close_return": _mean_ci(rets),
                        "n_with_data_at_this_bar": sum(1 for r in rets if r is not None)})

    means = [p["close_to_close_return"]["mean"] for p in per_bar
            if p["close_to_close_return"]["mean"] is not None]

    return {
        "phase": "7.9K", "measurement": "B (post-fill, 47 OPENED)",
        "bar_semantics": "CORRETTA (bar 1 = prima barra D1 completa, vedi "
            "nxs_forward_path_v2.py) - non piu' l'offset di +1 confermato in Phase 7.9J.",
        "epistemic_caveats_still_apply": (
            "Le cautele di Phase 7.9J (finestre forward sovrapposte fra eventi, "
            "dipendenza seriale entro-evento, CI95% non inferenzialmente valido) "
            "restano IDENTICHE - la correzione qui e' SOLO dell'offset di indicizzazione, "
            "non introduce indipendenza statistica che non esisteva. Vedi "
            "breakout_acc_natural_horizon_reconciliation_v1.json (Phase 7.9J) per "
            "l'analisi completa, ancora valida in V2."
        ),
        "n_of_47_used": len(curves),
        "per_bar_curve": per_bar,
        "shape_description": (
            f"Il ritorno medio close-to-close (misurazione B, semantica corretta) va da "
            f"~{round(means[0],1) if means else None} (bar 1, ora il giorno subito dopo "
            f"il fill) a ~{round(means[-1],1) if means else None} (bar {len(means)})."
        ),
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79K_DIR, "breakout_acc_natural_horizon_v2.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(payload["shape_description"])
    return doc


if __name__ == "__main__":
    main()
