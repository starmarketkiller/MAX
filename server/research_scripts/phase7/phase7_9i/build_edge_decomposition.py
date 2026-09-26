#!/usr/bin/env python3
"""Phase 7.9I - Edge Decomposition. Decompone il comportamento (MFE/MAE/
forward returns su Population B=47 OPENED) per dimensioni descrittive -
MAI a partire da PF, MAI soglie scelte guardando il risultato. Variabili
continue o quantili naturali (terzili sulla distribuzione osservata).
Nessuna optimization: nessuna ricerca di soglia, nessun grid search.
"""
import os
import statistics
import sys

PHASE79I_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

sys.path.insert(0, PHASE79I_DIR)
import nxs_mechanism_context as ctx  # noqa: E402

HORIZONS = ctx.PREREGISTERED_HORIZONS_D1
POST_HOC_OBSERVATION_MIN_N = 8  # sotto questa soglia, qualunque sottogruppo "forte" e'
                                 # etichettato POST_HOC_OBSERVATION per costruzione, mai
                                 # promosso a conclusione


def _fwd(row, h):
    if row["post_entry_path_anatomy"] is None:
        return None
    return row["post_entry_path_anatomy"]["horizons"].get(f"fwd_return_{h}d1_price_units")


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


def outcome_summary(rows):
    """Statistiche descrittive (MAI PF) per un gruppo di eventi Population B
    (OPENED, con path anatomy)."""
    mfe = _stats([r["post_entry_path_anatomy"]["mfe_price_units"] for r in rows
                 if r["post_entry_path_anatomy"]])
    mae = _stats([r["post_entry_path_anatomy"]["mae_price_units"] for r in rows
                 if r["post_entry_path_anatomy"]])
    fwd = {f"fwd_return_{h}d1": _stats([_fwd(r, h) for r in rows]) for h in HORIZONS}
    n_win_by_pnl = sum(1 for r in rows if (r.get("realized_pnl") or 0) > 0)
    return {
        "n": len(rows), "mfe": mfe, "mae": mae, "forward_returns": fwd,
        "descriptive_only_pnl_positive_count": n_win_by_pnl,  # solo descrittivo, MAI PF
    }


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
        if v <= t1:
            return "LOW"
        if v <= t2:
            return "MID"
        return "HIGH"
    return label, (t1, t2)


def decompose_by(rows, key, label_fn=None):
    groups = {}
    for r in rows:
        v = r[key] if label_fn is None else label_fn(r[key])
        groups.setdefault(v, []).append(r)
    out = {}
    for g, grp in sorted(groups.items(), key=lambda kv: str(kv[0])):
        entry = {"group": g, **outcome_summary(grp)}
        if len(grp) < POST_HOC_OBSERVATION_MIN_N:
            entry["flag"] = "POST_HOC_OBSERVATION - n troppo piccolo per una conclusione, " \
                            "riportato solo a scopo descrittivo/esplorativo"
        out[str(g)] = entry
    return out


def build():
    feat_doc = load_json(os.path.join(PHASE79I_DIR, "breakout_acc_feature_engineering_v1.json"))
    rows = feat_doc["payload"]["rows"]
    populations = ctx.split_populations(rows)
    pop_b = populations["B_opened"]  # 47 OPENED - unici con path anatomy reale

    decomposition = {
        "1_direction_buy_sell": decompose_by(pop_b, "direction_label"),
        "2_year": decompose_by(pop_b, "year"),
        "3_trigger_geometry_breakout_magnitude_price_units_tercile": None,
        "4_breakout_magnitude_atr_units_tercile": None,
        "5_distance_from_range_pct_tercile": None,
        "6_htf_context_causal_proxy_trend_aligned": decompose_by(
            pop_b, "htf_proxy_trend_aligned"),
        "7_volatility_regime_atr20_tercile": None,
        "8_cooldown_context_days_since_previous_raw_accept_tercile": None,
        "9_terminal_stage_all_75_structural_only": None,  # su tutti i 75, solo conteggi/geometria
    }

    tl = tercile_labels(pop_b, "breakout_magnitude_price_units")
    if tl:
        fn, cuts = tl
        decomposition["3_trigger_geometry_breakout_magnitude_price_units_tercile"] = {
            "tercile_cutpoints_price_units": cuts, **decompose_by(pop_b,
                "breakout_magnitude_price_units", fn)}

    tl = tercile_labels(pop_b, "breakout_magnitude_in_atr_units")
    if tl:
        fn, cuts = tl
        decomposition["4_breakout_magnitude_atr_units_tercile"] = {
            "tercile_cutpoints_atr_units": cuts, **decompose_by(pop_b,
                "breakout_magnitude_in_atr_units", fn)}

    tl = tercile_labels(pop_b, "breakout_magnitude_pct_of_range")
    if tl:
        fn, cuts = tl
        decomposition["5_distance_from_range_pct_tercile"] = {
            "tercile_cutpoints_pct": cuts, **decompose_by(pop_b,
                "breakout_magnitude_pct_of_range", fn)}

    tl = tercile_labels(pop_b, "causal_atr20_d1_price_units")
    if tl:
        fn, cuts = tl
        decomposition["7_volatility_regime_atr20_tercile"] = {
            "tercile_cutpoints_price_units": cuts, **decompose_by(pop_b,
                "causal_atr20_d1_price_units", fn)}

    tl = tercile_labels(pop_b, "days_since_previous_raw_accept_same_direction")
    if tl:
        fn, cuts = tl
        decomposition["8_cooldown_context_days_since_previous_raw_accept_tercile"] = {
            "tercile_cutpoints_days": cuts, **decompose_by(pop_b,
                "days_since_previous_raw_accept_same_direction", fn)}

    # 9 - struttura per stage terminale su TUTTI i 75 (solo conteggi + geometria di
    # breakout, MAI path anatomy che non esiste per non-OPENED)
    all_rows = rows
    by_stage = {}
    for stage in ("OPENED", "BLOCKED", "BROKER_REJECT", "NEVER_OBSERVED_IN_LIVE_TRACE"):
        grp = [r for r in all_rows if r["funnel_terminal_stage"] == stage]
        mags = [r["breakout_magnitude_price_units"] for r in grp
               if r["breakout_magnitude_price_units"] is not None]
        by_stage[stage] = {"n": len(grp), "breakout_magnitude_price_units": _stats(mags)}
    decomposition["9_terminal_stage_all_75_structural_only"] = by_stage

    post_hoc_flags = [k for k, v in decomposition.items() if isinstance(v, dict)
                      for gk, gv in v.items() if isinstance(gv, dict) and gv.get("flag")]

    return {
        "phase": "7.9I", "input_frozen_dataset": "breakout_acc_intended_d1_v1_dataset.json "
            f"(sha256={feat_doc['payload']['source_canonical_dataset_sha256']})",
        "no_optimization": True, "no_pf_as_starting_point": True,
        "method": "Statistiche descrittive (media/mediana/stdev/min/max) di MFE/MAE/forward "
            "return per sottogruppo. Terzili calcolati sulla distribuzione OSSERVATA "
            "(nessuna soglia scelta guardando l'esito). Population B (47 OPENED, uniche con "
            "path anatomy reale) usata per tutte le decomposizioni basate su MFE/MAE/forward "
            "return; Population completa (75) usata solo per la decomposizione strutturale "
            "per terminal_stage (punto 9), dove path anatomy non esiste per costruzione.",
        "post_hoc_observation_min_n": POST_HOC_OBSERVATION_MIN_N,
        "decomposition": decomposition,
        "post_hoc_observation_flags_present": len(post_hoc_flags) > 0,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79I_DIR, "breakout_acc_edge_decomposition_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    return doc


if __name__ == "__main__":
    main()
