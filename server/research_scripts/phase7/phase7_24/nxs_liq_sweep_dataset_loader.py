#!/usr/bin/env python3
"""Phase 7.24 - loader condiviso: legge il run diagnostico isolato di
Phase 7.23 (manifest + trades.csv + certificato) direttamente dalla
fonte, senza passare dal builder di Phase 7.23 (cosi' l'adjudication
di questa fase e' una ricostruzione INDIPENDENTE, non un riuso cieco).
Riusa solo il rilevatore di encoding dell'harness (BOM-sniffing, fixato
in Phase 7.24 stessa - vedi nxs_research_run_harness._detect_text_encoding)."""
import csv
import glob
import json
import os
import re
import sys

PHASE724_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE724_DIR, "..", "..", "..", ".."))
PHASE723_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_23")
sys.path.insert(0, PHASE723_DIR)
from nxs_research_run_harness import _detect_text_encoding  # noqa: E402

TRADES_COLS = ["time", "action", "ticket", "strategy", "price", "lots", "sl", "tp",
              "score_or_pnl", "reason", "hold_sec", "r_multiple", "resolved_tf"]

RUN_DIR_GLOB = os.path.join(PHASE723_DIR, "runs", "liq_sweep_diagnostic", "*.manifest.json")


def find_manifest():
    candidates = sorted(glob.glob(RUN_DIR_GLOB))
    return candidates[-1] if candidates else None


def load_manifest():
    path = find_manifest()
    if path is None:
        return None, None
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def load_raw_rows(manifest):
    trades_path = manifest.get("trades_csv_dest")
    if trades_path and not os.path.isabs(trades_path):
        trades_path = os.path.join(PHASE723_DIR, trades_path)
    if not trades_path or not os.path.exists(trades_path):
        return []
    encoding = _detect_text_encoding(trades_path)
    with open(trades_path, encoding=encoding, errors="replace") as f:
        reader = csv.reader(f)
        rows = [dict(zip(TRADES_COLS, row)) for row in reader if row]
    return [r for r in rows if r.get("strategy") == "LIQ_SWEEP"]


def parse_certificate_funnel(cert_path):
    """Estrae la riga --- Funnel --- del certificato v2 come dizionario
    di interi. Nessun default implicito: una chiave assente resta
    assente (mai trattata come 0)."""
    if not cert_path or not os.path.exists(cert_path):
        return None
    with open(cert_path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    m = re.search(r"^GENERATED=(\d+) BLOCKED=(\d+) OPEN_ATTEMPT=(\d+) OPENED=(\d+) BROKER_REJECT=(\d+)",
                  text, re.MULTILINE)
    if not m:
        return None
    funnel = {"GENERATED": int(m.group(1)), "BLOCKED": int(m.group(2)),
             "OPEN_ATTEMPT": int(m.group(3)), "OPENED": int(m.group(4)),
             "BROKER_REJECT": int(m.group(5))}
    gate_reasons = {}
    for gm in re.finditer(r"gate_reason=(\w+) count=(\d+)", text):
        gate_reasons[gm.group(1)] = int(gm.group(2))
    funnel["gate_reasons"] = gate_reasons
    return funnel


def pair_events(rows):
    """Appaia OPEN/CLOSE per ordine cronologico (FIFO su timestamp
    stringa ISO-like, sicuro solo perche' l'encoding e' ora corretto -
    vedi Phase 7.24 root-cause del bug BOM). Ritorna (paired, unmatched_opens)."""
    opens = [r for r in rows if r["action"] == "OPEN"]
    closes = [r for r in rows if r["action"] == "CLOSE"]
    opens_sorted = sorted(opens, key=lambda r: r["time"])
    closes_sorted = sorted(closes, key=lambda r: r["time"])
    paired = []
    oi = 0
    for c in closes_sorted:
        if oi < len(opens_sorted) and opens_sorted[oi]["time"] <= c["time"]:
            paired.append((opens_sorted[oi], c))
            oi += 1
    matched_open_times = set(o["time"] for o, _c in paired)
    unmatched_opens = [o for o in opens_sorted if o["time"] not in matched_open_times]
    return paired, unmatched_opens, opens_sorted, closes_sorted
