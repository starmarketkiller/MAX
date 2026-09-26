#!/usr/bin/env python3
"""Phase 7.9I - Path Anatomy. Studia la FORMA del percorso post-segnale
(Population B, 47 OPENED) - non un TP ottimale. MFE-prima-di-MAE vs
MAE-prima-di-MFE, tempo a MFE/MAE, reversal dopo movimento favorevole,
continuation vs failure, differenze BUY/SELL.
"""
import os
import statistics
import sys
from datetime import datetime

PHASE79I_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

sys.path.insert(0, PHASE79I_DIR)
import nxs_mechanism_context as ctx  # noqa: E402


def _stats(values):
    values = [v for v in values if v is not None]
    if not values:
        return {"n": 0}
    out = {"n": len(values), "mean": round(statistics.mean(values), 4),
           "median": round(statistics.median(values), 4)}
    if len(values) > 1:
        out["stdev"] = round(statistics.stdev(values), 4)
    out["min"] = round(min(values), 4)
    out["max"] = round(max(values), 4)
    return out


def build():
    feat_doc = load_json(os.path.join(PHASE79I_DIR, "breakout_acc_feature_engineering_v1.json"))
    rows = feat_doc["payload"]["rows"]
    d1_bars = ctx.load_d1_bars()
    pop_b = [r for r in rows if r["funnel_terminal_stage"] == "OPENED"]

    per_event = []
    for r in pop_b:
        path = r["post_entry_path_anatomy"]
        entry_dt = datetime.strptime(r["entry_fill_time"], "%Y.%m.%d %H:%M:%S")
        curve = ctx.full_path_curve(d1_bars, entry_dt, r["entry_fill_price"], r["direction"])
        bars_to_mfe = path.get("bars_to_mfe_d1")
        bars_to_mae = path.get("bars_to_mae_d1")
        mfe_first = (bars_to_mfe is not None and bars_to_mae is not None
                    and bars_to_mfe < bars_to_mae)
        fwd60 = path["horizons"].get("fwd_return_60d1_price_units")
        mfe = path.get("mfe_price_units")
        giveback = (mfe - fwd60) if (mfe is not None and fwd60 is not None) else None
        continuation = fwd60 is not None and fwd60 > 0

        per_event.append({
            "event_id": r["event_id"], "direction_label": r["direction_label"],
            "d1_bar_date": r["d1_bar_date"],
            "bars_to_mfe_d1": bars_to_mfe, "bars_to_mae_d1": bars_to_mae,
            "mfe_reached_before_mae": mfe_first,
            "mfe_price_units": mfe, "mae_price_units": path.get("mae_price_units"),
            "fwd_return_60d1_price_units": fwd60,
            "giveback_mfe_minus_fwd60_price_units": giveback,
            "classification_continuation_vs_failure": (
                "CONTINUATION" if continuation else "FAILURE" if fwd60 is not None else "UNKNOWN"),
            "path_curve_available": curve is not None,
        })

    n_total = len(per_event)
    n_mfe_first = sum(1 for e in per_event if e["mfe_reached_before_mae"])
    n_mae_first = sum(1 for e in per_event if e["mfe_reached_before_mae"] is False)

    by_dir = {}
    for d in ("BUY", "SELL"):
        grp = [e for e in per_event if e["direction_label"] == d]
        by_dir[d] = {
            "n": len(grp),
            "pct_mfe_before_mae": round(100 * sum(1 for e in grp if e["mfe_reached_before_mae"])
                                        / len(grp), 1) if grp else None,
            "bars_to_mfe": _stats([e["bars_to_mfe_d1"] for e in grp]),
            "bars_to_mae": _stats([e["bars_to_mae_d1"] for e in grp]),
            "mfe": _stats([e["mfe_price_units"] for e in grp]),
            "mae": _stats([e["mae_price_units"] for e in grp]),
            "giveback": _stats([e["giveback_mfe_minus_fwd60_price_units"] for e in grp]),
            "n_continuation": sum(1 for e in grp
                                  if e["classification_continuation_vs_failure"] == "CONTINUATION"),
            "n_failure": sum(1 for e in grp
                             if e["classification_continuation_vs_failure"] == "FAILURE"),
        }

    aggregate = {
        "n_events": n_total,
        "mfe_reached_before_mae": {"n": n_mfe_first, "pct": round(100 * n_mfe_first / n_total, 1)},
        "mae_reached_before_mfe": {"n": n_mae_first, "pct": round(100 * n_mae_first / n_total, 1)},
        "bars_to_mfe_distribution": _stats([e["bars_to_mfe_d1"] for e in per_event]),
        "bars_to_mae_distribution": _stats([e["bars_to_mae_d1"] for e in per_event]),
        "mfe_distribution": _stats([e["mfe_price_units"] for e in per_event]),
        "mae_distribution": _stats([e["mae_price_units"] for e in per_event]),
        "giveback_distribution": _stats([e["giveback_mfe_minus_fwd60_price_units"] for e in per_event]),
        "reversal_after_favorable_move": {
            "description": "giveback = MFE - forward_return_60d1 (in unita' di prezzo). "
                "Un giveback positivo grande indica che il movimento favorevole massimo "
                "viene parzialmente o totalmente ridato entro 60 barre D1 (reversal).",
            "giveback_gt_50pct_of_mfe_count": sum(
                1 for e in per_event
                if e["giveback_mfe_minus_fwd60_price_units"] is not None
                and e["mfe_price_units"] and e["mfe_price_units"] > 0
                and e["giveback_mfe_minus_fwd60_price_units"] / e["mfe_price_units"] > 0.5),
        },
        "continuation_vs_failure_at_60d1": {
            "CONTINUATION": sum(1 for e in per_event
                                if e["classification_continuation_vs_failure"] == "CONTINUATION"),
            "FAILURE": sum(1 for e in per_event
                          if e["classification_continuation_vs_failure"] == "FAILURE"),
            "UNKNOWN": sum(1 for e in per_event
                          if e["classification_continuation_vs_failure"] == "UNKNOWN"),
        },
        "by_direction": by_dir,
    }

    return {
        "phase": "7.9I", "input_frozen_dataset": "breakout_acc_intended_d1_v1_dataset.json "
            f"(sha256={feat_doc['payload']['source_canonical_dataset_sha256']})",
        "population_used": "B_opened (47 eventi con fill reale e path anatomy - unica "
            "popolazione con dati di percorso disponibili)",
        "no_optimization_no_tp_search": True,
        "method": "MFE/MAE e forward return a 60 barre D1 gia' calcolati nel dataset "
            "canonico (7.9H, orizzonti preregistrati). 'MFE prima di MAE' = "
            "bars_to_mfe_d1 < bars_to_mae_d1 sulla finestra di 60 barre. Giveback = "
            "MFE - forward_return_60d1 (quanto del massimo movimento favorevole viene "
            "perso entro la fine della finestra). Continuation/Failure classificato SOLO "
            "sul segno del forward return a 60 barre (l'orizzonte piu' lungo preregistrato), "
            "non su una soglia scelta guardando i risultati.",
        "aggregate": aggregate,
        "per_event": per_event,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79I_DIR, "breakout_acc_path_anatomy_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"mfe_before_mae: {payload['aggregate']['mfe_reached_before_mae']}")
    print(f"continuation_vs_failure: {payload['aggregate']['continuation_vs_failure_at_60d1']}")
    return doc


if __name__ == "__main__":
    main()
