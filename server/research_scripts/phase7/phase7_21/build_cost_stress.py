#!/usr/bin/env python3
"""Phase 7.21 punto 4 - stress dei costi con scenari PREREGISTRATI
(dichiarati prima di guardare quale sopravvive meglio). COST_BASE usa
i dati REALI cosi' come registrati (fill/swap/commissione reali dal
Tester); COST_MODERATE e COST_STRESS aggiungono un costo di round-trip
ASSUNTO (non misurato) sopra il reale, dichiarato esplicitamente come
assunzione - non scelto per preservare l'edge."""
import os
import sys

PHASE721_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE721_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE721_DIR)
from nxs_breakoutacc_dataset_loader import load_opened_events, net_pnl, split_by_direction  # noqa: E402

# Round-trip cost ASSUNTO aggiuntivo, in price units (= $ a lotto fisso 0.01 su GOLD),
# SOPRA quanto gia' reale nel dataset (swap reale gia' incluso in net_pnl - qui si
# aggiunge SOLO l'effetto di spread/slippage che il Tester ha registrato come 0.0
# uniformemente su tutti i 47 eventi, un artefatto noto del motore Tester, non
# un'evidenza che lo slippage reale sarebbe zero - vedi build_execution_realism.py).
SCENARIOS_EXTRA_ROUNDTRIP_COST_PRICE_UNITS = {
    "COST_BASE": 0.0,       # solo i dati reali gia' registrati, nessuna assunzione aggiunta
    "COST_MODERATE": 0.5,   # spread/slippage moderato assunto (ordine di grandezza: frazione di $ su GOLD)
    "COST_STRESS": 2.0,     # scenario avverso assunto (spread allargato + slippage sfavorevole)
}


def _stats(events, extra_cost):
    n = len(events)
    if n == 0:
        return {"n_trades": 0, "net_expectancy_per_trade": None, "profit_factor": None,
               "win_rate": None, "net_expectancy_total": None}
    nets = [net_pnl(e) - extra_cost for e in events]
    wins = [p for p in nets if p > 0]
    losses = [p for p in nets if p <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "n_trades": n,
        "net_expectancy_per_trade": sum(nets) / n,
        "net_expectancy_total": sum(nets),
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else None,
        "win_rate": len(wins) / n,
        "survives_positive": (sum(nets) / n) > 0,
    }


def build():
    events = load_opened_events()
    groups = split_by_direction(events)

    scenarios = {}
    for name, extra in SCENARIOS_EXTRA_ROUNDTRIP_COST_PRICE_UNITS.items():
        scenarios[name] = {
            "extra_roundtrip_cost_assumed_price_units": extra,
            "assumption_declared_not_measured": extra > 0,
            "ALL": _stats(groups["ALL"], extra),
            "BUY": _stats(groups["BUY"], extra),
            "SELL": _stats(groups["SELL"], extra),
        }

    payload = {
        "principle": "COST_BASE non e' 'senza costi' - i fill sono REALI (swap reale gia' incluso), "
                    "e' lo scenario 'nessun costo aggiuntivo ASSUNTO oltre a quanto gia' registrato "
                    "dal Tester'. COST_MODERATE/STRESS aggiungono un costo di round-trip ASSUNTO, "
                    "dichiarato esplicitamente come stima non misurata (i 47 eventi mostrano "
                    "slippage segnale->fill uniformemente 0.0 - un artefatto noto del motore "
                    "Tester in Research Mode, non un'evidenza di slippage reale zero).",
        "commission_observed": "SEMPRE 0.0 su tutti i 47 eventi (probabile convenzione demo/broker "
            "senza commissione esplicita su questo simbolo - non un'assunzione di questa fase, un "
            "dato osservato).",
        "swap_already_real_and_included_in_cost_base": True,
        "scenarios": scenarios,
        "scenario_not_selected_to_preserve_edge": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE721_DIR, "cost_stress_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    for name, sc in payload["scenarios"].items():
        print(f"  {name}: ALL exp/trade={sc['ALL']['net_expectancy_per_trade']:.2f} "
              f"survives={sc['ALL']['survives_positive']}")


if __name__ == "__main__":
    main()
