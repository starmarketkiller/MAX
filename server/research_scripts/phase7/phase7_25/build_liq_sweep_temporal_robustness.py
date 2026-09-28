#!/usr/bin/env python3
"""Phase 7.25 punto 7 - robustezza temporale: per anno, rolling window,
direzione, concentrazione temporale del profitto. Un SOLO run MT5
continuo (stesso broker/simbolo) - 'per anno' e' una suddivisione
temporale dello stesso campione, non regimi indipendenti verificati."""
import os
import sys
from collections import defaultdict

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE725_DIR)
from nxs_liq_sweep_edge_dataset_loader import (  # noqa: E402
    load_closed_events, net_pnl, split_by_direction, entry_time, _dt)

ROLLING_WINDOW = 10


def build():
    events = load_closed_events()
    if not events:
        return {"status": "NO_EVENTS_YET"}

    events_sorted = sorted(events, key=lambda e: _dt(entry_time(e)))
    nets = [net_pnl(e) for e in events_sorted]

    by_year = defaultdict(list)
    for e in events_sorted:
        by_year[_dt(entry_time(e)).year].append(net_pnl(e))
    per_year = {str(y): {"n_trades": len(v), "net_pnl_sum": sum(v),
                        "win_rate": sum(1 for p in v if p > 0) / len(v)}
               for y, v in sorted(by_year.items())}
    years_positive = sum(1 for v in per_year.values() if v["net_pnl_sum"] > 0)

    window = ROLLING_WINDOW
    rolling = []
    if len(nets) >= window:
        for i in range(len(nets) - window + 1):
            w = nets[i:i + window]
            rolling.append({"start_trade_idx": i, "end_trade_idx": i + window - 1,
                           "mean_net": sum(w) / window,
                           "entry_time_start": events_sorted[i]["entry"]["timestamp"],
                           "entry_time_end": events_sorted[i + window - 1]["entry"]["timestamp"]})
    rolling_all_positive = all(r["mean_net"] > 0 for r in rolling) if rolling else None
    rolling_min_mean = min((r["mean_net"] for r in rolling), default=None)

    groups = split_by_direction(events)
    direction_split = {name: {"n": len(evs), "net_total": sum(net_pnl(e) for e in evs)}
                       for name, evs in groups.items()}

    payload = {
        "by_year": per_year,
        "years_with_positive_net": years_positive,
        "years_total_with_at_least_1_trade": len(per_year),
        "rolling_window_size": ROLLING_WINDOW,
        f"rolling_window_{ROLLING_WINDOW}_trades_mean_net": rolling,
        "rolling_window_always_positive": rolling_all_positive,
        "rolling_window_min_mean_net": rolling_min_mean,
        "direction_split_net_total": direction_split,
        "regime_caveat": "Tutti gli eventi provengono da un UNICO run MT5 continuo "
            "(2023.10.02-2026.06.30, stesso broker/simbolo GOLD) - 'per anno' e' una "
            "suddivisione temporale dello STESSO campione, non regimi indipendenti verificati "
            "separatamente. Nessuna sessione applicabile (LIQ_SWEEP e' D1, non session-bound - "
            "vedi liq_sweep_identity_map_v1.json, Phase 7.23).",
        "single_regime_caveat": "Vedi regime_caveat.",
        "pattern_descriptive_vs_mechanism_validated": "Questa fase misura SOLO se il pattern "
            "descrittivo (sweep+delivery-candle+direzione, uscita ATR fissa) produce P&L positivo "
            "nel campione - NON dimostra un meccanismo causale (stesso principio gia' applicato a "
            "BREAKOUT_ACC Phase 7.21 e ORDER_BLOCK Phase 7.22).",
        "dependent_on_single_regime": years_positive < len(per_year) or (
            rolling_min_mean is not None and rolling_min_mean <= 0),
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE725_DIR, "temporal_robustness_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    if payload.get("status") != "NO_EVENTS_YET":
        print(f"  anni positivi: {payload['years_with_positive_net']}/"
             f"{payload['years_total_with_at_least_1_trade']} "
             f"rolling_always_positive={payload['rolling_window_always_positive']}")


if __name__ == "__main__":
    main()
