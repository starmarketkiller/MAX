#!/usr/bin/env python3
"""Phase 7.22 punto 3 - dataset economico canonico ORDER_BLOCK V2,
costruito dal trade log REALE del run MT5 di questa fase (NEXUS_
trades.csv, NXS_LogTradeCSV - stesso meccanismo gia' usato per
BREAKOUT_ACC in Phase 7.21). MT5 = ground truth.

Pairing OPEN->CLOSE: il ticket sulla riga OPEN e' sempre 0 (non ancora
assegnato al momento del log) - l'unico modo affidabile di accoppiare
e' FIFO cronologico per strategia (valido per un run a selettore
isolato, una posizione alla volta - nessuna sovrapposizione attesa per
questa identita', verificato dal verificatore indipendente)."""
import csv
import os
import sys

PHASE722_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE722_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

TRADES_CSV_COLS = ["time", "action", "ticket", "strategy", "price", "lots", "sl", "tp",
                   "score_or_pnl", "reason", "hold_sec", "r_multiple", "resolved_tf"]
DISCOVERY_CSV_PATH = os.path.join(PHASE722_DIR, "nexus_trades_discovery.csv")
STRATEGY_NAME = "ORDER_BLOCK"


def _direction(open_row):
    sl, tp, price = float(open_row["sl"]), float(open_row["tp"]), float(open_row["price"])
    if sl < price < tp:
        return 1
    if sl > price > tp:
        return -1
    return 0  # non determinabile (SL/TP mancanti) - non atteso, segnalato dal verificatore


def _load_rows(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = [dict(zip(TRADES_CSV_COLS, row)) for row in reader if row]
    return rows


def build():
    rows = _load_rows(DISCOVERY_CSV_PATH)
    if rows is None:
        return {"status": "RUN_NOT_YET_CAPTURED",
               "note": "nexus_trades_discovery.csv non presente - copiare NEXUS_trades.csv dal "
                      "terminale dopo il completamento del run nxs_orderblock_discovery.ini."}

    strat_rows = sorted((r for r in rows if r["strategy"] == STRATEGY_NAME), key=lambda r: r["time"])
    opens = [r for r in strat_rows if r["action"] == "OPEN"]
    closes = [r for r in strat_rows if r["action"] == "CLOSE"]

    events = []
    open_queue = list(opens)
    close_queue = list(closes)
    oi = ci = 0
    unmatched_closes = []
    while ci < len(close_queue):
        c = close_queue[ci]
        # il primo OPEN cronologicamente precedente a questo CLOSE e non ancora consumato.
        if oi < len(open_queue) and open_queue[oi]["time"] <= c["time"]:
            o = open_queue[oi]
            oi += 1
            events.append({
                "event_id": f"ob_evt_{len(events):04d}",
                "canonical_strategy_id": STRATEGY_NAME,
                "direction": _direction(o),
                "entry_time": o["time"], "entry_price": float(o["price"]),
                "entry_sl": float(o["sl"]), "entry_tp": float(o["tp"]),
                # entry_lots dalla riga CLOSE, non OPEN: NXS_LogTradeCSV registra sempre lots=0.00
                # sulla riga OPEN (il volume riempito e' noto solo a fill avvenuto) - la riga CLOSE
                # riporta tc.vol_in, il volume totale realmente entrato (bug scoperto e corretto in
                # questa stessa fase, verificato dal verificatore indipendente).
                "entry_lots": float(c["lots"]),
                "exit_time": c["time"], "exit_price": float(c["price"]),
                "exit_reason": c["reason"], "hold_sec": float(c["hold_sec"]),
                "net_pnl": float(c["score_or_pnl"]),  # tc.pnl = DEAL_PROFIT+SWAP+COMMISSION (NET reale)
                "r_multiple_raw": float(c["r_multiple"]) if c["r_multiple"] else 0.0,
                "r_multiple_note": "0.000 esatto puo' significare 'R sconosciuto' (NXS_Ledger_HasR="
                    "false, codificato come 0.0 per convenzione) invece di un vero R-multiple nullo - "
                    "ambiguita' nota del CSV standard, non risolvibile senza il log testuale "
                    "[NEXUS LEDGER] correlato (non catturato in questa fase).",
                "resolved_tf": c["resolved_tf"],
            })
        else:
            unmatched_closes.append(c)
        ci += 1

    unmatched_opens = open_queue[oi:]

    payload = {
        "source": "NEXUS_trades.csv reale del run MT5 di questa fase (nxs_orderblock_discovery.ini, "
                 "selettore 15 isolato, InpResearchMode=true, fill reali)",
        "pairing_method": "FIFO cronologico per strategia (ticket=0 su ogni riga OPEN, non "
                          "utilizzabile per il join diretto)",
        "n_open_rows": len(opens), "n_close_rows": len(closes),
        "n_events_paired": len(events),
        "n_unmatched_opens": len(unmatched_opens), "n_unmatched_closes": len(unmatched_closes),
        "unmatched_opens_sample": unmatched_opens[:3],
        "unmatched_closes_sample": unmatched_closes[:3],
        "events": events,
        "direction_undetermined_count": sum(1 for e in events if e["direction"] == 0),
        "mt5_is_ground_truth": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE722_DIR, "canonical_economic_dataset_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    if payload.get("status") == "RUN_NOT_YET_CAPTURED":
        print("  STATO: run non ancora catturato")
    else:
        print(f"  eventi accoppiati: {payload['n_events_paired']} "
              f"(non accoppiati: open={payload['n_unmatched_opens']} close={payload['n_unmatched_closes']})")


if __name__ == "__main__":
    main()
