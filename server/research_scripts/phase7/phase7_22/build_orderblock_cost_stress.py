#!/usr/bin/env python3
"""Phase 7.22 punto 7 - stress dei costi, scenari PREREGISTRATI.
COST_BASE = dati reali cosi' come registrati; COST_MODERATE/STRESS
aggiungono un costo di round-trip ASSUNTO (dichiarato, non misurato)."""
import os
import sys

PHASE722_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE722_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE722_DIR)
from nxs_orderblock_dataset_loader import load_events, net_pnl, split_by_direction  # noqa: E402

SCENARIOS_EXTRA_ROUNDTRIP_COST_PRICE_UNITS = {
    "COST_BASE": 0.0, "COST_MODERATE": 0.5, "COST_STRESS": 2.0,
}  # stessi livelli dichiarati in Phase 7.21 (BREAKOUT_ACC) - coerenza fra le due validazioni


def _stats(events, extra_cost):
    n = len(events)
    if n == 0:
        return {"n_trades": 0, "net_expectancy_per_trade": None, "profit_factor": None,
               "win_rate": None, "net_expectancy_total": None, "survives_positive": None}
    nets = [net_pnl(e) - extra_cost for e in events]
    wins = [p for p in nets if p > 0]
    losses = [p for p in nets if p <= 0]
    gross_win, gross_loss = sum(wins), abs(sum(losses))
    return {"n_trades": n, "net_expectancy_per_trade": sum(nets) / n, "net_expectancy_total": sum(nets),
           "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else None,
           "win_rate": len(wins) / n, "survives_positive": (sum(nets) / n) > 0}


def build():
    events = load_events()
    groups = split_by_direction(events)
    scenarios = {}
    for name, extra in SCENARIOS_EXTRA_ROUNDTRIP_COST_PRICE_UNITS.items():
        scenarios[name] = {"extra_roundtrip_cost_assumed_price_units": extra,
                          "assumption_declared_not_measured": extra > 0,
                          "ALL": _stats(groups["ALL"], extra), "BUY": _stats(groups["BUY"], extra),
                          "SELL": _stats(groups["SELL"], extra)}
    payload = {
        "principle": "COST_BASE usa i fill/swap/commissione REALI gia' registrati dal Tester - non "
                    "e' 'senza costi'. COST_MODERATE/STRESS aggiungono un costo ASSUNTO, dichiarato.",
        "scenarios": scenarios,
        "scenario_not_selected_to_preserve_edge": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE722_DIR, "orderblock_cost_stress_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    for name, sc in payload["scenarios"].items():
        if sc["ALL"]["n_trades"]:
            print(f"  {name}: ALL exp/trade={sc['ALL']['net_expectancy_per_trade']:.2f} "
                  f"survives={sc['ALL']['survives_positive']}")


if __name__ == "__main__":
    main()
