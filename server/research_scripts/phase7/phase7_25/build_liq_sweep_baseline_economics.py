#!/usr/bin/env python3
"""Phase 7.25 punto 2 - baseline economica SENZA tuning, sui 42 eventi
CLOSED del dataset canonico MT5 (Phase 7.24). ALL/BUY/SELL con
denominatori espliciti. Nessun lato eliminato per performance peggiore
(SELL ha solo 3 eventi - conservato comunque)."""
import os
import statistics
import sys

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE725_DIR)
from nxs_liq_sweep_edge_dataset_loader import (  # noqa: E402
    load_closed_events, net_pnl, net_pnl_in_r, split_by_direction, entry_time, exit_time, _dt)

CONTRACT_SIZE_OZ = 100
LEVERAGE = 500  # valore reale osservato nel certificato (Phase 7.23), non quello richiesto nell'ini


def _max_drawdown_and_recovery(pnls_in_order):
    equity = peak = max_dd = 0.0
    for p in pnls_in_order:
        equity += p
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    net_total = sum(pnls_in_order)
    return max_dd, (net_total / max_dd) if max_dd > 0 else None


def _max_consecutive(pnls_in_order, want_positive):
    best = cur = 0
    for p in pnls_in_order:
        is_match = (p > 0) if want_positive else (p <= 0)
        cur = cur + 1 if is_match else 0
        best = max(best, cur)
    return best


def _stats_for_group(events):
    events_sorted = sorted(events, key=lambda e: _dt(entry_time(e)))
    n = len(events_sorted)
    if n == 0:
        return {"n_trades": 0}
    nets = [net_pnl(e) for e in events_sorted]
    r_multiples = [x for x in (net_pnl_in_r(e) for e in events_sorted) if x is not None]
    wins = [p for p in nets if p > 0]
    losses = [p for p in nets if p <= 0]
    gross_win, gross_loss = sum(wins), abs(sum(losses))

    holding_days, margins = [], []
    for e in events_sorted:
        entry_t, exit_t = _dt(entry_time(e)), _dt(exit_time(e))
        holding_days.append((exit_t - entry_t).total_seconds() / 86400.0)
        margins.append((CONTRACT_SIZE_OZ * (e["lots"] or 0.01) * e["entry"]["signal_reference_price"])
                      / LEVERAGE)

    period_days = (_dt(events_sorted[-1]["entry"]["timestamp"]) -
                  _dt(events_sorted[0]["entry"]["timestamp"])).total_seconds() / 86400.0 if n > 1 else None
    dd, recov = _max_drawdown_and_recovery(nets)

    return {
        "n_trades": n,
        "net_expectancy_per_trade": sum(nets) / n,
        "net_expectancy_total": sum(nets),
        "expectancy_in_r_per_trade": (sum(r_multiples) / len(r_multiples)) if r_multiples else None,
        "expectancy_in_r_all_values": [round(x, 3) for x in r_multiples],
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else None,
        "win_rate": len(wins) / n, "n_wins": len(wins), "n_losses": len(losses),
        "avg_win": (sum(wins) / len(wins)) if wins else None,
        "avg_loss": (sum(losses) / len(losses)) if losses else None,
        "payoff_ratio": (abs(sum(wins) / len(wins)) / abs(sum(losses) / len(losses)))
                        if wins and losses and sum(losses) != 0 else None,
        "max_consecutive_wins": _max_consecutive(nets, True),
        "max_consecutive_losses": _max_consecutive(nets, False),
        "max_drawdown_currency": dd, "recovery_factor": recov,
        "trade_frequency_per_year": (n / (period_days / 365.25)) if period_days else None,
        "period_days_covered_by_this_group": period_days,
        "avg_holding_days": statistics.mean(holding_days),
        "median_holding_days": statistics.median(holding_days),
        "total_exposure_days_sum": sum(holding_days),
        "exposure_pct_of_period": (sum(holding_days) / period_days * 100) if period_days else None,
        "avg_margin_usd_at_lot_lev_500": statistics.mean(margins),
        "net_pnl_distribution": {"min": min(nets), "max": max(nets), "mean": statistics.mean(nets),
                                "median": statistics.median(nets),
                                "stdev": statistics.stdev(nets) if n > 1 else None},
        "net_pnl_all_values": [round(p, 2) for p in nets],
    }


def build():
    events = load_closed_events()
    groups = split_by_direction(events)
    payload = {
        "population": "I 42 eventi CLOSED del dataset canonico MT5 (Phase 7.24, finestra "
            "2023.10.02-2026.06.30) - fill/P&L reali del Tester, MT5=ground truth. Esclusa la "
            "posizione ancora aperta a fine finestra (nessun P&L realizzato).",
        "denominators_explicit": {k: len(v) for k, v in groups.items()},
        "net_pnl_definition": "actual_pnl del dataset canonico = score_or_pnl della riga CLOSE "
            "(gia' netto - DEAL_PROFIT+DEAL_SWAP+DEAL_COMMISSION, vedi NXS_TradeLedger.mqh).",
        "risk_r_definition": "|signal_reference_price - planned_sl| in price units (= $ a lotto "
            "fisso 0.01 su GOLD) - calcolato indipendentemente dal campo r_multiple del CSV.",
        "ALL": _stats_for_group(groups["ALL"]), "BUY": _stats_for_group(groups["BUY"]),
        "SELL": _stats_for_group(groups["SELL"]),
        "sell_sample_caveat": "SELL ha solo 3 eventi - qualunque statistica su questo gruppo e' "
            "descrittiva, non generalizzabile. Conservato per intero (nessun lato eliminato per "
            "performance peggiore, come da istruzione esplicita del task).",
        "no_side_eliminated_for_worse_performance": True,
        "no_tuning_applied": True, "no_optimization_applied": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE725_DIR, "baseline_economics_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    for k in ("ALL", "BUY", "SELL"):
        g = payload[k]
        if g["n_trades"]:
            print(f"  {k}: n={g['n_trades']} net_exp/trade={g['net_expectancy_per_trade']:.2f} "
                  f"PF={g['profit_factor']} WR={g['win_rate']:.2f}")
        else:
            print(f"  {k}: n=0")


if __name__ == "__main__":
    main()
