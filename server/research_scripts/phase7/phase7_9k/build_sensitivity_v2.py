#!/usr/bin/env python3
"""Phase 7.9K - Sensitivity V2: confronto Population A (67) vs tutti i
75, usando la misurazione A (post-segnale, uniforme, timestamp reale
per i 67 + sintetico esplicito per gli 8 B-only) con bar semantics
corretta. Sostituisce sia la sensitivity strutturale sia quella di
percorso di Phase 7.9I/7.9J con un'unica versione basata sulla
metodologia corretta e piu' precisa (timestamp reali)."""
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

    pop_a = [e for e in events if e["population_source"] == "LIVE_TRACE_GENERATED"]
    pop_c = [e for e in events if e["population_source"] == "OFFLINE_ISOLATED_RECONSTRUCTION_ONLY"]

    def profile(pop, label):
        mfe_vals, fwd60_vals = [], []
        n_censored = 0
        for e in pop:
            path = e["measurement_A_post_signal_path"]
            if path.get("status") not in ("FULL_COVERAGE", "CENSORED_INSUFFICIENT_BARS"):
                continue
            if path["status"] == "CENSORED_INSUFFICIENT_BARS" and 60 in path.get("horizons_censored", []):
                n_censored += 1
            mfe_vals.append(path["mfe_price_units"])
            fwd60_vals.append(path["horizons"].get("fwd_return_60d1_price_units"))
        return {"label": label, "n": len(pop), "n_censored_at_60": n_censored,
               "mfe": _stats(mfe_vals), "fwd_return_60d1": _stats(fwd60_vals)}

    profile_a67 = profile(pop_a, "Population A (67 live-observed, misurazione A)")
    profile_75 = profile(events, "Tutti i 75 (misurazione A)")
    profile_c8 = profile(pop_c, "Gli 8 B-only da soli (misurazione A, timestamp SINTETICO)")

    delta = None
    if (profile_a67["fwd_return_60d1"].get("median") is not None
            and profile_75["fwd_return_60d1"].get("median") is not None):
        delta = round(profile_75["fwd_return_60d1"]["median"]
                      - profile_a67["fwd_return_60d1"]["median"], 4)

    return {
        "phase": "7.9K", "measurement": "A (post-segnale, uniforme, bar semantics corretta)",
        "timestamp_disclaimer": "I 67 live-observed usano il timestamp REALE del segnale "
            "(dal trace live) - gli 8 B-only usano un timestamp SINTETICO "
            "(SYNTHETIC_NOT_OBSERVED_NOON_PLACEHOLDER, mai un tempo di esecuzione "
            "osservato).",
        "population_A_67": profile_a67,
        "population_all_75": profile_75,
        "population_C_8_alone": profile_c8,
        "delta_fwd_return_60d1_median": delta,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79K_DIR, "breakout_acc_sensitivity_v2.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print("delta:", payload["delta_fwd_return_60d1_median"])
    return doc


if __name__ == "__main__":
    main()
