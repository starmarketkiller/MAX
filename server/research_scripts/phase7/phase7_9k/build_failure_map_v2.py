#!/usr/bin/env python3
"""Phase 7.9K - Failure Map V2 + robustezza minima, misurazione B (47
OPENED), bar semantics corretta, censura esplicita."""
import os
import statistics
import sys

PHASE79K_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79I_DIR = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "phase7_9i"))
ROOT = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

sys.path.insert(0, PHASE79K_DIR)
sys.path.insert(0, PHASE79I_DIR)
import nxs_forward_path_v2 as fp  # noqa: E402
import nxs_mechanism_context as ctx  # noqa: E402


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
    feat_rows = {r["event_id"]: r for r in ctx.build_feature_table()["rows"]}

    opened = []
    for e in dataset["events"]:
        if e["funnel_terminal_stage"] != "OPENED":
            continue
        feat = dict(feat_rows[e["event_id"]])
        feat["measurement_B_post_fill_path"] = e["measurement_B_post_fill_path"]
        feat["classification"] = fp.classify_continuation_failure_v2(
            e["measurement_B_post_fill_path"], 60)
        opened.append(feat)

    non_censored = [r for r in opened if r["classification"] != "UNKNOWN_CENSORED"]
    failures = [r for r in non_censored if r["classification"] == "FAILURE"]
    continuations = [r for r in non_censored if r["classification"] == "CONTINUATION"]

    cross_tab = {}
    for r in opened:
        key = (r["direction_label"], r["year"])
        cross_tab.setdefault(key, []).append(r)
    cross_rows = []
    for (d, y), grp in sorted(cross_tab.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        n_cont = sum(1 for r in grp if r["classification"] == "CONTINUATION")
        n_cens = sum(1 for r in grp if r["classification"] == "UNKNOWN_CENSORED")
        cross_rows.append({"direction": d, "year": y, "n": len(grp), "n_continuation": n_cont,
                           "n_censored": n_cens})

    def profile(grp):
        return {"n": len(grp),
               "pct_buy": round(100 * sum(1 for r in grp if r["direction_label"] == "BUY")
                                / len(grp), 1) if grp else None,
               "breakout_magnitude_price_units": _stats(
                   [r["breakout_magnitude_price_units"] for r in grp])}

    n_sell_total = sum(1 for r in non_censored if r["direction_label"] == "SELL")
    n_sell_failure = sum(1 for r in failures if r["direction_label"] == "SELL")

    failure_map = {
        "n_failures": len(failures), "n_continuations": len(continuations),
        "n_censored_excluded": len(opened) - len(non_censored),
        "failure_profile": profile(failures), "continuation_profile": profile(continuations),
        "primary_failure_mode": (
            f"SELL sovra-rappresentato fra i FAILURE: {n_sell_failure}/{n_sell_total} di "
            "tutti i SELL (denominatore ESCLUDE i censurati) finiscono in FAILURE a 60 "
            "barre D1 (bar semantics corretta) - invariato qualitativamente rispetto a "
            "V1/7.9I/7.9J."
        ),
    }

    n_buy = sum(1 for r in opened if r["direction_label"] == "BUY")
    n_sell = sum(1 for r in opened if r["direction_label"] == "SELL")
    years = sorted(set(r["year"] for r in opened))
    year_counts = {y: sum(1 for r in opened if r["year"] == y) for y in years}
    max_year_share = max(year_counts.values()) / len(opened)

    robustness = {
        "sample_size": {"n_opened": len(opened), "n_buy": n_buy, "n_sell": n_sell,
                        "n_censored_at_60": len(opened) - len(non_censored)},
        "concentration_by_year": {"year_counts": year_counts,
                                  "max_single_year_share_pct": round(100 * max_year_share, 1)},
        "buy_sell_dependence": "FORTE - invariata dopo la correzione (vedi confronto "
            "prima/dopo in breakout_acc_path_anatomy_v2.json).",
        "overall_confidence": "BASSA - stesse ragioni di Phase 7.9J (N piccolo, un solo "
            "regime, confondimento trend/direzione) + ora esplicitamente 1 evento "
            "censurato a 60 barre.",
    }

    return {
        "phase": "7.9K",
        "buy_sell_year_cross_v2": cross_rows,
        "failure_map_v2": failure_map,
        "robustness_v2": robustness,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79K_DIR, "breakout_acc_failure_map_v2.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(payload["failure_map_v2"]["primary_failure_mode"])
    return doc


if __name__ == "__main__":
    main()
