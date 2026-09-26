#!/usr/bin/env python3
"""Phase 7.9I - Sensitivity: Population A (67 live-observed) vs tutti i
75 eventi (67 + 8 B-only). Gli 8 B-only NON devono alterare il
risultato primario senza essere esplicitamente identificati - qui si
misura ESATTAMENTE quanto lo alterano.
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
    rows = feat_doc["payload"]["rows"]

    pop_67 = [r for r in rows if r["population_source"] == "LIVE_TRACE_GENERATED"]
    pop_75 = rows
    b_only = [r for r in rows if r["population_source"] == "OFFLINE_ISOLATED_RECONSTRUCTION_ONLY"]

    def structural_profile(pop, label):
        n_buy = sum(1 for r in pop if r["direction_label"] == "BUY")
        n_sell = sum(1 for r in pop if r["direction_label"] == "SELL")
        mags = [r["breakout_magnitude_price_units"] for r in pop]
        by_year = {}
        for r in pop:
            by_year[r["year"]] = by_year.get(r["year"], 0) + 1
        return {
            "label": label, "n": len(pop), "n_buy": n_buy, "n_sell": n_sell,
            "pct_buy": round(100 * n_buy / len(pop), 1) if pop else None,
            "breakout_magnitude_price_units": _stats(mags),
            "by_year": dict(sorted(by_year.items())),
        }

    profile_67 = structural_profile(pop_67, "Population A (67, live-observed)")
    profile_75 = structural_profile(pop_75, "Tutti i 75 eventi (67 + 8 B-only)")
    profile_b_only = structural_profile(b_only, "Gli 8 B-only da soli")

    delta = {
        "n_buy_delta": profile_75["n_buy"] - profile_67["n_buy"],
        "n_sell_delta": profile_75["n_sell"] - profile_67["n_sell"],
        "pct_buy_delta_points": round(profile_75["pct_buy"] - profile_67["pct_buy"], 2),
        "breakout_magnitude_median_delta": round(
            (profile_75["breakout_magnitude_price_units"].get("median") or 0)
            - (profile_67["breakout_magnitude_price_units"].get("median") or 0), 4),
    }

    # Nota IMPORTANTE: i B-only non hanno fill/path anatomy reale (mai eseguiti), quindi
    # NON possono influenzare Edge Decomposition/Path Anatomy/Natural Horizon, che usano
    # esclusivamente Population B (47 OPENED, tutti in Population A). L'unico impatto
    # possibile degli 8 B-only e' STRUTTURALE (conteggi, distribuzione direzione/anno/
    # magnitudine) se qualcuno li includesse per errore in un'analisi futura.
    b_only_directions = [r["direction_label"] for r in b_only]
    b_only_years = sorted(r["year"] for r in b_only)

    return {
        "phase": "7.9I",
        "purpose": "Quantificare quanto gli 8 eventi B-only (Population C) alterebbero le "
            "statistiche strutturali SE fossero (erroneamente) inclusi insieme ai 67 "
            "live-observed (Population A) - per costruzione NON influenzano nessuna delle "
            "conclusioni di Edge Decomposition/Path Anatomy/Natural Horizon/Mechanism "
            "Discovery, che usano tutte esclusivamente Population B (47 OPENED, sottoinsieme "
            "di Population A).",
        "population_A_67_live_observed": profile_67,
        "population_all_75": profile_75,
        "population_C_8_b_only_alone": profile_b_only,
        "delta_75_minus_67": delta,
        "b_only_directions": b_only_directions,
        "b_only_years": b_only_years,
        "conclusion": (
            "Gli 8 B-only non hanno alcun impatto sulle analisi primarie (Edge "
            "Decomposition/Path Anatomy/Natural Horizon/Mechanism Discovery), che usano "
            "esclusivamente i 47 eventi OPENED con fill reale - un sottoinsieme di "
            "Population A, disgiunto da Population C per costruzione. L'unico impatto "
            "misurabile e' strutturale/descrittivo (conteggi per direzione/anno/"
            "magnitudine), quantificato sopra: "
            f"{'notevole' if abs(delta['pct_buy_delta_points']) > 5 else 'marginale'} "
            f"(variazione %BUY: {delta['pct_buy_delta_points']} punti percentuali)."
        ),
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79I_DIR, "breakout_acc_sensitivity_67_vs_75_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(payload["conclusion"])
    return doc


if __name__ == "__main__":
    main()
