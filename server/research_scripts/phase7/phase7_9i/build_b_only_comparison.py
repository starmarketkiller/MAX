#!/usr/bin/env python3
"""Phase 7.9I - Capitolo dedicato: gli 8 eventi B-only (Population C)
confrontati contro i 67 live-observed (Population A) su feature
causalmente disponibili. Verifica se sono distribuzionalmente simili,
concentrati in anni/regimi particolari, associati a stati particolari,
o sistematicamente diversi. Mai usati per migliorare artificialmente
il risultato primario (che li esclude per costruzione).
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
    rows = feat_doc["payload"]["rows"]

    a67 = [r for r in rows if r["population_source"] == "LIVE_TRACE_GENERATED"]
    c8 = [r for r in rows if r["population_source"] == "OFFLINE_ISOLATED_RECONSTRUCTION_ONLY"]

    def year_hist(pop):
        h = {}
        for r in pop:
            h[r["year"]] = h.get(r["year"], 0) + 1
        return dict(sorted(h.items()))

    comparison = {
        "n": {"A_67": len(a67), "C_8": len(c8)},
        "direction_split": {
            "A_67": {"BUY": sum(1 for r in a67 if r["direction_label"] == "BUY"),
                    "SELL": sum(1 for r in a67 if r["direction_label"] == "SELL")},
            "C_8": {"BUY": sum(1 for r in c8 if r["direction_label"] == "BUY"),
                   "SELL": sum(1 for r in c8 if r["direction_label"] == "SELL")},
        },
        "year_histogram": {"A_67": year_hist(a67), "C_8": year_hist(c8)},
        "breakout_magnitude_price_units": {
            "A_67": _stats([r["breakout_magnitude_price_units"] for r in a67]),
            "C_8": _stats([r["breakout_magnitude_price_units"] for r in c8]),
        },
        "breakout_magnitude_atr_units": {
            "A_67": _stats([r["breakout_magnitude_in_atr_units"] for r in a67]),
            "C_8": _stats([r["breakout_magnitude_in_atr_units"] for r in c8]),
        },
        "causal_atr20_d1": {
            "A_67": _stats([r["causal_atr20_d1_price_units"] for r in a67]),
            "C_8": _stats([r["causal_atr20_d1_price_units"] for r in c8]),
        },
        "htf_proxy_trend_aligned": {
            "A_67": sum(1 for r in a67 if r["htf_proxy_trend_aligned"]),
            "A_67_total_with_data": sum(1 for r in a67 if r["htf_proxy_trend_aligned"] is not None),
            "C_8": sum(1 for r in c8 if r["htf_proxy_trend_aligned"]),
            "C_8_total_with_data": sum(1 for r in c8 if r["htf_proxy_trend_aligned"] is not None),
        },
        "days_since_previous_raw_accept_same_direction": {
            "A_67": _stats([r["days_since_previous_raw_accept_same_direction"] for r in a67]),
            "C_8": _stats([r["days_since_previous_raw_accept_same_direction"] for r in c8]),
        },
    }

    c8_years = sorted(r["year"] for r in c8)
    year_concentration_note = (
        f"Gli 8 B-only cadono negli anni {c8_years} - "
        f"{'concentrati in un sottoinsieme ristretto' if len(set(c8_years)) <= 4 else 'distribuiti su piu\' anni'} "
        f"({len(set(c8_years))} anni distinti su 8 eventi)."
    )

    mag_a = comparison["breakout_magnitude_price_units"]["A_67"].get("median")
    mag_c = comparison["breakout_magnitude_price_units"]["C_8"].get("median")
    magnitude_note = None
    if mag_a is not None and mag_c is not None:
        magnitude_note = (
            f"Magnitudine di breakout mediana: A_67={mag_a}, C_8={mag_c} - "
            f"{'sostanzialmente diversa' if abs(mag_a - mag_c) > 0.3 * mag_a else 'simile'} "
            "fra le due popolazioni."
        )

    new_observation_note = None
    if mag_a is not None and mag_c is not None and mag_c < 0.5 * mag_a:
        new_observation_note = (
            "OSSERVAZIONE NUOVA (Phase 7.9I, non presente in 7.9H): gli 8 B-only hanno una "
            f"magnitudine di breakout mediana MOLTO piu' piccola ({mag_c}) dei 67 "
            f"live-observed ({mag_a}) - marginali/borderline rispetto alla soglia di "
            "Acceptance. Questo e' COERENTE con il meccanismo candidato "
            "INTRADAY_BAR_TIMING_DIFFERENCE gia' ipotizzato in Phase 7.9H (un breakout "
            "marginale sulla barra D1 FINALE potrebbe non aver soddisfatto la soglia "
            "durante la valutazione intraday reale, per uno scarto di prezzo piccolo) - "
            "NON conferma il meccanismo (nessun nuovo esperimento eseguito qui), ma e' un "
            "elemento di evidenza indiretta a favore, da riportare come "
            "POST_HOC_OBSERVATION -> NEW HYPOTHESIS, non come conclusione."
        )

    return {
        "phase": "7.9I",
        "purpose": "Confronto distribuzionale fra gli 8 eventi B-only (mai osservati nel "
            "trace live) e i 67 eventi live-observed, su feature causalmente disponibili "
            "(direzione, anno, magnitudine del breakout, volatilita' causale, contesto HTF "
            "proxy, distanza dal precedente raw-accept). Non usati per migliorare il "
            "risultato primario, che li esclude per costruzione (Population B = solo "
            "OPENED, sottoinsieme di Population A).",
        "comparison": comparison,
        "year_concentration_note": year_concentration_note,
        "magnitude_note": magnitude_note,
        "new_observation_post_hoc": new_observation_note,
        "reference_causal_classification": "server/research_scripts/phase7/phase7_9h/"
            "b_only_residual_classification_v1.json (Phase 7.9H) - meccanismo "
            "CROSS_TIMEFRAME_STATE_CONTAMINATION escluso strutturalmente per tutti e 8; "
            "2 meccanismi candidati non confermati (timing intrabarra, gap di attivazione).",
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79I_DIR, "breakout_acc_b_only_comparison_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(payload["year_concentration_note"])
    print(payload["magnitude_note"])
    return doc


if __name__ == "__main__":
    main()
