#!/usr/bin/env python3
"""Phase 7.21 punto 3 - baseline economica SENZA tuning, sui 47 eventi
OPENED (unico sottoinsieme con esito economico reale) del dataset
canonico V2. Nessun parametro modificato. ALL/BUY/SELL con denominatori
espliciti. BUY-only NON e' presentato come strategia validata - solo
come descrizione, coerente con H2 dichiarata post-hoc in
data_exposure_map_v1.json."""
import os
import statistics
import sys
from datetime import datetime

PHASE721_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE721_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE721_DIR)
from nxs_breakoutacc_dataset_loader import (load_opened_events, net_pnl, gross_pnl,  # noqa: E402
                                            risk_r, net_pnl_in_r, split_by_direction)

CONTRACT_SIZE_OZ = 100  # GOLD standard, coerente con le run r002/r003 (lotto fisso 0.01)
LEVERAGE = 100  # coerente col certificate r002 (leverage=1:100)


def _dt(s):
    return datetime.strptime(s, "%Y.%m.%d %H:%M:%S")


def _max_drawdown_and_recovery(pnls_in_order):
    """Drawdown sull'equity cumulata (solo P&L di trade, nessun deposito
    iniziale sommato - drawdown IN VALUTA del solo flusso di trade)."""
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls_in_order:
        equity += p
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)
    net_total = sum(pnls_in_order)
    recovery_factor = (net_total / max_dd) if max_dd > 0 else None
    return max_dd, recovery_factor


def _max_consecutive(pnls_in_order, want_positive):
    best = cur = 0
    for p in pnls_in_order:
        is_match = (p > 0) if want_positive else (p < 0)
        cur = cur + 1 if is_match else 0
        best = max(best, cur)
    return best


def _stats_for_group(events):
    events_sorted = sorted(events, key=lambda e: _dt(e["entry_fill_time"]))
    n = len(events_sorted)
    nets = [net_pnl(e) for e in events_sorted]
    grosses = [gross_pnl(e) for e in events_sorted]
    r_multiples = [net_pnl_in_r(e) for e in events_sorted if net_pnl_in_r(e) is not None]

    wins = [p for p in nets if p > 0]
    losses = [p for p in nets if p <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))

    holding_days = []
    margins = []
    for e in events_sorted:
        entry_t, exit_t = _dt(e["entry_fill_time"]), _dt(e["exit_fill_time"])
        holding_days.append((exit_t - entry_t).total_seconds() / 86400.0)
        margin = (CONTRACT_SIZE_OZ * e["entry_volume"] * e["entry_fill_price"]) / LEVERAGE
        margins.append(margin)

    period_days = None
    if n > 1:
        period_days = (_dt(events_sorted[-1]["entry_fill_time"]) -
                       _dt(events_sorted[0]["entry_fill_time"])).total_seconds() / 86400.0

    return {
        "n_trades": n,
        "net_expectancy_per_trade": (sum(nets) / n) if n else None,
        "net_expectancy_total": sum(nets),
        "gross_expectancy_per_trade": (sum(grosses) / n) if n else None,
        "expectancy_in_r_per_trade": (sum(r_multiples) / len(r_multiples)) if r_multiples else None,
        "expectancy_in_r_all_values": [round(x, 3) for x in r_multiples],
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else None,
        "win_rate": (len(wins) / n) if n else None,
        "n_wins": len(wins), "n_losses": len(losses),
        "avg_win": (sum(wins) / len(wins)) if wins else None,
        "avg_loss": (sum(losses) / len(losses)) if losses else None,
        "payoff_ratio": (abs(sum(wins) / len(wins)) / abs(sum(losses) / len(losses)))
                        if wins and losses and sum(losses) != 0 else None,
        "max_consecutive_wins": _max_consecutive(nets, True),
        "max_consecutive_losses": _max_consecutive(nets, False),
        "max_drawdown_currency": _max_drawdown_and_recovery(nets)[0],
        "recovery_factor": _max_drawdown_and_recovery(nets)[1],
        "trade_frequency_per_year": (n / (period_days / 365.25)) if period_days else None,
        "period_days_covered_by_this_group": period_days,
        "avg_holding_days": statistics.mean(holding_days) if holding_days else None,
        "median_holding_days": statistics.median(holding_days) if holding_days else None,
        "total_exposure_days_sum": sum(holding_days),
        "exposure_pct_of_period": (sum(holding_days) / period_days * 100) if period_days else None,
        "avg_margin_usd_at_0_01_lot_lev_100": statistics.mean(margins) if margins else None,
        "net_pnl_distribution": {
            "min": min(nets), "max": max(nets), "mean": statistics.mean(nets),
            "median": statistics.median(nets),
            "stdev": statistics.stdev(nets) if n > 1 else None,
            "skew_note": "Skew non calcolato (campione piccolo, poco informativo) - vedi "
                        "distribuzione grezza in net_pnl_all_values per ispezione diretta.",
        },
        "net_pnl_all_values": [round(p, 2) for p in nets],
    }


def build():
    events = load_opened_events()
    groups = split_by_direction(events)

    payload = {
        "population": "Solo i 47/75 eventi con funnel_terminal_stage=OPENED (unico sottoinsieme con "
            "P&L reale) - i restanti 28 (11 BLOCKED, 9 BROKER_REJECT, 8 NEVER_OBSERVED_IN_LIVE_TRACE) "
            "non hanno un esito economico e sono trattati separatamente in "
            "build_execution_realism.py (punto 5) - NON scartati silenziosamente.",
        "denominators_explicit": {"ALL": len(groups["ALL"]), "BUY": len(groups["BUY"]),
                                  "SELL": len(groups["SELL"])},
        "net_pnl_definition": "realized_pnl (deal profit grezzo) + realized_swap + "
            "realized_commission - tutti campi gia' presenti nel dataset canonico, nessun dato nuovo.",
        "risk_r_definition": "|entry_fill_price - entry_sl| in price units (= $ a lotto fisso 0.01 su "
            "GOLD, contract_size 100oz - verificato: coincide esattamente col |realized_pnl| dei "
            "trade usciti a SL).",
        "ALL": _stats_for_group(groups["ALL"]),
        "BUY": _stats_for_group(groups["BUY"]),
        "SELL": _stats_for_group(groups["SELL"]),
        "buy_only_not_presented_as_validated_strategy": True,
        "no_tuning_applied": True,
        "no_optimization_applied": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE721_DIR, "baseline_economics_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    for k in ("ALL", "BUY", "SELL"):
        g = payload[k]
        print(f"  {k}: n={g['n_trades']} net_exp/trade={g['net_expectancy_per_trade']:.2f} "
              f"PF={g['profit_factor']} WR={g['win_rate']:.2f}" if g['n_trades'] else f"  {k}: n=0")


if __name__ == "__main__":
    main()
