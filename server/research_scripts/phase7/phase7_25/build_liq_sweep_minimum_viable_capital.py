#!/usr/bin/env python3
"""Phase 7.25 punto 11 - Minimum Viable Capital per LIQ_SWEEP, stessa
metodologia di Phase 7.21/7.22 per confrontabilita' diretta."""
import os
import statistics
import sys

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE725_DIR)
from nxs_liq_sweep_edge_dataset_loader import load_closed_events, risk_r  # noqa: E402

CONTRACT_SIZE_OZ = 100
MIN_LOT = 0.01
LOT_STEP = 0.01
LEVERAGE_REAL_ACCOUNT = 500  # osservato nel certificato (Phase 7.23), non il valore richiesto nell'ini
CAPITAL_LEVELS_EUR = [300, 500, 1000, 2500, 10000]
RISK_THRESHOLD_PCT = 5.0  # stessa soglia dichiarata di Phase 7.21/7.22


def build():
    events = load_closed_events()
    if not events:
        return {"status": "NO_EVENTS_YET"}

    risks = [risk_r(e) for e in events]
    avg_risk = statistics.mean(risks)
    max_risk = max(risks)
    min_risk = min(risks)
    avg_price = statistics.mean(e["entry"]["signal_reference_price"] for e in events)

    margin_per_min_lot = (CONTRACT_SIZE_OZ * MIN_LOT * avg_price) / LEVERAGE_REAL_ACCOUNT
    risk_usd_avg = CONTRACT_SIZE_OZ * MIN_LOT * avg_risk
    risk_usd_max = CONTRACT_SIZE_OZ * MIN_LOT * max_risk

    table = []
    for capital in CAPITAL_LEVELS_EUR:
        risk_pct_avg = (risk_usd_avg / capital) * 100
        risk_pct_max = (risk_usd_max / capital) * 100
        margin_pct = (margin_per_min_lot / capital) * 100
        table.append({
            "capital_eur": capital,
            "technically_executable_at_min_lot": capital >= margin_per_min_lot,
            "margin_usage_usd_at_min_lot": margin_per_min_lot,
            "margin_usage_pct_of_capital": margin_pct,
            "free_margin_reserve_pct": 100 - margin_pct,
            "risk_usd_at_min_lot_avg_sl": risk_usd_avg, "risk_pct_of_capital_avg_sl": risk_pct_avg,
            "risk_usd_at_min_lot_worst_sl_seen": risk_usd_max,
            "risk_pct_of_capital_worst_sl_seen": risk_pct_max,
            "max_concurrent_positions_by_margin_only": int(capital // margin_per_min_lot)
                                                       if margin_per_min_lot > 0 else None,
            "risk_profile_materially_altered_by_min_lot_floor": risk_pct_avg > RISK_THRESHOLD_PCT,
            "dd_monetario_atteso_worst_case_seen": risk_usd_max,
        })

    mvc_candidates = [row for row in table if row["risk_pct_of_capital_avg_sl"] <= RISK_THRESHOLD_PCT]
    mvc = mvc_candidates[0]["capital_eur"] if mvc_candidates else None

    payload = {
        "assumptions_declared": {"contract_size_oz": CONTRACT_SIZE_OZ, "min_lot": MIN_LOT,
            "lot_step": LOT_STEP, "leverage": f"1:{LEVERAGE_REAL_ACCOUNT}",
            "avg_entry_price_gold_in_sample": avg_price,
            "avg_risk_price_units_sl_distance": avg_risk,
            "max_risk_price_units_sl_distance_seen": max_risk,
            "min_risk_price_units_sl_distance_seen": min_risk,
            "note_price_range_wide": "Il campione copre GOLD da ~1826 a ~4001 (2023-2026) - la "
                "distanza SL in price units varia molto in valore assoluto nel tempo (ATR scala "
                "col prezzo) - avg_price/avg_risk sono medie sull'intero campione, non "
                "rappresentative di un singolo regime di prezzo."},
        "capital_table": table,
        "minimum_viable_capital_definition": f"Capitale minimo (fra i livelli testati) sotto cui il "
            f"rischio medio a lotto minimo (0.01) supera il {RISK_THRESHOLD_PCT}% del capitale.",
        "MINIMUM_VIABLE_CAPITAL_EUR": mvc,
        "max_concurrent_exposure_note": "LIQ_SWEEP e' single-position-at-a-time per costruzione "
            "(gate OPEN_POSITION verificato in Phase 7.24 - 3569/3623 blocchi sono per questo "
            "motivo) - massimo 1 posizione concorrente per definizione, non un vincolo di margine.",
        "no_optimization_no_sizing_proposed": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE725_DIR, "minimum_viable_capital_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    if payload.get("status") != "NO_EVENTS_YET":
        print(f"  MINIMUM_VIABLE_CAPITAL_EUR: {payload['MINIMUM_VIABLE_CAPITAL_EUR']}")


if __name__ == "__main__":
    main()
