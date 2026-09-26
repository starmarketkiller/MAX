#!/usr/bin/env python3
"""Phase 7.9K - Edge Decomposition V2 (misurazione B, bar semantics
corretta). Stesse dimensioni di Phase 7.9I/7.9J (direzione, anno,
magnitudine, ATR, HTF/trend causale, cooldown context)."""
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

POST_HOC_OBSERVATION_MIN_N = 8


def _stats(values):
    values = [v for v in values if v is not None]
    if not values:
        return {"n": 0}
    out = {"n": len(values), "mean": round(statistics.mean(values), 4),
           "median": round(statistics.median(values), 4)}
    if len(values) > 1:
        out["stdev"] = round(statistics.stdev(values), 4)
    return out


def tercile_labels(rows, key):
    vals = sorted((r[key] for r in rows if r[key] is not None))
    n = len(vals)
    if n < POST_HOC_OBSERVATION_MIN_N:
        return None
    t1 = vals[n // 3]
    t2 = vals[(2 * n) // 3]

    def label(v):
        if v is None:
            return "UNKNOWN"
        return "LOW" if v <= t1 else ("MID" if v <= t2 else "HIGH")
    return label, (t1, t2)


def outcome_summary(rows, path_key):
    mfe = _stats([r[path_key]["mfe_price_units"] for r in rows if r[path_key].get("status") in
                 ("FULL_COVERAGE", "CENSORED_INSUFFICIENT_BARS")])
    mae = _stats([r[path_key]["mae_price_units"] for r in rows if r[path_key].get("status") in
                 ("FULL_COVERAGE", "CENSORED_INSUFFICIENT_BARS")])
    return {"n": len(rows), "mfe": mfe, "mae": mae}


def decompose_by(rows, key, path_key, label_fn=None):
    groups = {}
    for r in rows:
        v = r[key] if label_fn is None else label_fn(r[key])
        groups.setdefault(v, []).append(r)
    out = {}
    for g, grp in sorted(groups.items(), key=lambda kv: str(kv[0])):
        entry = {"group": g, **outcome_summary(grp, path_key)}
        if len(grp) < POST_HOC_OBSERVATION_MIN_N:
            entry["flag"] = "POST_HOC_OBSERVATION"
        out[str(g)] = entry
    return out


def build():
    dataset = load_json(os.path.join(PHASE79K_DIR, "breakout_acc_intended_d1_v2_dataset.json"))["payload"]
    feat_rows = {r["event_id"]: r for r in ctx.build_feature_table()["rows"]}

    opened = []
    for e in dataset["events"]:
        if e["funnel_terminal_stage"] != "OPENED":
            continue
        feat = feat_rows[e["event_id"]]
        row = dict(feat)
        row["measurement_B_post_fill_path"] = e["measurement_B_post_fill_path"]
        opened.append(row)

    decomposition = {
        "1_direction_buy_sell": decompose_by(opened, "direction_label", "measurement_B_post_fill_path"),
        "2_year": decompose_by(opened, "year", "measurement_B_post_fill_path"),
        "6_htf_context_causal_proxy_trend_aligned": decompose_by(
            opened, "htf_proxy_trend_aligned", "measurement_B_post_fill_path"),
    }
    tl = tercile_labels(opened, "breakout_magnitude_price_units")
    if tl:
        fn, cuts = tl
        decomposition["3_breakout_magnitude_tercile"] = {
            "cutpoints": cuts, **decompose_by(opened, "breakout_magnitude_price_units",
                                              "measurement_B_post_fill_path", fn)}
    tl = tercile_labels(opened, "causal_atr20_d1_price_units")
    if tl:
        fn, cuts = tl
        decomposition["7_volatility_regime_atr20_tercile"] = {
            "cutpoints": cuts, **decompose_by(opened, "causal_atr20_d1_price_units",
                                              "measurement_B_post_fill_path", fn)}

    return {
        "phase": "7.9K", "measurement": "B (post-fill, 47 OPENED, bar semantics corretta)",
        "no_optimization": True, "no_pf_as_starting_point": True,
        "decomposition": decomposition,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79K_DIR, "breakout_acc_edge_decomposition_v2.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    return doc


if __name__ == "__main__":
    main()
