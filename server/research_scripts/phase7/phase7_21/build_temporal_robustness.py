#!/usr/bin/env python3
"""Phase 7.21 punto 7 - robustezza temporale: anno, direzione,
concentrazione dei profitti, dipendenza da pochi eventi."""
import os
import sys
from collections import defaultdict
from datetime import datetime

PHASE721_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE721_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE721_DIR)
from nxs_breakoutacc_dataset_loader import load_opened_events, net_pnl, split_by_direction  # noqa: E402


def _dt(s):
    return datetime.strptime(s, "%Y.%m.%d %H:%M:%S")


def build():
    events = load_opened_events()
    events_sorted = sorted(events, key=lambda e: _dt(e["entry_fill_time"]))
    nets = [net_pnl(e) for e in events_sorted]
    total_net = sum(nets)

    by_year = defaultdict(list)
    for e in events_sorted:
        by_year[_dt(e["entry_fill_time"]).year].append(net_pnl(e))
    per_year = {str(y): {"n_trades": len(v), "net_pnl_sum": sum(v),
                        "win_rate": sum(1 for p in v if p > 0) / len(v)}
               for y, v in sorted(by_year.items())}
    years_positive = sum(1 for v in per_year.values() if v["net_pnl_sum"] > 0)
    years_total = len(per_year)

    # concentrazione: contributo dei top N trade al P&L totale.
    sorted_desc = sorted(nets, key=lambda x: -x)
    concentration = {}
    for topn in (1, 3, 5):
        topn_actual = min(topn, len(sorted_desc))
        concentration[f"top_{topn}"] = {
            "sum": sum(sorted_desc[:topn_actual]),
            "pct_of_total_net": (sum(sorted_desc[:topn_actual]) / total_net * 100) if total_net else None,
        }
    top10pct_n = max(1, round(len(sorted_desc) * 0.10))
    concentration["top_10pct_n_trades"] = top10pct_n
    concentration["top_10pct"] = {
        "sum": sum(sorted_desc[:top10pct_n]),
        "pct_of_total_net": (sum(sorted_desc[:top10pct_n]) / total_net * 100) if total_net else None,
    }

    # edge senza i top N trade (rimozione = l'edge scompare?).
    edge_without_top = {}
    for topn in (1, 3, 5):
        topn_actual = min(topn, len(sorted_desc))
        remaining = sum(nets) - sum(sorted_desc[:topn_actual])
        edge_without_top[f"without_top_{topn}"] = {
            "net_total_remaining": remaining, "still_positive": remaining > 0,
        }

    # rolling window (10 trade), su expectancy netta.
    window = 10
    rolling = []
    if len(nets) >= window:
        for i in range(len(nets) - window + 1):
            w = nets[i:i + window]
            rolling.append({"start_trade_idx": i, "end_trade_idx": i + window - 1,
                           "mean_net": sum(w) / window})

    groups = split_by_direction(events)
    direction_split = {}
    for name, evs in groups.items():
        n_evs = sorted(evs, key=lambda e: _dt(e["entry_fill_time"]))
        net_vals = [net_pnl(e) for e in n_evs]
        direction_split[name] = {"n": len(n_evs), "net_total": sum(net_vals)}

    payload = {
        "by_year": per_year,
        "years_with_positive_net": years_positive,
        "years_total_with_at_least_1_trade": years_total,
        "concentration_of_profit": concentration,
        "edge_survives_without_top_trades": edge_without_top,
        "rolling_window_10_trades_mean_net": rolling,
        "direction_split_net_total": direction_split,
        "single_regime_caveat": "Tutti i 47 eventi provengono da un UNICO run MT5 continuo "
            "(2019.02-2026.06, stesso broker/simbolo) - 'per anno' qui e' una suddivisione "
            "temporale dello STESSO campione, non regimi di mercato indipendenti verificati "
            "separatamente (stesso limite gia' dichiarato in Phase 7.9K).",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE721_DIR, "temporal_robustness_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  anni positivi: {payload['years_with_positive_net']}/{payload['years_total_with_at_least_1_trade']}")
    print(f"  top1 % of total: {payload['concentration_of_profit']['top_1']['pct_of_total_net']:.1f}%")
    print(f"  top5 % of total: {payload['concentration_of_profit']['top_5']['pct_of_total_net']:.1f}%")


if __name__ == "__main__":
    main()
