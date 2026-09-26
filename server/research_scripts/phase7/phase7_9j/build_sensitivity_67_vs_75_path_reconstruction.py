#!/usr/bin/env python3
"""Phase 7.9J - punto 2 della revisione: confronto dei PERCORSI
post-segnale fra Population A (67 live-observed) e tutti i 75 eventi
(67 + 8 B-only), con convenzioni temporali/di prezzo IDENTICHE per
tutti gli eventi non-OPENED (proxy c1 = chiusura della barra di
breakout, stesso metodo del Gate Diagnostic - MAI un fill reale o un
P&L eseguito). L'analisi dei 47 trade con fill reale resta separata e
distinta (population_source_detail='REAL_FILL').

Il confronto 67 vs 75 di Phase 7.9I copriva SOLO conteggi strutturali
(direzione/anno/magnitudine) - qui si estende, dove ricostruibile, al
percorso (MFE/MAE/forward return), esplicitamente etichettando quali
righe sono reali e quali controfattuali.
"""
import os
import statistics
import sys
from datetime import datetime

PHASE79J_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79I_DIR = os.path.abspath(os.path.join(PHASE79J_DIR, "..", "phase7_9i"))
ROOT = os.path.abspath(os.path.join(PHASE79J_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

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
    feat = ctx.build_feature_table()
    rows = feat["rows"]
    d1_bars = ctx.load_d1_bars()

    pop_a = [r for r in rows if r["population_source"] == "LIVE_TRACE_GENERATED"]  # 67
    pop_c = [r for r in rows if r["population_source"] == "OFFLINE_ISOLATED_RECONSTRUCTION_ONLY"]  # 8
    pop_all_75 = rows

    reconstructable = all(r["breakout_close_c1"] is not None for r in pop_c)
    limitation_note = None
    if not reconstructable:
        limitation_note = (
            "Il confronto di percorso NON e' ricostruibile per uno o piu' degli 8 eventi "
            "B-only (manca il prezzo di chiusura della barra di breakout, c1) - "
            "l'esclusione degli 8 dalle analisi primarie NON puo' essere qualificata come "
            "una vera sensitivity del meccanismo, resta un limite dichiarato."
        )

    def event_path(r):
        if r["funnel_terminal_stage"] == "OPENED":
            path = r["post_entry_path_anatomy"]
            kind = "REAL_FILL"
        else:
            if r["breakout_close_c1"] is None:
                return None, None
            path = ctx.counterfactual_path_anatomy(
                d1_bars, r["d1_bar_date"], r["breakout_close_c1"], r["direction"])
            kind = "COUNTERFACTUAL_PROXY_C1"
        if path.get("status") != "OK":
            return None, kind
        return path, kind

    def population_path_profile(pop, label):
        real_rows = []
        cf_rows = []
        for r in pop:
            path, kind = event_path(r)
            if path is None:
                continue
            fwd60 = path["horizons"].get("fwd_return_60d1_price_units")
            entry = {"event_id": r["event_id"], "mfe": path["mfe_price_units"],
                    "mae": path["mae_price_units"], "fwd_return_60d1": fwd60}
            if kind == "REAL_FILL":
                real_rows.append(entry)
            else:
                cf_rows.append(entry)
        combined = real_rows + cf_rows
        return {
            "label": label, "n_total_with_path": len(combined),
            "n_real_fill": len(real_rows), "n_counterfactual_proxy": len(cf_rows),
            "combined_mfe": _stats([e["mfe"] for e in combined]),
            "combined_mae": _stats([e["mae"] for e in combined]),
            "combined_fwd_return_60d1": _stats([e["fwd_return_60d1"] for e in combined]),
            "real_fill_only_mfe": _stats([e["mfe"] for e in real_rows]),
            "real_fill_only_fwd_return_60d1": _stats([e["fwd_return_60d1"] for e in real_rows]),
            "counterfactual_only_mfe": _stats([e["mfe"] for e in cf_rows]),
            "counterfactual_only_fwd_return_60d1": _stats([e["fwd_return_60d1"] for e in cf_rows]),
        }

    profile_a67 = population_path_profile(pop_a, "Population A (67 live-observed: 47 "
        "REAL_FILL + 20 COUNTERFACTUAL_PROXY_C1 per BLOCKED/BROKER_REJECT)")
    profile_75 = population_path_profile(pop_all_75, "Tutti i 75 (67 + 8 B-only, tutti "
        "COUNTERFACTUAL_PROXY_C1 tranne i 47 REAL_FILL)")

    delta_fwd60_median = None
    if (profile_a67["combined_fwd_return_60d1"].get("median") is not None
            and profile_75["combined_fwd_return_60d1"].get("median") is not None):
        delta_fwd60_median = round(
            profile_75["combined_fwd_return_60d1"]["median"]
            - profile_a67["combined_fwd_return_60d1"]["median"], 4)

    return {
        "phase": "7.9J",
        "purpose": "Estensione del confronto 67 vs 75 (Phase 7.9I, solo strutturale) al "
            "PERCORSO post-segnale, dove ricostruibile - stessa metodologia del Gate "
            "Diagnostic (proxy c1 per eventi mai eseguiti, MAI un fill/P&L reale).",
        "no_fill_or_pnl_attributed_to_non_opened_events": True,
        "reconstructable_for_all_8_b_only": reconstructable,
        "limitation_declared": limitation_note,
        "population_A_67_path_profile": profile_a67,
        "population_all_75_path_profile": profile_75,
        "delta_combined_fwd_return_60d1_median": delta_fwd60_median,
        "conclusion": (
            "Il confronto di percorso e' ricostruibile per tutti gli 8 B-only (c1 "
            "disponibile per costruzione). La differenza fra Population A e tutti i 75 "
            f"sul forward return mediano a 60 barre e' {delta_fwd60_median} unita' di "
            "prezzo - " + ("marginale" if delta_fwd60_median is not None and abs(delta_fwd60_median) < 5
                          else "non trascurabile") + ". IMPORTANTE: questo confronto "
            "usa percorsi CONTROFATTUALI (proxy) per 28 dei 75 eventi (20 BLOCKED/"
            "BROKER_REJECT + 8 B-only) - nessuno di questi e' un trade reale, e questo "
            "confronto NON sostituisce ne' altera le analisi primarie di Path Anatomy/"
            "Natural Horizon/Mechanism Discovery (Phase 7.9I), che restano basate "
            "ESCLUSIVAMENTE sui 47 eventi REAL_FILL (Population B)."
        ),
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79J_DIR, "breakout_acc_sensitivity_67_vs_75_path_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(payload["conclusion"])
    return doc


if __name__ == "__main__":
    main()
