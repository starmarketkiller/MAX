#!/usr/bin/env python3
"""Phase 7.21 punto 11 - Minimum Viable Capital. Valuta la strategia su
300/500/1000/2500/10000 EUR con contract size reale, leva reale, lot
step, margin requirements, spread/costi - l'edge va normalizzato al
rischio, non confuso col saldo iniziale."""
import os
import statistics
import sys

PHASE721_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE721_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE721_DIR)
from nxs_breakoutacc_dataset_loader import load_opened_events, risk_r  # noqa: E402

CONTRACT_SIZE_OZ = 100  # GOLD standard (coerente con le run r002/r003)
MIN_LOT = 0.01
LOT_STEP = 0.01
LEVERAGE_REAL_ACCOUNT = 100  # coerente col certificate r002 (leverage=1:100) - EUR/USD non convertito
CAPITAL_LEVELS_EUR = [300, 500, 1000, 2500, 10000]


def build():
    events = load_opened_events()
    risks = [risk_r(e) for e in events]
    avg_risk_price_units = statistics.mean(risks)
    max_risk_price_units = max(risks)
    min_risk_price_units = min(risks)
    # prezzo GOLD medio nel campione, per stimare il margine a min lot.
    avg_price = statistics.mean(e["entry_fill_price"] for e in events)

    margin_per_min_lot = (CONTRACT_SIZE_OZ * MIN_LOT * avg_price) / LEVERAGE_REAL_ACCOUNT
    risk_usd_per_min_lot_avg = CONTRACT_SIZE_OZ * MIN_LOT * avg_risk_price_units
    risk_usd_per_min_lot_max = CONTRACT_SIZE_OZ * MIN_LOT * max_risk_price_units

    table = []
    for capital in CAPITAL_LEVELS_EUR:
        risk_pct_avg = (risk_usd_per_min_lot_avg / capital) * 100
        risk_pct_max = (risk_usd_per_min_lot_max / capital) * 100
        margin_pct = (margin_per_min_lot / capital) * 100
        free_margin_reserve_pct = 100 - margin_pct
        # max posizioni concorrenti sostenibili solo per margine (non per rischio simultaneo -
        # BREAKOUT_ACC e' D1/selettore isolato, tipicamente 1 posizione alla volta nei run usati).
        max_concurrent_by_margin = int(capital // margin_per_min_lot) if margin_per_min_lot > 0 else None
        table.append({
            "capital_eur": capital,
            "technically_executable_at_min_lot": capital >= margin_per_min_lot,
            "margin_usage_usd_at_min_lot": margin_per_min_lot,
            "margin_usage_pct_of_capital": margin_pct,
            "free_margin_reserve_pct": free_margin_reserve_pct,
            "risk_usd_at_min_lot_avg_sl": risk_usd_per_min_lot_avg,
            "risk_pct_of_capital_avg_sl": risk_pct_avg,
            "risk_usd_at_min_lot_worst_sl_seen": risk_usd_per_min_lot_max,
            "risk_pct_of_capital_worst_sl_seen": risk_pct_max,
            "max_concurrent_positions_by_margin_only": max_concurrent_by_margin,
            "risk_profile_materially_altered_by_min_lot_floor": risk_pct_avg > 5.0,
            "note": "Il rischio per trade e' IMPOSTO dal lot minimo (0.01) - non e' scalabile sotto "
                   "questa soglia. A capitale basso, 0.01 lot puo' rappresentare una frazione di "
                   "rischio molto maggiore del tipico 1-2% raccomandato, alterando materialmente il "
                   "profilo di rischio rispetto a un conto piu' grande con lo STESSO 0.01 lot fisso "
                   "usato in questo dataset.",
        })

    minimum_viable_capital_threshold_pct = 5.0  # soglia dichiarata: rischio medio a min lot <= 5% del capitale
    mvc_candidates = [row for row in table if row["risk_pct_of_capital_avg_sl"] <= minimum_viable_capital_threshold_pct]
    minimum_viable_capital = mvc_candidates[0]["capital_eur"] if mvc_candidates else None

    payload = {
        "assumptions_declared": {
            "contract_size_oz": CONTRACT_SIZE_OZ, "min_lot": MIN_LOT, "lot_step": LOT_STEP,
            "leverage": f"1:{LEVERAGE_REAL_ACCOUNT}",
            "eur_usd_conversion": "NON applicata (capitale trattato in USD-equivalente 1:1 per "
                "semplicita' - i valori EUR richiesti dalla task sono usati come etichetta di "
                "capitale, non convertiti da un tasso di cambio specifico, non disponibile/"
                "pertinente in questa fase).",
            "avg_entry_price_gold_in_sample": avg_price,
            "avg_risk_price_units_sl_distance": avg_risk_price_units,
            "max_risk_price_units_sl_distance_seen": max_risk_price_units,
            "min_risk_price_units_sl_distance_seen": min_risk_price_units,
        },
        "capital_table": table,
        "minimum_viable_capital_definition": "Capitale minimo (fra i livelli testati) sotto cui il "
            f"rischio medio imposto dal lot minimo (0.01) supera il {minimum_viable_capital_threshold_pct}% "
            "del capitale per trade - soglia dichiarata qui, non ottimizzata sui risultati.",
        "MINIMUM_VIABLE_CAPITAL_EUR": minimum_viable_capital,
        "MINIMUM_VIABLE_CAPITAL_CAVEAT": "Questa e' una stima STRUTTURALE (margine/rischio-per-trade "
            "normalizzato), NON una promozione a trading su questo capitale - dipende interamente "
            "dal fatto che l'edge stesso sia validato (vedi decision_card_v1.json) prima di essere "
            "rilevante. Nessun position sizing o risk multiplier proposto qui.",
        "no_optimization_no_sizing_proposed": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE721_DIR, "minimum_viable_capital_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  MINIMUM_VIABLE_CAPITAL_EUR: {payload['MINIMUM_VIABLE_CAPITAL_EUR']}")
    for row in payload["capital_table"]:
        print(f"  {row['capital_eur']}EUR: risk%={row['risk_pct_of_capital_avg_sl']:.1f} "
              f"margin%={row['margin_usage_pct_of_capital']:.2f} "
              f"executable={row['technically_executable_at_min_lot']}")


if __name__ == "__main__":
    main()
