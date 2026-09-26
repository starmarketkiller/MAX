#!/usr/bin/env python3
"""Phase 7.9K - Path Anatomy V2 (misurazione B, post-fill, 47 OPENED) +
confronto per-evento e aggregato prima/dopo (punto 4 della task)."""
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
    opened = [e for e in events if e["funnel_terminal_stage"] == "OPENED"]

    per_event = []
    n_reclassified = 0
    for e in opened:
        v2 = e["measurement_B_post_fill_path"]
        v1 = e["post_entry_path_anatomy_V1_SUPERSEDED"]

        v2_fwd60 = v2["horizons"].get("fwd_return_60d1_price_units")
        v1_fwd60 = v1["horizons"].get("fwd_return_60d1_price_units") if v1 else None

        v2_cls = fp.classify_continuation_failure_v2(v2, 60)
        v1_cls = ("CONTINUATION" if v1_fwd60 and v1_fwd60 > 0 else
                 "FAILURE" if v1_fwd60 is not None else "UNKNOWN")
        reclassified = v2_cls != v1_cls
        if reclassified:
            n_reclassified += 1

        per_event.append({
            "event_id": e["event_id"], "direction_label": (
                "BUY" if e["direction"] == 1 else "SELL"),
            "d1_bar_date": e["d1_bar_date"],
            "v1_mfe": v1["mfe_price_units"] if v1 else None,
            "v2_mfe": v2.get("mfe_price_units"),
            "v1_mae": v1["mae_price_units"] if v1 else None,
            "v2_mae": v2.get("mae_price_units"),
            "v1_bars_to_mfe": v1["bars_to_mfe_d1"] if v1 else None,
            "v2_bars_to_mfe": v2.get("bars_to_mfe_d1"),
            "v1_bars_to_mae": v1["bars_to_mae_d1"] if v1 else None,
            "v2_bars_to_mae": v2.get("bars_to_mae_d1"),
            "v1_fwd_return_60d1": v1_fwd60,
            "v2_fwd_return_60d1": v2_fwd60,
            "v1_classification": v1_cls, "v2_classification": v2_cls,
            "reclassified": reclassified,
            "v2_status": v2.get("status"), "v2_coverage_bars": v2.get("coverage_bars"),
        })

    n_censored_60 = sum(1 for p in per_event if p["v2_status"] == "CENSORED_INSUFFICIENT_BARS")

    def agg(rows, key_v1, key_v2):
        return {"v1": _stats([r[key_v1] for r in rows]), "v2": _stats([r[key_v2] for r in rows])}

    aggregate_before_after = {
        "n_events": len(per_event),
        "n_censored_at_60_bars": n_censored_60,
        "n_reclassified_continuation_failure": n_reclassified,
        "mfe": agg(per_event, "v1_mfe", "v2_mfe"),
        "mae": agg(per_event, "v1_mae", "v2_mae"),
        "bars_to_mfe": agg(per_event, "v1_bars_to_mfe", "v2_bars_to_mfe"),
        "bars_to_mae": agg(per_event, "v1_bars_to_mae", "v2_bars_to_mae"),
        "fwd_return_60d1": agg(per_event, "v1_fwd_return_60d1", "v2_fwd_return_60d1"),
    }

    by_direction = {}
    for d in ("BUY", "SELL"):
        grp = [p for p in per_event if p["direction_label"] == d]
        n_cont_v1 = sum(1 for p in grp if p["v1_classification"] == "CONTINUATION")
        n_cont_v2 = sum(1 for p in grp if p["v2_classification"] == "CONTINUATION")
        n_censored = sum(1 for p in grp if p["v2_classification"] == "UNKNOWN_CENSORED")
        by_direction[d] = {
            "n": len(grp), "n_continuation_v1": n_cont_v1, "n_continuation_v2": n_cont_v2,
            "n_censored_v2": n_censored,
            "pct_continuation_v1": round(100 * n_cont_v1 / len(grp), 1) if grp else None,
            "pct_continuation_v2": round(100 * n_cont_v2 / (len(grp) - n_censored), 1)
                if (len(grp) - n_censored) > 0 else None,
            "denominator_v2_excludes_censored": len(grp) - n_censored,
        }

    return {
        "phase": "7.9K", "measurement": "B (post-fill, 47 OPENED, fill reale verificato)",
        "dataset_v2_sha256_reference": "vedi breakout_acc_intended_d1_v2_dataset.json",
        "per_event_before_after": per_event,
        "aggregate_before_after": aggregate_before_after,
        "by_direction_continuation_before_after": by_direction,
        "censoring_note": (
            f"{n_censored_60} evento/i con copertura <60 barre al momento del calcolo "
            "(vicino alla fine dello storico disponibile) - classificato UNKNOWN_CENSORED, "
            "MAI FAILURE. Denominatori per le percentuali di continuation ESCLUDONO "
            "esplicitamente i censurati."
        ),
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79K_DIR, "breakout_acc_path_anatomy_v2.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"n_reclassified: {payload['aggregate_before_after']['n_reclassified_continuation_failure']}")
    print(f"n_censored: {payload['aggregate_before_after']['n_censored_at_60_bars']}")
    return doc


if __name__ == "__main__":
    main()
