#!/usr/bin/env python3
"""Phase 7.9I - Deliverable #7 (BUY/SELL x anno x regime, incrociati -
non solo separati come in Edge Decomposition), Failure Map, e
robustezza minima (sample size, concentrazione per anno, dipendenza
BUY/SELL, sensitivity agli 8 B-only e ai non-OPENED, confidence).
"""
import os
import statistics
import sys

PHASE79I_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402


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
    feat_doc = load_json(os.path.join(PHASE79I_DIR, "breakout_acc_feature_engineering_v1.json"))
    path_doc = load_json(os.path.join(PHASE79I_DIR, "breakout_acc_path_anatomy_v1.json"))
    rows = feat_doc["payload"]["rows"]
    per_event_path = {e["event_id"]: e for e in path_doc["payload"]["per_event"]}
    pop_b = [r for r in rows if r["funnel_terminal_stage"] == "OPENED"]

    # --- Deliverable #7: direzione x anno incrociati (non solo separati) ---
    cross_tab = {}
    for r in pop_b:
        key = (r["direction_label"], r["year"])
        cross_tab.setdefault(key, []).append(r)
    cross_rows = []
    for (d, y), grp in sorted(cross_tab.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        cont = sum(1 for r in grp if per_event_path.get(r["event_id"], {}).get(
            "classification_continuation_vs_failure") == "CONTINUATION")
        cross_rows.append({"direction": d, "year": y, "n": len(grp),
                           "n_continuation": cont,
                           "atr_regime_median": _stats(
                               [r["causal_atr20_d1_price_units"] for r in grp]).get("median")})

    # --- Failure Map: per ogni evento OPENED classificato FAILURE, cosa lo caratterizza? ---
    failures = [r for r in pop_b if per_event_path.get(r["event_id"], {}).get(
        "classification_continuation_vs_failure") == "FAILURE"]
    continuations = [r for r in pop_b if per_event_path.get(r["event_id"], {}).get(
        "classification_continuation_vs_failure") == "CONTINUATION"]

    def profile(grp):
        return {
            "n": len(grp),
            "pct_buy": round(100 * sum(1 for r in grp if r["direction_label"] == "BUY")
                             / len(grp), 1) if grp else None,
            "breakout_magnitude_price_units": _stats(
                [r["breakout_magnitude_price_units"] for r in grp]),
            "causal_atr20_d1": _stats([r["causal_atr20_d1_price_units"] for r in grp]),
            "by_year": {y: sum(1 for r in grp if r["year"] == y)
                       for y in sorted(set(r["year"] for r in grp))},
        }

    failure_map = {
        "n_failures": len(failures), "n_continuations": len(continuations),
        "failure_profile": profile(failures),
        "continuation_profile": profile(continuations),
        "failure_direction_split": {
            "BUY": sum(1 for r in failures if r["direction_label"] == "BUY"),
            "SELL": sum(1 for r in failures if r["direction_label"] == "SELL"),
        },
        "primary_failure_mode": (
            "SELL e' sovra-rappresentato fra i FAILURE: "
            f"{sum(1 for r in failures if r['direction_label']=='SELL')}/"
            f"{sum(1 for r in pop_b if r['direction_label']=='SELL')} di tutti i SELL "
            "finiscono in FAILURE a 60 barre D1 - il principale failure mode osservato e' "
            "'segnale SELL in un mercato con trend rialzista strutturale', non un pattern "
            "di breakout geometricamente distinguibile (magnitudine/ATR non mostrano "
            "differenze nette fra FAILURE e CONTINUATION)."
        ),
    }

    # --- Robustezza minima ---
    n_buy = sum(1 for r in pop_b if r["direction_label"] == "BUY")
    n_sell = sum(1 for r in pop_b if r["direction_label"] == "SELL")
    years = sorted(set(r["year"] for r in pop_b))
    year_counts = {y: sum(1 for r in pop_b if r["year"] == y) for y in years}
    max_year_share = max(year_counts.values()) / len(pop_b)

    robustness = {
        "sample_size": {"n_opened": len(pop_b), "n_buy": n_buy, "n_sell": n_sell,
                        "assessment": "PICCOLO - N=47 totali, SELL=11 in particolare non "
                            "consente conclusioni forti a livello di singola direzione."},
        "concentration_by_year": {"year_counts": year_counts,
                                  "max_single_year_share_pct": round(100 * max_year_share, 1),
                                  "assessment": ("CONCENTRAZIONE MODERATA" if max_year_share < 0.25
                                                else "CONCENTRAZIONE ALTA - un singolo anno "
                                                     "pesa piu' del 25% del campione")},
        "buy_sell_dependence": {
            "assessment": "FORTE - il risultato aggregato dipende quasi interamente dal "
                "sottogruppo BUY (vedi Mechanism Discovery); qualunque conclusione che non "
                "distingua BUY da SELL e' fuorviante."},
        "sensitivity_to_8_b_only": {
            "assessment": "NULLA sulle analisi primarie (Population B esclude per "
                "costruzione i B-only) - vedi breakout_acc_sensitivity_67_vs_75_v1.json."},
        "sensitivity_to_non_opened": {
            "assessment": "Il gate diagnostic (BLOCKED/BROKER_REJECT) usa path "
                "CONTROFATTUALI con N piccoli (11 e 9) - non altera Population B ma "
                "qualunque affermazione sui gate stessi resta a bassa confidence."},
        "overall_confidence_for_strong_conclusions": "BASSA-MODERATA - pattern direzionale "
            "ampio e convergente su piu' analisi, ma N complessivo piccolo, un solo regime "
            "di mercato rappresentato, nessuna correzione per test multipli nel Natural "
            "Horizon.",
    }

    return {
        "phase": "7.9I",
        "deliverable_7_buy_sell_year_regime_cross_decomposition": cross_rows,
        "deliverable_8_failure_map": failure_map,
        "robustness_minimum_checks": robustness,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79I_DIR, "breakout_acc_failure_map_and_robustness_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(payload["deliverable_8_failure_map"]["primary_failure_mode"])
    return doc


if __name__ == "__main__":
    main()
