#!/usr/bin/env python3
"""Phase 7.18 punto 4 - parity A (EA pre-fix, contaminato) vs B (EA
post-fix) vs C (ricostruzione TF-scoped Python, Phase 7.17, storia
piena per il warm-up, poi ritagliata sulla finestra del run breve).
MT5 post-fix resta la fonte canonica - Python NON e' ground truth.
"""
import csv
import os
import sys
from datetime import datetime

PHASE718_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE713_DIR = os.path.abspath(os.path.join(PHASE718_DIR, "..", "phase7_13"))
PHASE717_DIR = os.path.abspath(os.path.join(PHASE718_DIR, "..", "phase7_17"))
ROOT = os.path.abspath(os.path.join(PHASE718_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

sys.path.insert(0, PHASE717_DIR)
from nxs_tsi_replica import TSIState, tsi_update  # noqa: E402

PRE_CSV = os.path.join(PHASE718_DIR, "nxs_tsi_realtrace_diag_prefix_curated.csv")
POST_CSV = os.path.join(PHASE718_DIR, "nxs_tsi_realtrace_diag_postfix_curated.csv")
WINDOW_START = "2026.01.01"
WINDOW_END = "2026.08.25"


def _load(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _summarize(rows, label):
    by_tf = {}
    canonical_tf = rows[0]["canonical_tf"] if rows else None
    canonical_events = []
    n_mutations_non_canonical = 0
    for r in rows:
        by_tf[r["tf"]] = by_tf.get(r["tf"], 0) + 1
        if r["tf"] != canonical_tf and r.get("mutated") == "1":
            n_mutations_non_canonical += 1
        if r["signal_dir"] in ("BUY", "SELL") and r["tf"] == canonical_tf:
            canonical_events.append({"close_time_srv": r["close_time_srv"], "signal_dir": r["signal_dir"],
                                     "tsi": r.get("tsi"), "signal_line": r.get("signal_line")})
    return {
        "label": label, "n_rows_total": len(rows), "rows_by_tf": by_tf,
        "canonical_tf": canonical_tf,
        "n_mutations_non_canonical": n_mutations_non_canonical,
        "n_signals_canonical": len(canonical_events),
        "canonical_events": canonical_events,
    }


def _build_c_tf_scoped_full_history_then_window():
    """Ricostruzione TF-scoped C: usa la STORIA PIENA locale (2023-10-02..
    2026-08-25, phase7_13) per un warm-up realistico, poi ritaglia
    l'output sulla finestra del run breve MT5 per il confronto."""
    doc = load_json(os.path.join(PHASE713_DIR, "multi_tf_dataset_v1.json"))
    d1_bars = doc["payload"]["tf_bars"]["D1"]
    seed_close = d1_bars[0]["open"]
    state = TSIState()
    series = []
    for i, b in enumerate(d1_bars):
        curbar0 = d1_bars[i + 1]["open_time"] if i + 1 < len(d1_bars) else b["close_time"]
        sig, rec = tsi_update(state, b["close"], curbar0, seed_close)
        series.append({"close_time": b["close_time"], "signal_dir": sig,
                       "tsi": rec.get("tsi"), "signal_line": rec.get("signal_line")})
    start_d = datetime.strptime(WINDOW_START, "%Y.%m.%d").date()
    end_d = datetime.strptime(WINDOW_END, "%Y.%m.%d").date()
    windowed = [e for e in series
               if start_d <= datetime.fromisoformat(e["close_time"]).date() <= end_d]
    return windowed


def build():
    pre_rows = _load(PRE_CSV)
    post_rows = _load(POST_CSV)
    A = _summarize(pre_rows, "A_EA_PRE_FIX")
    B = _summarize(post_rows, "B_EA_POST_FIX")
    c_windowed = _build_c_tf_scoped_full_history_then_window()
    C = {
        "label": "C_TF_SCOPED_RECONSTRUCTION_PHASE_7_17_FULL_HISTORY_WARMUP",
        "source": "server/research_scripts/phase7/phase7_17/nxs_tsi_replica.py, fatta girare "
                 "sull'intera storia locale 2023-10-02..2026-08-25 (phase7_13/"
                 "multi_tf_dataset_v1.json) per un warm-up realistico del filtro ricorsivo, "
                 "poi ritagliata sulla finestra del run breve MT5",
        "window": [WINDOW_START, WINDOW_END],
        "n_signals_windowed": sum(1 for e in c_windowed if e["signal_dir"] is not None),
        "signals_windowed": [e for e in c_windowed if e["signal_dir"] is not None],
    }

    guard_non_canonical_rows_in_B = sum(v for tf, v in B["rows_by_tf"].items() if tf != B["canonical_tf"])
    guard_fully_effective = (guard_non_canonical_rows_in_B == 0)

    a_events = {(e["close_time_srv"], e["signal_dir"]) for e in A["canonical_events"]}
    b_events = {(e["close_time_srv"], e["signal_dir"]) for e in B["canonical_events"]}
    a_only = sorted(a_events - b_events)
    b_only = sorted(b_events - a_events)
    matched_ab = sorted(a_events & b_events)

    def _date_only(ts):
        return ts.split(" ")[0].replace(".", "-")

    b_dates = {(_date_only(e["close_time_srv"]), e["signal_dir"]) for e in B["canonical_events"]}
    c_dates = {(e["close_time"][:10], e["signal_dir"]) for e in c_windowed if e["signal_dir"] is not None}
    matched_bc = sorted(b_dates & c_dates)
    b_only_vs_c = sorted(b_dates - c_dates)
    c_only_vs_b = sorted(c_dates - b_dates)

    # confronto valori TSI intermedi (post-fix vs C), sulle date comuni
    b_tsi_by_date = {}
    for r in post_rows:
        if r["tf"] == B["canonical_tf"] and r.get("tsi") not in (None, "", "0.000000") and r["signal_dir"] != "WARMUP":
            b_tsi_by_date[_date_only(r["close_time_srv"])] = r.get("tsi")
    c_tsi_by_date = {e["close_time"][:10]: e["tsi"] for e in c_windowed if e["tsi"] is not None}
    common_dates = sorted(set(b_tsi_by_date) & set(c_tsi_by_date))
    tsi_diffs = []
    for d in common_dates:
        try:
            diff = abs(float(b_tsi_by_date[d]) - float(c_tsi_by_date[d]))
            tsi_diffs.append(diff)
        except (TypeError, ValueError):
            continue

    payload = {
        "window": [WINDOW_START, WINDOW_END],
        "A_pre_fix": A,
        "B_post_fix": B,
        "C_tf_scoped_reconstruction": C,
        "guard_effectiveness_check": {
            "non_canonical_rows_present_in_B": guard_non_canonical_rows_in_B,
            "guard_fully_effective_zero_non_canonical_mutations": guard_fully_effective,
        },
        "a_vs_b_same_real_ticks_comparison": {
            "a_total_canonical": A["n_signals_canonical"], "b_total_canonical": B["n_signals_canonical"],
            "n_matched": len(matched_ab), "n_only_in_a": len(a_only), "n_only_in_b": len(b_only),
            "only_in_a": a_only, "only_in_b": b_only,
        },
        "b_vs_c_structural_comparison": {
            "n_matched_date_direction": len(matched_bc),
            "n_b_only_vs_c": len(b_only_vs_c), "n_c_only_vs_b": len(c_only_vs_b),
            "b_only_vs_c": b_only_vs_c, "c_only_vs_b": c_only_vs_b,
            "tsi_value_comparison_on_common_dates": {
                "n_common_dates": len(common_dates),
                "mean_abs_diff": (sum(tsi_diffs) / len(tsi_diffs)) if tsi_diffs else None,
                "max_abs_diff": max(tsi_diffs) if tsi_diffs else None,
            },
            "caveat": "MT5 post-fix (B) ha un warm-up del filtro basato sulla storia REALE "
                     "completa del broker (probabilmente anni, non solo dal 2023-10-02) - C "
                     "usa solo la storia locale disponibile (2023-10-02+). Una differenza "
                     "numerica residua nei valori TSI e' ATTESA per questo motivo, gia' "
                     "dichiarato in Phase 7.16/7.17 - Python NON e' ground truth, MT5 "
                     "post-fix resta la fonte canonica.",
        },
        "python_not_ground_truth_mt5_postfix_is_canonical": True,
        "not_a_backtest_campaign": True,
        "not_used_for_profitability": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE718_DIR, "tsi_parity_comparison_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  A canonici: {payload['A_pre_fix']['n_signals_canonical']}, "
          f"B canonici: {payload['B_post_fix']['n_signals_canonical']}")
    print(f"  righe non canoniche in B: {payload['guard_effectiveness_check']['non_canonical_rows_present_in_B']}")
    print(f"  guardia efficace al 100%: {payload['guard_effectiveness_check']['guard_fully_effective_zero_non_canonical_mutations']}")
    ab = payload["a_vs_b_same_real_ticks_comparison"]
    print(f"  A/B: {ab['n_matched']} uguali, {ab['n_only_in_a']} solo A, {ab['n_only_in_b']} solo B")


if __name__ == "__main__":
    main()
