#!/usr/bin/env python3
"""Phase 7.9D - punti 4-5-6-7: legge l'OUTPUT REALE del run diagnostico
(certificato + Journal Tester) e produce:
  - breakout_acc_execution_events_v1.csv/json (un evento per signal_id,
    stato terminale osservato)
  - breakout_acc_execution_gate_counts_v1.json (conteggi aggregati,
    dal certificato + ricalcolati indipendentemente dal Journal)

Nessuna nuova strumentazione: legge SOLO output gia' prodotto dal
sistema esistente (Decision/Gate/Execution Trace v1 + Test Validity
Certificate v2), invariati in questa fase.
"""
import json
import os
import re
import sys

PHASE79D_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE79D_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE79D_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

RUN_ID_MARKER = "GOLD_2019.02.03"   # univoco per FromDate in questo run - nessun altro run in
                                    # questo terminale usa questa data come inizio periodo
CERT_DIR = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\Common\Files\NEXUS\certificates"
TESTER_LOG = (r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6"
              r"\Tester\logs\20260922.log")
# baseline: numero di righe presenti nel log PRIMA del lancio del run diagnostico (verificato
# manualmente subito prima del lancio, vedi vault report) - le righe del MIO run sono tutte
# DOPO questo offset, ma il filtro primario resta comunque RUN_ID_MARKER (univoco), l'offset e'
# solo un'ottimizzazione per non rileggere l'intero file da zero.
BASELINE_LINE_OFFSET = 588048

TRACE_RE = re.compile(
    r"\[NXS_TRACE\] run_id=(?P<run_id>\S+ \S+) decision_id=(?P<decision_id>\d+) "
    r"signal_id=(?P<signal_id>\d+) strategy=(?P<strategy>\S+) source_tf=(?P<source_tf>\S+) "
    r"entry_tf=(?P<entry_tf>\S+) level_id=(?P<level_id>\S+) position_id=(?P<position_id>\d+) "
    r"timestamp=(?P<timestamp>\S+ \S+) pipeline_stage=(?P<stage>\S+) gate_reason=(?P<gate>\S+) "
    r"detail=(?P<detail>.*?) build=(?P<build>\S+)$"
)


def find_certificate_path():
    for suffix in ("", "_r001", "_r002", "_r003"):
        p = os.path.join(CERT_DIR, f"GOLD_2019.02.03_00-00-00_sel9{suffix}.json")
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"nessun certificato trovato per il run in {CERT_DIR}")


def parse_trace_lines():
    events = []
    with open(TESTER_LOG, encoding="utf-16") as f:
        for i, line in enumerate(f):
            if i < BASELINE_LINE_OFFSET:
                continue
            if RUN_ID_MARKER not in line or "[NXS_TRACE]" not in line:
                continue
            m = TRACE_RE.search(line)
            if not m:
                continue
            d = m.groupdict()
            events.append(d)
    return events


def build():
    cert_path = find_certificate_path()
    cert = load_json(cert_path)
    trace_events = parse_trace_lines()

    by_signal = {}
    for ev in trace_events:
        sid = ev["signal_id"]
        by_signal.setdefault(sid, []).append(ev)

    per_signal_records = []
    n_generated = n_opened = n_broker_reject = n_blocked = 0
    gate_counts = {}
    for sid, evs in sorted(by_signal.items(), key=lambda kv: int(kv[0])):
        evs_sorted = evs  # gia' in ordine di apparizione = ordine temporale del Journal
        generated = next((e for e in evs_sorted if e["stage"] == "GENERATED"), None)
        terminal = None
        for e in evs_sorted:
            if e["stage"] in ("BLOCKED", "OPENED", "BROKER_REJECT"):
                terminal = e   # l'ultimo terminale vince (dovrebbe essercene uno solo per contratto)
        if generated is None:
            continue
        n_generated += 1
        rec = {
            "signal_id": sid, "timestamp": generated["timestamp"], "direction_strategy": generated["strategy"],
            "generated_detail": generated["detail"],
            "terminal_stage": terminal["stage"] if terminal else "MISSING_TERMINAL",
            "gate_reason": terminal["gate"] if terminal else "NONE",
            "detail": terminal["detail"] if terminal else "",
            "position_id": terminal["position_id"] if terminal else "0",
        }
        per_signal_records.append(rec)
        if terminal is None:
            continue
        if terminal["stage"] == "OPENED":
            n_opened += 1
        elif terminal["stage"] == "BROKER_REJECT":
            n_broker_reject += 1
        elif terminal["stage"] == "BLOCKED":
            n_blocked += 1
            gate_counts[terminal["gate"]] = gate_counts.get(terminal["gate"], 0) + 1

    n_terminal = n_opened + n_broker_reject + n_blocked
    n_missing_terminal = sum(1 for r in per_signal_records if r["terminal_stage"] == "MISSING_TERMINAL")

    accounting = {
        "total_generated": n_generated,
        "opened": n_opened, "broker_reject": n_broker_reject, "blocked": n_blocked,
        "terminal_total": n_terminal, "missing_terminal": n_missing_terminal,
        "invariant_holds": (n_generated == n_terminal),
        "gate_reason_counts_recomputed_from_journal": gate_counts,
    }

    cross_check = {
        "certificate_path": os.path.relpath(cert_path, ROOT).replace("\\", "/"),
        "certificate_generated": cert.get("funnel", {}).get("generated"),
        "certificate_blocked": cert.get("funnel", {}).get("blocked"),
        "certificate_opened": cert.get("funnel", {}).get("opened"),
        "certificate_broker_reject": cert.get("funnel", {}).get("broker_reject"),
        "certificate_gate_reason_counts": cert.get("gate_reason_counts", {}),
        "certificate_verdict": cert.get("verdict"),
        "matches_journal_recomputation": (
            cert.get("funnel", {}).get("generated") == n_generated and
            cert.get("funnel", {}).get("blocked") == n_blocked and
            cert.get("funnel", {}).get("opened") == n_opened and
            cert.get("funnel", {}).get("broker_reject") == n_broker_reject
        ),
    }

    return per_signal_records, accounting, cross_check, cert


def main():
    per_signal_records, accounting, cross_check, cert = build()

    events_doc = wrap_with_provenance({
        "phase": "7.9D", "candidate": "BREAKOUT_ACC",
        "source": "Journal Tester reale (NXS_TRACE lines), run_id marker=" + RUN_ID_MARKER,
        "n_events": len(per_signal_records),
        "events": per_signal_records,
    }, os.path.basename(__file__))
    save_json(os.path.join(PHASE79D_DIR, "breakout_acc_execution_events_v1.json"), events_doc)

    csv_path = os.path.join(PHASE79D_DIR, "breakout_acc_execution_events_v1.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        f.write("signal_id,timestamp,strategy,generated_detail,terminal_stage,gate_reason,detail,position_id\n")
        for r in per_signal_records:
            f.write(f"{r['signal_id']},{r['timestamp']},{r['direction_strategy']},{r['generated_detail']},"
                    f"{r['terminal_stage']},{r['gate_reason']},{r['detail']},{r['position_id']}\n")

    counts_doc = wrap_with_provenance({
        "phase": "7.9D", "candidate": "BREAKOUT_ACC",
        "accounting": accounting, "certificate_cross_check": cross_check,
        "certificate_full": cert,
    }, os.path.basename(__file__))
    save_json(os.path.join(PHASE79D_DIR, "breakout_acc_execution_gate_counts_v1.json"), counts_doc)

    print(json.dumps(accounting, indent=2))
    print(json.dumps(cross_check, indent=2))
    return events_doc, counts_doc


if __name__ == "__main__":
    main()
