#!/usr/bin/env python3
"""Phase 7.24 punto 3 - Dataset canonico MT5 per LIQ_SWEEP: un record
per evento con tutti i campi richiesti (event_id, run_id, identita',
timestamp, direzione, prezzo segnale/fill, exit, P&L reale, SL/TP
reali, lifecycle, provenance, hash). MT5 = ground truth (nessuna
derivazione Python usata qui)."""
import os
import sys

PHASE724_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE724_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE724_DIR)
from nxs_liq_sweep_dataset_loader import load_manifest, load_raw_rows, pair_events  # noqa: E402


def _direction(sl, tp, price):
    if sl < price < tp:
        return "BUY"
    if sl > price > tp:
        return "SELL"
    return "AMBIGUOUS"


def build():
    manifest, manifest_path = load_manifest()
    if manifest is None:
        return {"status": "NO_MANIFEST_FOUND"}

    rows = load_raw_rows(manifest)
    paired, unmatched_opens, opens_sorted, closes_sorted = pair_events(rows)

    provenance = {
        "run_id": manifest["run_id"],
        "run_isolation_manifest": manifest_path,
        "strategy_identity": manifest["strategy_identity"],
        "selector": manifest["selector"],
        "symbol": manifest["symbol"],
        "code_git_sha": manifest["code_git_sha"],
        "config_hash": manifest["config_hash"],
        "period_from": manifest["period_from"], "period_to": manifest["period_to"],
        "source": "MQL5 Strategy Tester (MT5) - ground truth. Nessun dato Python usato per "
                 "costruire questo dataset.",
    }

    events = []
    for o, c in paired:
        sl, tp, price = float(o["sl"]), float(o["tp"]), float(o["price"])
        exit_price = float(c["price"])
        net_pnl = float(c["score_or_pnl"])
        event_id = f"{manifest['run_id']}::ticket_{c['ticket']}"
        events.append({
            "event_id": event_id,
            "run_id": manifest["run_id"],
            "strategy_identity": "LIQ_SWEEP", "selector": manifest["selector"],
            "lifecycle": "CLOSED",
            "direction": _direction(sl, tp, price),
            "entry": {
                "timestamp": o["time"],
                "signal_reference_price": price,
                "signal_reason_tag": o["reason"],
                "fill_price_note": "nessun prezzo di fill separato loggato per l'OPEN in questo "
                    "formato CSV - il prezzo di segnale/entry e' l'unico disponibile per questo "
                    "evento (limite noto del logging, non della strategia - dichiarato, non "
                    "nascosto).",
                "planned_sl": sl, "planned_tp": tp,
            },
            "exit": {
                "timestamp": c["time"], "exit_price": exit_price,
                "exit_reason": c["reason"],
                "hold_seconds": int(c["hold_sec"]) if c["hold_sec"] else None,
                "r_multiple": float(c["r_multiple"]) if c["r_multiple"] else None,
                "resolved_tf": c["resolved_tf"] or None,
            },
            "actual_pnl": net_pnl,
            "lots": float(c["lots"]) if c["lots"] else None,
            "ticket": c["ticket"],
            "block_reject_reason": None,
            "provenance_ref": manifest["run_id"],
        })

    for o in unmatched_opens:
        sl, tp, price = float(o["sl"]), float(o["tp"]), float(o["price"])
        event_id = f"{manifest['run_id']}::open_only_{o['time'].replace(' ', '_').replace(':', '').replace('.', '')}"
        events.append({
            "event_id": event_id,
            "run_id": manifest["run_id"],
            "strategy_identity": "LIQ_SWEEP", "selector": manifest["selector"],
            "lifecycle": "OPEN_AT_PERIOD_END",
            "direction": _direction(sl, tp, price),
            "entry": {
                "timestamp": o["time"], "signal_reference_price": price,
                "signal_reason_tag": o["reason"],
                "fill_price_note": "vedi nota sopra - stesso limite di logging per ogni OPEN.",
                "planned_sl": sl, "planned_tp": tp,
            },
            "exit": None,
            "actual_pnl": None,
            "lots": None,
            "ticket": None,
            "block_reject_reason": None,
            "provenance_ref": manifest["run_id"],
            "note": "posizione ancora aperta al termine della finestra testata "
                   "(period_end=2026.06.29 23:58:58) - nessun P&L realizzato disponibile in "
                   "questo run. Vedi funnel_accounting_v1.json, adjudication #2 "
                   "(EXPECTED_FUNNEL_DIFFERENCE). ESCLUSO dal dataset economico (n=42) ma "
                   "conservato qui per completezza del ciclo di vita completo.",
        })

    events.sort(key=lambda e: e["entry"]["timestamp"])

    closed_events = [e for e in events if e["lifecycle"] == "CLOSED"]
    payload = {
        "provenance": provenance,
        "python_used_to_build_this_dataset": False,
        "n_events_total": len(events),
        "n_events_closed_economic": len(closed_events),
        "n_events_open_at_period_end": len(events) - len(closed_events),
        "net_pnl_closed_only": round(sum(e["actual_pnl"] for e in closed_events), 2),
        "events": events,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE724_DIR, "liq_sweep_canonical_dataset_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  n_events_total={payload['n_events_total']} closed={payload['n_events_closed_economic']} "
         f"open_at_end={payload['n_events_open_at_period_end']} net_pnl_closed={payload['net_pnl_closed_only']}")


if __name__ == "__main__":
    main()
