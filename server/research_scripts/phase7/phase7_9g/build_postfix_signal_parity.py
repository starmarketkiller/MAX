#!/usr/bin/env python3
"""Phase 7.9G - punti 6, 7, 8: run diagnostico di parity post-fix (EA
live corretto), confronto a tre vie (EA live / ricostruzione MQL5
offline isolata a D1 / ricostruzione Python), separazione same-feed vs
cross-feed parity - mai il P&L come criterio.
"""
import csv
import json
import os
import re
import sys
from datetime import datetime

PHASE79G_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79G_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "8d2cde76f4233aa0da3ffa83778eee421a60093c"
RUN_ID_MARKER = "GOLD_2019.02.03"
CERT_DIR = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\Common\Files\NEXUS\certificates"
TESTER_LOG = (r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6"
              r"\Tester\logs\20260923.log")
BASELINE_LINE_OFFSET = 200   # righe presenti PRIMA del lancio del run post-fix (20260923.log, giorno nuovo)

TRACE_RE = re.compile(
    r"\[NXS_TRACE\] run_id=(?P<run_id>\S+ \S+) decision_id=(?P<decision_id>\d+) "
    r"signal_id=(?P<signal_id>\d+) strategy=(?P<strategy>\S+) source_tf=(?P<source_tf>\S+) "
    r"entry_tf=(?P<entry_tf>\S+) level_id=(?P<level_id>\S+) position_id=(?P<position_id>\d+) "
    r"timestamp=(?P<timestamp>\S+ \S+) pipeline_stage=(?P<stage>\S+) gate_reason=(?P<gate>\S+) "
    r"detail=(?P<detail>.*?) build=(?P<build>\S+)$"
)


def _read_text_any_encoding(path):
    for enc in ("utf-8", "utf-16", "utf-16-le", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                text = f.read()
            if text.strip():
                return text
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise RuntimeError(f"impossibile decodificare {path}")


def find_postfix_certificate():
    # il run post-fix e' il PIU' RECENTE fra i candidati con questo run_id base
    candidates = []
    for suffix in ("", "_r001", "_r002", "_r003", "_r004"):
        p = os.path.join(CERT_DIR, f"GOLD_2019.02.03_00-00-00_sel9{suffix}.json")
        if os.path.exists(p):
            candidates.append(p)
    if not candidates:
        raise FileNotFoundError("nessun certificato trovato per il run post-fix")
    candidates.sort(key=lambda p: os.path.getmtime(p))
    return candidates[-1]   # il piu' recente = il run appena eseguito


def parse_live_ea_stream():
    cert_path = find_postfix_certificate()
    cert = json.loads(_read_text_any_encoding(cert_path))

    events = []
    text = _read_text_any_encoding(TESTER_LOG)
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if i < BASELINE_LINE_OFFSET:
            continue
        if RUN_ID_MARKER not in line or "[NXS_TRACE]" not in line:
            continue
        m = TRACE_RE.search(line)
        if m:
            events.append(m.groupdict())

    by_signal = {}
    for ev in events:
        by_signal.setdefault(ev["signal_id"], []).append(ev)

    live_records = []
    for sid, evs in sorted(by_signal.items(), key=lambda kv: int(kv[0])):
        generated = next((e for e in evs if e["stage"] == "GENERATED"), None)
        terminal = None
        for e in evs:
            if e["stage"] in ("BLOCKED", "OPENED", "BROKER_REJECT"):
                terminal = e
        if generated is None:
            continue
        live_records.append({
            "signal_id": sid, "timestamp": generated["timestamp"],
            "generated_detail": generated["detail"],
            "terminal_stage": terminal["stage"] if terminal else "MISSING_TERMINAL",
        })
    return live_records, cert, cert_path


def parse_mql5_offline_isolated():
    path = os.path.join(PHASE79G_DIR, "raw_data", "nxs_breakoutacc_cadence_diag_prefix_isolated.csv")
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    raw = [r for r in rows if r["raw_dir"] != "0"]
    cooldown_pass = [r for r in raw if r["cooldown_ok"] == "1"]
    final_fire = [r for r in cooldown_pass if r["htf_ok"] == "1"]
    return {
        "n_raw_acceptance": len(raw), "n_post_cooldown": len(cooldown_pass),
        "n_final_generated": len(final_fire),
        "final_events": [{"date": r["d1_bar_time"], "dir": int(r["raw_dir"])} for r in final_fire],
    }


def parse_python_reconstruction():
    doc = load_json(os.path.join(PHASE79G_DIR, "raw_data", "python_breakoutacc_full_signal_stream.json"))
    events = doc["events"] if "events" in doc else doc
    raw = [e for e in events if e["event"] in ("SIGNAL_FIRE", "BLOCKED_COOLDOWN", "BLOCKED_HTF")]
    cooldown_pass = [e for e in raw if e["event"] in ("SIGNAL_FIRE", "BLOCKED_HTF")]
    final_fire = [e for e in raw if e["event"] == "SIGNAL_FIRE"]
    return {
        "n_raw_acceptance": len(raw), "n_post_cooldown": len(cooldown_pass),
        "n_final_generated": len(final_fire),
        "final_events": [{"date": e["bar_time"][:10].replace("-", "."), "dir": e["raw_dir"]} for e in final_fire],
    }


def pair_dates(events_a, events_b, tolerance_days=3):
    # Pairing per DATA + DIREZIONE (stessa convenzione di 7.9C/7.9D/7.9E) - mai solo la data.
    #
    # 23/09 - CORREZIONE Phase 7.10 (label inversion trovata nell'audit di integrita'
    # retroattivo): questa funzione e' POSIZIONALE - "only_a" nel dict di ritorno e'
    # SEMPRE il residuo del PRIMO argomento passato, "only_b" del SECONDO,
    # indipendentemente da quale stream logico (A/B/C del report) venga passato per
    # primo. La versione originale di questa fase chiamava pair_dates(stream_B, stream_A)
    # per la sezione "same_feed_parity_A_vs_B" - un'INVERSIONE reale (only_a conteneva il
    # residuo di B, only_b il residuo di A). I NUMERI sostanziali (matched/opened/verdetto)
    # non erano mai stati sbagliati (venivano letti correttamente nel codice di decisione,
    # che compensava lo scambio) - solo le ETICHETTE nell'artifact erano fuorvianti
    # rispetto alla convenzione A/B usata nel resto del report. Fix: OGNI chiamata qui sotto
    # passa ora gli argomenti nello STESSO ordine del nome della sezione (A_vs_B -> (A,B),
    # A_vs_C -> (A,C), B_vs_C -> (B,C)), cosi' only_a/only_b coincidono SEMPRE con la prima/
    # seconda lettera del nome della sezione che li contiene. Vedi
    # server/research_scripts/phase7/phase7_10/breakout_acc_7_9g_label_correction_v1.json
    # per l'audit before/after completo (hash, valori originali preservati).
    items_a = sorted(((datetime.strptime(e["date"], "%Y.%m.%d"), int(e["dir"])) for e in events_a),
                      key=lambda t: t[0])
    items_b = sorted(((datetime.strptime(e["date"], "%Y.%m.%d"), int(e["dir"])) for e in events_b),
                      key=lambda t: t[0])
    matched, only_a, only_b = [], list(items_a), list(items_b)
    for db, dirb in list(items_b):
        best = None
        for da, dira in only_a:
            if dira == dirb and abs((db - da).days) <= tolerance_days:
                best = (da, dira)
                break
        if best is not None:
            matched.append((best, (db, dirb)))
            only_a.remove(best)
            only_b.remove((db, dirb))
    return {"matched": len(matched), "only_a": len(only_a), "only_b": len(only_b),
            "only_a_dates": [f"{d.strftime('%Y-%m-%d')} dir={dr}" for d, dr in only_a],
            "only_b_dates": [f"{d.strftime('%Y-%m-%d')} dir={dr}" for d, dr in only_b]}


def build():
    live_records, cert, cert_path = parse_live_ea_stream()
    mql5_offline = parse_mql5_offline_isolated()
    python_recon = parse_python_reconstruction()

    live_events_for_pairing = [
        {"date": r["timestamp"].split(" ")[0], "dir": 1 if "above_range" in r["generated_detail"] else -1}
        for r in live_records
    ]

    stream_A = {
        "label": "live EA GENERATED (post-fix, run diagnostico reale)",
        "n_generated": len(live_records),
        "n_opened": sum(1 for r in live_records if r["terminal_stage"] == "OPENED"),
        "n_blocked": sum(1 for r in live_records if r["terminal_stage"] == "BLOCKED"),
        "certificate_funnel": cert.get("funnel", {}),
        "certificate_path": os.path.relpath(cert_path, ROOT).replace("\\", "/"),
        "events": [{"date": e["date"], "dir": e["dir"]} for e in live_events_for_pairing],
    }
    stream_B = {"label": "ricostruzione MQL5 offline isolata a D1 (NXS_BreakoutAccCadenceDiagnostic.mq5, "
                        "gia' D1-only per costruzione - nessuna modifica necessaria)", **mql5_offline}
    stream_C = {"label": "ricostruzione Python (server/backtest.py:sig_breakout_acc, invariato - "
                        "gia' D1-only per costruzione, mai esposto alla contaminazione cross-TF)",
                **python_recon}

    same_feed_pairing = pair_dates(stream_A["events"], stream_B["final_events"])
    cross_feed_pairing_A_vs_C = pair_dates(stream_A["events"], stream_C["final_events"])
    cross_feed_pairing_B_vs_C = pair_dates(stream_B["final_events"], stream_C["final_events"])

    exact_target = {
        "declared_target": "live EA GENERATED == MQL5 offline reconstructed == Python "
            "reconstructed, timestamp+direzione esatti 4/4 (o comunque coerenti)",
        "counts": {"A_live_ea": stream_A["n_generated"], "B_mql5_offline": stream_B["n_final_generated"],
                   "C_python": stream_C["n_final_generated"]},
        "same_feed_parity_A_vs_B": {
            "description": "A (EA live, dati broker reale) vs B (script offline MQL5, STESSO "
                "feed broker/cache) - stesso feed, quindi le differenze qui sono attribuibili "
                "SOLO a logica/timing, mai a differenze di dati.",
            "pairing": same_feed_pairing,
            "exact_match": (stream_A["n_generated"] == stream_B["n_final_generated"]
                            and same_feed_pairing["only_a"] == 0 and same_feed_pairing["only_b"] == 0),
        },
        "cross_feed_parity_A_vs_C": {
            "description": "A (EA live, feed broker) vs C (Python, feed Dukascopy) - feed "
                "DIVERSI, differenze qui possono includere anche scostamenti OHLC reali fra "
                "fonti dati, non solo logica.",
            "pairing": cross_feed_pairing_A_vs_C,
        },
        "cross_feed_parity_B_vs_C": {
            "description": "B (MQL5 offline, feed broker) vs C (Python, feed Dukascopy) - "
                "isola l'effetto del solo feed, a parita' di logica (entrambi D1-only "
                "post-fix/gia'-corretti).",
            "pairing": cross_feed_pairing_B_vs_C,
        },
    }

    return {
        "phase": "7.9G", "candidate": "BREAKOUT_ACC", "baseline_commit": BASELINE_COMMIT,
        "diagnostic_only_not_serious_backtest": True, "no_pnl_used_for_parity": True,
        "stream_A_live_ea": stream_A, "stream_B_mql5_offline": stream_B, "stream_C_python": stream_C,
        "exact_parity_target": exact_target,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79G_DIR, "breakout_acc_postfix_signal_parity_v1.json"), doc)
    print(json.dumps(payload["exact_parity_target"]["counts"], indent=2))
    print("same_feed_exact_match:", payload["exact_parity_target"]["same_feed_parity_A_vs_B"]["exact_match"])
    return doc


if __name__ == "__main__":
    main()
