#!/usr/bin/env python3
"""Phase 7.14 punto 3 - congela la baseline PRE-FIX dal trace reale
(EA istrumentato, nessuna guardia TF ancora applicata alla logica).
Riproducibile: stesso .ini, stesso periodo, stesso build EA (hash del
sorgente NXS_Strategies.mqh con l'istrumentazione temporanea attiva).
Non usa PF/WR come criterio - solo conteggi ed event identity.
"""
import csv
import os
import sys

PHASE714_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE714_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, file_sha256  # noqa: E402

LOCAL_TRACE_CSV = os.path.join(PHASE714_DIR, "nxs_orderblock_realtrace_diag_prefix.csv")
STRAT_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")


def build():
    with open(LOCAL_TRACE_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    canonical_tf = rows[0]["canonical_tf"] if rows else None
    zones_created = {"BUY_SIDE": 0, "SELL_SIDE": 0}
    zones_invalidated = {"BUY_SIDE": 0, "SELL_SIDE": 0}
    zones_expired = {"BUY_SIDE": 0, "SELL_SIDE": 0}
    zones_consumed_retest = {"BUY_SIDE": 0, "SELL_SIDE": 0}
    generated_events = []   # segnali sparati sul TF canonico (would_be_kept_by_router==1)
    non_canonical_fires = []  # segnali sparati su TF non canonico (scartati dal router)

    for r in rows:
        side, op, tf = r["side"], r["op"], r["tf"]
        if op == "ZONE_CREATED":
            zones_created[side] += 1
        elif op == "ZONE_INVALIDATED":
            zones_invalidated[side] += 1
        elif op == "ZONE_EXPIRED":
            zones_expired[side] += 1
        elif op == "RETEST_SIGNAL_FIRED":
            zones_consumed_retest[side] += 1
            event = {"close_time_srv": r["close_time_srv"], "tf": tf, "side": side,
                     "signal_dir": r["signal_dir"]}
            if r["would_be_kept_by_router"] == "1":
                generated_events.append(event)
            else:
                non_canonical_fires.append(event)

    payload = {
        "baseline_kind": "PRE_FIX",
        "reproducible_via": "server/research_scripts/phase7/phase7_14/nxs_orderblock_realtrace_prefix.ini "
                           "+ NXS_Strategies.mqh con istrumentazione temporanea NXS_OB_DIAG_TRACE attiva",
        "nxs_strategies_mqh_sha256_at_capture": file_sha256(STRAT_PATH),
        "canonical_tf": canonical_tf,
        "n_rows_total": len(rows),
        "zones_created": zones_created,
        "zones_invalidated": zones_invalidated,
        "zones_expired": zones_expired,
        "zones_consumed_by_retest_total": zones_consumed_retest,
        "generated_signals_canonical_kept": generated_events,
        "n_generated_signals_canonical_kept": len(generated_events),
        "non_canonical_fires_discarded": non_canonical_fires,
        "n_non_canonical_fires_discarded": len(non_canonical_fires),
        "no_pf_or_wr_used": True,
        "note": "Blocked/opened non modellati in questa cattura (dipendono da gate H1/SMC/esecuzione "
               "broker gia' dichiarati fuori scope in Phase 7.13/7.12) - questa baseline congela "
               "generated (raw trigger canonico) e la contabilita' del ciclo di vita delle zone.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE714_DIR, "baseline_pre_fix_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  generated canonici (tenuti): {payload['n_generated_signals_canonical_kept']}")
    print(f"  spari non canonici (scartati): {payload['n_non_canonical_fires_discarded']}")
    print(f"  zone create: {payload['zones_created']} | invalidate: {payload['zones_invalidated']} | "
          f"scadute: {payload['zones_expired']} | consumate da retest: {payload['zones_consumed_by_retest_total']}")


if __name__ == "__main__":
    main()
