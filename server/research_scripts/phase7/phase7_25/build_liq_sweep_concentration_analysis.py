#!/usr/bin/env python3
"""Phase 7.25 punto 3 - profit concentration: dipendenza dai trade
migliori (top1/3/5/10%, risultato senza top-N). Se l'edge sparisce
togliendo pochi eventi, dichiarato esplicitamente."""
import os
import sys

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE725_DIR)
from nxs_liq_sweep_edge_dataset_loader import load_closed_events, net_pnl  # noqa: E402


def _concentration_for(nets):
    n = len(nets)
    total_net = sum(nets)
    sorted_desc = sorted(nets, key=lambda x: -x)
    out = {}
    for topn in (1, 3, 5):
        actual = min(topn, n)
        s = sum(sorted_desc[:actual])
        out[f"top_{topn}"] = {"n_trades_included": actual, "sum": s,
                              "pct_of_total_net": (s / total_net * 100) if total_net else None}
    top10pct_n = max(1, round(n * 0.10))
    s10 = sum(sorted_desc[:top10pct_n])
    out["top_10pct"] = {"n_trades_included": top10pct_n, "sum": s10,
                       "pct_of_total_net": (s10 / total_net * 100) if total_net else None}

    without = {}
    for topn in (1, 3, 5):
        actual = min(topn, n)
        remaining = total_net - sum(sorted_desc[:actual])
        without[f"without_top_{topn}"] = {"net_total_remaining": remaining,
                                          "still_positive": remaining > 0,
                                          "edge_survives": remaining > 0}
    out["without_top_n"] = without
    out["total_net"] = total_net
    out["n_trades"] = n
    out["sorted_desc_all_values"] = [round(x, 2) for x in sorted_desc]
    return out


def build():
    events = load_closed_events()
    nets_all = [net_pnl(e) for e in events]
    result = _concentration_for(nets_all)

    top5 = result["top_5"]
    edge_depends_on_few = (top5["pct_of_total_net"] is not None and
                           abs(top5["pct_of_total_net"]) >= 100.0)
    without_top3_positive = result["without_top_n"]["without_top_3"]["still_positive"]
    without_top5_positive = result["without_top_n"]["without_top_5"]["still_positive"]

    payload = {
        "population": "42 eventi CLOSED (ALL, direzioni non separate - la concentrazione si "
            "valuta sulla serie che genera il P&L aggregato).",
        "concentration": result,
        "edge_depends_heavily_on_top_5_pct_ge_100": edge_depends_on_few,
        "edge_survives_without_top_3": without_top3_positive,
        "edge_survives_without_top_5": without_top5_positive,
        "declared_conclusion": (
            "CONCENTRAZIONE ELEVATA MA NON TOTALE: " if without_top5_positive else
            "CONCENTRAZIONE ESTREMA: l'edge (net P&L positivo) NON sopravvive alla rimozione dei "
            "primi 5 trade migliori - il risultato aggregato dipende in modo determinante da "
            "pochissimi eventi."
        ) + (
            f"i primi 5 trade spiegano il {top5['pct_of_total_net']:.1f}% del netto totale, ma "
            f"rimuovendoli il risultato resta "
            f"{'positivo' if without_top5_positive else 'negativo'} "
            f"({result['without_top_n']['without_top_5']['net_total_remaining']:.2f}$)."
            if top5["pct_of_total_net"] is not None else "non calcolabile."
        ),
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE725_DIR, "concentration_analysis_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    top5 = payload["concentration"]["top_5"]
    print(f"  top_5 pct_of_total_net={top5['pct_of_total_net']:.1f}% "
         f"edge_survives_without_top_5={payload['edge_survives_without_top_5']}")


if __name__ == "__main__":
    main()
