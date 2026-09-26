#!/usr/bin/env python3
"""Phase 7.9K - Gate Diagnostic V2. Migliora la V1/7.9I: usa il
timestamp REALE del segnale (misurazione A) per BLOCKED/BROKER_REJECT
(tutti fra i 67 live-observed, quindi tutti hanno un timestamp reale
dal trace - non serve piu' un placeholder a mezzogiorno). Bar semantics
corretta. Ancora diagnostico, non proposta di modifica del gate."""
import os
import statistics
import sys

PHASE79K_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

sys.path.insert(0, PHASE79K_DIR)
import nxs_forward_path_v2 as fp  # noqa: E402


def _stats(values):
    values = [v for v in values if v is not None]
    if not values:
        return {"n": 0}
    out = {"n": len(values), "mean": round(statistics.mean(values), 4),
           "median": round(statistics.median(values), 4)}
    if len(values) > 1:
        out["stdev"] = round(statistics.stdev(values), 4)
    return out


def build():
    dataset = load_json(os.path.join(PHASE79K_DIR, "breakout_acc_intended_d1_v2_dataset.json"))["payload"]
    events = dataset["events"]

    groups = {"OPENED": [], "BLOCKED": [], "BROKER_REJECT": []}
    for e in events:
        stage = e["funnel_terminal_stage"]
        if stage not in groups:
            continue
        if stage == "OPENED":
            path = e["measurement_B_post_fill_path"]
            method = "REALE (fill verificato)"
        else:
            path = e["measurement_A_post_signal_path"]
            method = ("Timestamp REALE del segnale (trace live) + prezzo c1 - MAI un fill "
                     "reale, il segnale non e' mai stato eseguito")
        if path.get("status") not in ("FULL_COVERAGE", "CENSORED_INSUFFICIENT_BARS"):
            continue
        fwd60 = path["horizons"].get("fwd_return_60d1_price_units")
        cls = fp.classify_continuation_failure_v2(path, 60)
        groups[stage].append({"event_id": e["event_id"], "mfe": path["mfe_price_units"],
                              "mae": path["mae_price_units"], "fwd_return_60d1": fwd60,
                              "classification": cls, "method": method})

    summary = {}
    for stage, evs in groups.items():
        n_cont = sum(1 for e in evs if e["classification"] == "CONTINUATION")
        n_censored = sum(1 for e in evs if e["classification"] == "UNKNOWN_CENSORED")
        denom = len(evs) - n_censored
        summary[stage] = {
            "n": len(evs), "n_censored": n_censored, "denominator_excl_censored": denom,
            "path_method": evs[0]["method"] if evs else None,
            "mfe": _stats([e["mfe"] for e in evs]),
            "mae": _stats([e["mae"] for e in evs]),
            "fwd_return_60d1": _stats([e["fwd_return_60d1"] for e in evs]),
            "n_continuation": n_cont,
            "pct_continuation": round(100 * n_cont / denom, 1) if denom else None,
        }

    return {
        "phase": "7.9K",
        "improvement_over_v1": "BLOCKED/BROKER_REJECT ora usano il timestamp REALE del "
            "segnale (dal trace live, disponibile per tutti i 67) invece di un "
            "placeholder sintetico a mezzogiorno (Phase 7.9I/7.9J) - stesso prezzo "
            "proxy (c1), timestamp piu' preciso.",
        "counterfactual_disclaimer": "BLOCKED/BROKER_REJECT: MAI trade reali - nessuna "
            "decisione di modifica del gate deve basarsi su questi numeri da soli.",
        "by_stage": summary,
        "sample_size_caveat": (
            f"BLOCKED n={summary['BLOCKED']['n']}, BROKER_REJECT n={summary['BROKER_REJECT']['n']} "
            "- entrambi piccoli, non decidibile se il gate filtra causalmente, "
            "casualmente, o elimina eventi migliori."
        ),
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79K_DIR, "breakout_acc_gate_diagnostic_v2.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    for k, v in payload["by_stage"].items():
        print(k, v["n"], v.get("pct_continuation"), v["fwd_return_60d1"].get("median"))
    return doc


if __name__ == "__main__":
    main()
